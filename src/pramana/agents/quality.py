"""Agent 5: QualityEvaluationAgent — transparent 100-point rubric + penalty engine."""

from __future__ import annotations

from typing import List

from ..models import PricingVerification, RawCandidate, ScoreBreakdown, UNKNOWN
from .opensource import OpenSourceReport
from .research import ResearchDossier


HIGH_VALUE_KEYWORDS = (
    "agent", "multi-agent", "llm", "rag", "vector", "python", "c++", "api",
    "local", "coding", "cuda", "gpu", "mcp", "workflow", "automation", "whisper",
)


class QualityEvaluationAgent:
    """Scores tools strictly on empirical signals without artificial inflation."""

    def score(
        self,
        candidate: RawCandidate,
        dossier: ResearchDossier,
        pricing: PricingVerification,
        os_report: OpenSourceReport,
    ) -> ScoreBreakdown:
        bd = ScoreBreakdown()
        penalties: List[str] = []

        # 1. Free functionality (25 pts)
        if pricing.free_tier_type in ("Completely Free", "Free Open Source"):
            bd.free_functionality = 24.0 if os_report.is_open_source else 23.0
        elif pricing.free_tier_type == "Free Student Plan":
            bd.free_functionality = 22.0
        elif pricing.free_tier_type == "Generous Free Tier":
            bd.free_functionality = 20.0
        elif pricing.free_tier_type == "Free Credits (Starter)":
            bd.free_functionality = 17.5
        elif pricing.free_tier_type == "Freemium Useful Free":
            bd.free_functionality = 15.0
        elif pricing.free_tier_type == "Freemium (One-time Credits)":
            bd.free_functionality = 7.0
        else:
            bd.free_functionality = 2.0

        # 2. Practical usefulness (20 pts)
        blob = f"{candidate.name} {dossier.description} {' '.join(candidate.topics)}".lower()
        kw_hits = sum(1 for kw in HIGH_VALUE_KEYWORDS if kw in blob)
        usefulness = 11.0 + min(6.0, kw_hits * 1.5)
        if dossier.api_availability != UNKNOWN and "No" not in dossier.api_availability:
            usefulness += 2.0
        if dossier.local_installation_available == "Yes":
            usefulness += 1.0
        bd.practical_usefulness = min(20.0, usefulness)

        # 3. Reliability (15 pts)
        rel = 7.0 if dossier.http_ok else 3.0
        if os_report.stars >= 10000:
            rel += 7.0
        elif os_report.stars >= 2000:
            rel += 5.5
        elif os_report.stars >= 300:
            rel += 4.0
        elif dossier.http_ok:
            rel += 4.5
        if os_report.archived:
            rel -= 5.0
        bd.reliability = max(0.0, min(15.0, rel))

        # 4. Student value (15 pts)
        sv = 9.0
        if dossier.category in ("AI and Machine Learning", "Coding and Development", "Career and Education"):
            sv += 3.0
        if pricing.credit_card_required == "No":
            sv += 2.0
        if pricing.india_available == "Yes":
            sv += 1.0
        bd.student_value = min(15.0, sv)

        # 5. Ease of use (10 pts)
        ease = 6.5
        if "Windows" in dossier.supported_os or "Web" in dossier.supported_os:
            ease += 2.0
        if pricing.registration_required in ("No", "Optional"):
            ease += 1.5
        bd.ease_of_use = min(10.0, ease)

        # 6. Performance (10 pts)
        perf = 7.0
        if dossier.local_installation_available == "Yes" or "Free API" in dossier.api_availability:
            perf += 2.0
        if "groq" in candidate.name.lower() or "rust" in (os_report.primary_language or "").lower() or "c++" in (os_report.primary_language or "").lower():
            perf += 1.0
        bd.performance = min(10.0, perf)

        # 7. Documentation (5 pts)
        bd.documentation = 4.5 if dossier.official_documentation != UNKNOWN else 2.0

        # Penalties
        penalty_total = 0.0
        if pricing.credit_card_required == "Yes":
            penalty_total += 25.0
            penalties.append("-25: Credit card required")
        if pricing.is_trial_only or not pricing.is_genuinely_free:
            penalty_total += 35.0
            penalties.append("-35: Trial-only or unverified free tier")
        if pricing.is_one_time_credits_only:
            penalty_total += 15.0
            penalties.append("-15: One-time credits only (no recurring free tier)")
        if os_report.archived:
            penalty_total += 12.0
            penalties.append("-12: GitHub repository is archived")
        if not dossier.http_ok:
            penalty_total += 15.0
            penalties.append("-15: Official URL unreachable during verification")
        if pricing.india_available == "Restricted":
            penalty_total += 15.0
            penalties.append("-15: Geographic availability restricted for India")

        bd.penalties = penalty_total
        bd.penalty_reasons = penalties
        total = bd.compute_total()

        bd.explanation = (
            f"Score {total}/100 — Free({bd.free_functionality}/25) + Usefulness({bd.practical_usefulness}/20) "
            f"+ Reliability({bd.reliability}/15) + Student({bd.student_value}/15) + Ease({bd.ease_of_use}/10) "
            f"+ Perf({bd.performance}/10) + Docs({bd.documentation}/5)"
            + (f" minus penalties ({'; '.join(penalties)})" if penalties else " with 0 penalties.")
        )
        return bd
