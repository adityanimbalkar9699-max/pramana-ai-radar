"""Agent 9: MonitoringAgent — re-verifies existing tools for pricing drift or discontinuation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..database import PramanaDatabase
from ..models import RawCandidate, ToolRecord, today_iso
from ..sources.base import SafeHttpClient
from .opensource import OpenSourceAgent
from .pricing import PricingVerificationAgent
from .research import ResearchAgent


@dataclass
class MonitoringSummary:
    checked_count: int = 0
    pricing_changes: List[str] = field(default_factory=list)
    discontinued: List[str] = field(default_factory=list)
    errors: int = 0


class MonitoringAgent:
    """Periodically re-verifies saved tools to catch removed free tiers or dead URLs."""

    def __init__(self, db: PramanaDatabase, client: SafeHttpClient, github_token: str = "") -> None:
        self.db = db
        self.client = client
        self.research = ResearchAgent(client)
        self.pricing = PricingVerificationAgent(client)
        self.opensource = OpenSourceAgent(client, github_token=github_token)

    def check_batch(self, max_tools: int = 6) -> MonitoringSummary:
        summary = MonitoringSummary()
        tools = self.db.list_tools(status="active")
        # Sort oldest verification date first
        tools.sort(key=lambda t: t.get("last_verification_date", ""))
        batch = tools[:max_tools]

        for t in batch:
            summary.checked_count += 1
            try:
                cand = RawCandidate(
                    name=t["name"],
                    url=t["official_website"],
                    source_name="Monitoring Re-Check",
                    source_url=t["official_website"],
                    summary=t["short_description"],
                    github_repo=t.get("github_repository", ""),
                    category_hint=t["category"],
                    subcategory_hint=t["subcategory"],
                )
                dossier = self.research.investigate(cand)
                os_rep = self.opensource.inspect(cand, dossier.discovered_github)
                price_ver = self.pricing.verify(cand, dossier, os_rep.license_name)

                # If site returns 404/410 permanently, flag as discontinued
                new_status = t["status"]
                if dossier.http_status in (404, 410) and not os_rep.github_repository:
                    new_status = "discontinued"
                    summary.discontinued.append(t["name"])

                # Detect change from genuinely free to non-free
                if t["is_genuinely_free"] and not price_ver.is_genuinely_free and price_ver.is_trial_only:
                    new_status = "pricing_changed"
                    summary.pricing_changes.append(f"{t['name']}: shifted toward trial/paid")

                # Update verification date and pricing history cleanly if changed
                with self.db.connect() as conn:
                    conn.execute(
                        "UPDATE tools SET last_verification_date = ?, status = ? WHERE canonical_key = ?",
                        (today_iso(), new_status, t["canonical_key"]),
                    )
                    if new_status != t["status"]:
                        conn.execute(
                            """
                            INSERT INTO pricing_history
                            (canonical_key, tool_name, old_free_plan, new_free_plan, old_limits, new_limits, change_type, source_url, detected_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                t["canonical_key"],
                                t["name"],
                                t["free_plan_details"],
                                price_ver.free_plan_details,
                                t["free_usage_limits"],
                                price_ver.free_usage_limits,
                                "discontinued" if new_status == "discontinued" else "reduced",
                                t["official_website"],
                                today_iso(),
                            ),
                        )
            except Exception:
                summary.errors += 1

        return summary
