"""Agent 3: PricingVerificationAgent — verifies genuine free plans & catches Fake-Free traps."""

from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from ..models import PricingVerification, RawCandidate, UNKNOWN
from ..sources.base import SafeHttpClient, extract_html_metadata
from .research import ResearchDossier


TRIAL_TRAP_PATTERNS = [
    re.compile(r"\b(\d{1,2})[- ]day free trial\b", re.I),
    re.compile(r"\bfree trial only\b", re.I),
    re.compile(r"\bno free (plan|tier)\b", re.I),
    re.compile(r"\bstart (your )?free trial\b", re.I),
    re.compile(r"\bcredit card required\b", re.I),
    re.compile(r"\badd (a )?payment method to (start|continue)\b", re.I),
]

ONE_TIME_CREDIT_PATTERNS = [
    re.compile(r"\$\d+\s*(in )?(free )?credits?\b", re.I),
    re.compile(r"\bone[- ]time\s+(free )?credits?\b", re.I),
    re.compile(r"\binitial\s+\d+\s+free credits?\b", re.I),
]

PERMANENT_FREE_SIGNALS = [
    "free forever",
    "free tier",
    "free plan",
    "open source",
    "open-source",
    "mit license",
    "apache-2.0",
    "apache 2.0",
    "gpl",
    "bsd",
    "$0",
    "no credit card",
    "100% free",
    "community edition",
    "self-host",
    "free for students",
    "student developer pack",
]

GEO_RESTRICTION_PATTERNS = [
    re.compile(r"\bnot available in (your country|india)\b", re.I),
    re.compile(r"\bus[- ]only\b", re.I),
]

KNOWN_FREE_LIMIT_HINTS = {
    "groq.com": "Free developer tier with per-minute & daily token/request rate limits (no credit card required).",
    "aistudio.google.com": "Free tier in Google AI Studio with RPM/TPM/RPD rate limits; prompts may be logged on free tier.",
    "openrouter.ai": "Unlimited access to `:free` tagged open models subject to per-minute/daily rate limits; paid models require credits.",
    "qdrant.tech": "Permanent 1 GB free cloud cluster + unlimited local open-source Docker/self-hosted usage.",
    "supabase.com": "Free tier includes 2 active projects, 500 MB database, 50K MAUs, and pgvector support.",
    "workers.cloudflare.com": "Free tier includes 100,000 Workers requests/day and daily Workers AI free neuron quota.",
    "notebooklm.google.com": "Free Google account usage with source/notebook quotas per day.",
    "kaggle.com": "30 hours/week free GPU (T4/P100) + 20 hours/week TPU + public/private notebooks.",
    "education.github.com": "Free for verified students (college email/ID); includes Copilot Pro & partner credits.",
}


class PricingVerificationAgent:
    """Verifies free-plan truth from official pricing pages and GitHub licenses."""

    def __init__(self, client: SafeHttpClient) -> None:
        self.client = client

    def verify(
        self,
        candidate: RawCandidate,
        dossier: ResearchDossier,
        verified_license: str = "",
    ) -> PricingVerification:
        pricing_texts: List[str] = [dossier.visible_text]
        pricing_url = ""

        # Probe discovered pricing links or standard /pricing path on official domain
        probe_urls = list(dossier.pricing_links)
        if not probe_urls and dossier.final_url.startswith("http") and "github.com/" not in dossier.final_url.lower():
            probe_urls.append(urljoin(dossier.final_url.rstrip("/") + "/", "pricing"))

        for purl in probe_urls[:2]:
            res = self.client.fetch(purl)
            if res.ok and res.text:
                meta = extract_html_metadata(res.text, res.final_url)
                if meta["visible_text"]:
                    pricing_texts.append(str(meta["visible_text"]))
                    pricing_url = res.final_url
                    break

        combined = " ".join(pricing_texts)
        low = combined.lower()

        is_open_source = bool(
            verified_license
            and verified_license not in (UNKNOWN, "Closed Source", "Proprietary", "Custom / Check Repo")
        ) or ("github.com/" in (dossier.discovered_github or candidate.url).lower() and any(
            k in low for k in ("mit license", "apache", "gpl", "bsd", "open source", "open-source")
        ))

        flags: List[str] = []
        trial_hits = [p.pattern for p in TRIAL_TRAP_PATTERNS if p.search(combined)]
        credit_hits = [p.pattern for p in ONE_TIME_CREDIT_PATTERNS if p.search(combined)]
        # Exclude false positive when "no free plan" / "no free tier" explicitly negates "free plan"
        cleaned_low = re.sub(r"\bno free (plan|tier)\b", "", low)
        free_hits = [sig for sig in PERMANENT_FREE_SIGNALS if sig in cleaned_low]

        if any("credit card required" in low or "add a payment method" in low for _ in [1]):
            if "no credit card required" not in low and "without a credit card" not in low:
                flags.append("Possible credit card requirement detected on page")

        has_trial_only = bool(trial_hits) and not free_hits and not is_open_source
        if has_trial_only:
            flags.append("Free trial language detected without permanent free tier")

        is_one_time_only = bool(credit_hits) and not free_hits and not is_open_source
        if is_one_time_only:
            flags.append("Appears limited to one-time starter credits rather than recurring free usage")

        # Determine India availability
        if any(p.search(combined) for p in GEO_RESTRICTION_PATTERNS):
            india_avail = "Restricted"
            flags.append("Potential geographic restriction detected")
        elif is_open_source or dossier.http_ok:
            india_avail = "Yes"
        else:
            india_avail = UNKNOWN

        # Classify free tier type accurately
        if is_open_source:
            tier_type = "Free Open Source"
            genuinely_free = True
            cc_req = "No"
            reg_req = "No" if "github.com/" in dossier.final_url.lower() or dossier.local_installation_available == "Yes" else "Optional"
            plan_details = f"Open-source ({verified_license or 'OSI/Public Repo'}) — free for local & commercial/student use."
        elif "student" in (candidate.name + " " + candidate.summary).lower() and "free" in low:
            tier_type = "Free Student Plan"
            genuinely_free = True
            cc_req = "No"
            reg_req = "Yes (Student Verification)"
            plan_details = "Verified free student plan with zero subscription fee."
        elif has_trial_only:
            tier_type = "Trial Only"
            genuinely_free = False
            cc_req = "Yes" if "credit card required" in low and "no credit card" not in low else UNKNOWN
            reg_req = "Yes"
            plan_details = "Rejected: Appears to offer a time-limited trial rather than a genuine free tier."
        elif is_one_time_only:
            tier_type = "Freemium (One-time Credits)"
            genuinely_free = False
            cc_req = "No" if "no credit card" in low else UNKNOWN
            reg_req = "Yes"
            plan_details = "Warning: Primarily offers one-time free credits without confirmed recurring free allowance."
        elif free_hits or "huggingface.co" in dossier.final_url.lower():
            if "100% free" in low or "completely free" in low or "huggingface.co" in dossier.final_url.lower():
                tier_type = "Completely Free"
            elif "free tier" in low or "free plan" in low or "$0" in low or "free forever" in low:
                tier_type = "Generous Free Tier"
            else:
                tier_type = "Freemium Useful Free"
            genuinely_free = True
            cc_req = "No" if ("no credit card" in low or "free" in low) else UNKNOWN
            reg_req = "No" if "no sign" in low or "no account" in low else "Yes"
            plan_details = f"Verified {tier_type} via official site/pricing signals ({', '.join(free_hits[:3]) or 'public access'})."
        else:
            # Could not verify free plan from live page — mark UNKNOWN rather than fabricating
            tier_type = UNKNOWN
            genuinely_free = False
            cc_req = UNKNOWN
            reg_req = UNKNOWN
            plan_details = UNKNOWN
            flags.append("Could not empirically confirm permanent free tier from inspected pages")

        # Domain-verified usage limits if known, else extracted or UNKNOWN
        limits = UNKNOWN
        for dom, hint in KNOWN_FREE_LIMIT_HINTS.items():
            if dom in dossier.final_url.lower() or dom in candidate.url.lower():
                limits = hint
                break
        if limits == UNKNOWN:
            if is_open_source:
                limits = "Unlimited local execution (bounded only by your hardware / RTX 4050 6GB VRAM)."
            elif "rate limit" in low or "requests per" in low or "tokens per" in low:
                limits = "Subject to official free-tier rate/quota limits (see pricing/docs)."

        return PricingVerification(
            free_tier_type=tier_type,
            is_genuinely_free=genuinely_free,
            free_plan_details=plan_details,
            free_usage_limits=limits,
            credit_card_required=cc_req,
            registration_required=reg_req,
            is_trial_only=has_trial_only,
            is_one_time_credits_only=is_one_time_only,
            india_available=india_avail,
            fake_free_flags=flags,
            pricing_url=pricing_url or dossier.final_url,
            verification_notes=f"Inspected {dossier.final_url}" + (f" and {pricing_url}" if pricing_url else ""),
        )
