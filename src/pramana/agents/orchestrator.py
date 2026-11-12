"""Agent 10: OrchestratorAgent — coordinates the 10-agent pipeline end-to-end."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config import RuntimeConfig
from ..database import PramanaDatabase
from ..models import RawCandidate, ToolRecord, today_iso
from ..notifications import NotificationManager
from ..sources import SafeHttpClient
from .deduplication import DeduplicationAgent, make_canonical_key
from .discovery import DiscoveryAgent
from .monitoring import MonitoringAgent
from .opensource import OpenSourceAgent
from .personalization import PersonalizationAgent
from .pricing import PricingVerificationAgent
from .quality import QualityEvaluationAgent
from .reporting import ReportGenerationAgent
from .research import ResearchAgent

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    run_id: int
    status: str
    candidates_scanned: int = 0
    new_tools_added: int = 0
    rejected_fake_free: int = 0
    duplicates_skipped: int = 0
    pricing_changes_detected: int = 0
    emerging_categories: List[str] = field(default_factory=list)
    new_tools: List[Dict[str, Any]] = field(default_factory=list)
    sources_succeeded: List[str] = field(default_factory=list)
    sources_failed: List[str] = field(default_factory=list)
    daily_digest: Dict[str, Any] = field(default_factory=dict)
    weekly_report: Optional[Dict[str, Any]] = None
    notification_status: Dict[str, Any] = field(default_factory=dict)


class OrchestratorAgent:
    """Coordinates all 9 specialist agents with fault isolation and atomic persistence."""

    def __init__(self, db: PramanaDatabase, config: RuntimeConfig) -> None:
        self.db = db
        self.config = config
        self.client = SafeHttpClient(timeout=config.request_timeout)
        self.discovery = DiscoveryAgent(self.client, github_token=config.github_token)
        self.research = ResearchAgent(self.client)
        self.pricing = PricingVerificationAgent(self.client)
        self.opensource = OpenSourceAgent(self.client, github_token=config.github_token)
        self.quality = QualityEvaluationAgent()
        self.personalization = PersonalizationAgent()
        self.monitoring = MonitoringAgent(self.db, self.client, github_token=config.github_token)
        self.reporting = ReportGenerationAgent(self.db)
        self.notifier = NotificationManager(self.config, self.db)

    def _evaluate_candidate(self, cand: RawCandidate) -> tuple[Optional[ToolRecord], Optional[str], List[str]]:
        """Run Research + OpenSource + Pricing + Quality + Personalization on one candidate."""
        dossier = self.research.investigate(cand)
        os_rep = self.opensource.inspect(cand, dossier.discovered_github)
        price_ver = self.pricing.verify(cand, dossier, os_rep.license_name)

        # Strict acceptance gate: never admit fake-free / trial-only / unverified tools
        if not price_ver.is_genuinely_free:
            reason = (
                "Rejected as non-free / trial-only / unverified free tier: "
                + ("; ".join(price_ver.fake_free_flags) or price_ver.free_tier_type)
            )
            return None, reason, price_ver.fake_free_flags

        score_bd = self.quality.score(cand, dossier, price_ver, os_rep)
        if score_bd.total_score < self.config.min_score:
            reason = f"Below minimum quality score ({score_bd.total_score} < {self.config.min_score})"
            return None, reason, price_ver.fake_free_flags

        pers, useful_summary, best_use = self.personalization.evaluate(cand, dossier, price_ver, os_rep)

        canon_key = make_canonical_key(cand.name, dossier.final_url or cand.url, os_rep.github_repository)
        tags = list(dict.fromkeys(
            [t.lower() for t in cand.topics[:5]]
            + [dossier.category.lower().split()[0], pers.priority_track.lower()]
        ))

        tool = ToolRecord(
            name=cand.name,
            official_website=dossier.final_url or cand.url,
            category=dossier.category,
            subcategory=dossier.subcategory,
            short_description=dossier.description[:320],
            main_capabilities=dossier.main_capabilities,
            what_makes_it_useful=useful_summary,
            free_plan_details=price_ver.free_plan_details,
            free_usage_limits=price_ver.free_usage_limits,
            credit_card_required=price_ver.credit_card_required,
            registration_required=price_ver.registration_required,
            open_source_status=os_rep.open_source_status,
            github_repository=os_rep.github_repository,
            supported_os=dossier.supported_os,
            api_availability=dossier.api_availability,
            local_installation_available=dossier.local_installation_available,
            important_limitations=dossier.limitations or (
                ["Verify rate limits on official docs before heavy hackathon traffic."]
                if price_ver.free_tier_type != "Free Open Source"
                else ["Bounded locally by 6GB RTX 4050 VRAM / 16GB RAM."]
            ),
            privacy_considerations=dossier.privacy_considerations,
            last_verification_date=today_iso(),
            official_documentation=dossier.official_documentation,
            best_student_use_case=best_use,
            canonical_key=canon_key,
            free_tier_type=price_ver.free_tier_type,
            is_genuinely_free=True,
            india_available=price_ver.india_available,
            score=score_bd.total_score,
            score_breakdown=score_bd,
            personalization=pers,
            sources=[cand.source_url or cand.url, price_ver.pricing_url],
            tags=tags[:8],
            stars=os_rep.stars,
            license_name=os_rep.license_name,
            discovery_date=today_iso(),
            status="active",
            direct_app_url=str(cand.extra.get("direct_app_url") or dossier.final_url or cand.url),
            pricing_url=price_ver.pricing_url,
            web_only=bool(
                cand.extra.get("web_only")
                or dossier.local_installation_available == "No"
                or "huggingface.co/spaces/" in cand.url.lower()
                or "Web" in dossier.supported_os and "Windows" not in dossier.supported_os
            ),
            free_quota_cadence=price_ver.free_quota_cadence,
        )
        return tool, None, []

    def run_daily(
        self,
        *,
        target_new: Optional[int] = None,
        bootstrap_if_empty: bool = True,
        send_notifications: bool = True,
    ) -> PipelineResult:
        target = target_new if target_new is not None else self.config.daily_target
        run_id = self.db.start_run("daily")
        result = PipelineResult(run_id=run_id, status="running")

        try:
            self.db.create_backup()
            existing = self.db.get_all_names_and_urls()
            is_empty_db = len(existing) == 0

            dedup = DeduplicationAgent(existing)
            batch = self.discovery.run(
                include_seed_when_empty_db=(bootstrap_if_empty and is_empty_db),
                per_source_limit=14,
            )
            result.sources_succeeded = batch.sources_succeeded
            result.sources_failed = batch.sources_failed
            result.emerging_categories = batch.emerging_categories_detected

            unique_candidates: List[RawCandidate] = []
            for cand in batch.candidates:
                result.candidates_scanned += 1
                is_dup, _ = dedup.is_duplicate(cand.name, cand.url, cand.github_repo)
                if is_dup:
                    result.duplicates_skipped += 1
                    continue
                unique_candidates.append(cand)

            # Cap per-run deep inspections to keep CI runtime crisp & respectful
            eval_budget = max(target * 5, 36 if is_empty_db else 18)
            to_inspect = unique_candidates[:eval_budget]

            verified_new: List[ToolRecord] = []
            with ThreadPoolExecutor(max_workers=4) as pool:
                future_map = {
                    pool.submit(self._evaluate_candidate, cand): cand for cand in to_inspect
                }
                for fut in as_completed(future_map):
                    cand = future_map[fut]
                    try:
                        tool, rej_reason, flags = fut.result(timeout=30)
                        if tool is not None:
                            verified_new.append(tool)
                        else:
                            result.rejected_fake_free += 1
                            key = make_canonical_key(cand.name, cand.url, cand.github_repo)
                            self.db.record_rejected(key, cand.name, cand.url, rej_reason or "Rejected", flags)
                    except Exception as exc:
                        logger.debug("Evaluation error for %s: %s", cand.name, exc)

            # Sort highest-scoring discoveries first; keep all on bootstrap or top discoveries daily
            verified_new.sort(key=lambda t: t.score, reverse=True)
            to_persist = verified_new if is_empty_db else verified_new[: max(target, 6)]

            for tool in to_persist:
                outcome = self.db.upsert_tool(tool)
                if outcome == "inserted":
                    result.new_tools_added += 1
                    result.new_tools.append(tool.to_dict())

            # Monitoring Agent checks a small batch of existing tools for pricing drift
            mon = self.monitoring.check_batch(max_tools=5)
            result.pricing_changes_detected = len(mon.pricing_changes) + len(mon.discontinued)

            # Daily Digest & Reports
            result.daily_digest = self.reporting.build_daily_digest(result.new_tools)
            self.reporting.export_csv()
            self.reporting.export_excel()
            self.db.export_catalog_snapshot()

            if send_notifications:
                result.notification_status = self.notifier.notify_daily(result.daily_digest)

            result.status = "success" if batch.sources_succeeded else "partial"
            self.db.finish_run(
                run_id,
                status=result.status,
                candidates_scanned=result.candidates_scanned,
                new_tools_added=result.new_tools_added,
                rejected_fake_free=result.rejected_fake_free,
                duplicates_skipped=result.duplicates_skipped,
                pricing_changes_detected=result.pricing_changes_detected,
                sources_succeeded=result.sources_succeeded,
                sources_failed=result.sources_failed,
                summary=f"Added {result.new_tools_added} verified tools; rejected {result.rejected_fake_free} non-free/low-score.",
            )
            return result
        except Exception as exc:
            logger.exception("Daily orchestration failed")
            result.status = "failed"
            self.db.finish_run(
                run_id,
                status="failed",
                candidates_scanned=result.candidates_scanned,
                new_tools_added=result.new_tools_added,
                rejected_fake_free=result.rejected_fake_free,
                duplicates_skipped=result.duplicates_skipped,
                pricing_changes_detected=result.pricing_changes_detected,
                sources_succeeded=result.sources_succeeded,
                sources_failed=result.sources_failed + [str(exc)],
                summary=f"Failed: {exc}",
            )
            if send_notifications:
                self.notifier.notify_failure("Daily Discovery", str(exc))
            raise

    def run_weekly(self, send_notifications: bool = True) -> PipelineResult:
        # First run a daily discovery pass + broader monitoring sweep
        res = self.run_daily(target_new=5, bootstrap_if_empty=True, send_notifications=False)
        run_id = self.db.start_run("weekly")
        try:
            mon = self.monitoring.check_batch(max_tools=15)
            weekly = self.reporting.generate_weekly_report()
            self.db.export_catalog_snapshot()
            res.weekly_report = weekly
            if send_notifications:
                res.notification_status = self.notifier.notify_weekly(weekly)
            self.db.finish_run(
                run_id,
                status="success",
                candidates_scanned=res.candidates_scanned,
                new_tools_added=res.new_tools_added,
                rejected_fake_free=res.rejected_fake_free,
                duplicates_skipped=res.duplicates_skipped,
                pricing_changes_detected=res.pricing_changes_detected + len(mon.pricing_changes),
                sources_succeeded=res.sources_succeeded,
                sources_failed=res.sources_failed,
                summary=f"Weekly report {weekly['week_label']} generated with Top 10 rankings & PDF/CSV/XLSX.",
            )
            return res
        except Exception as exc:
            self.db.finish_run(
                run_id,
                status="failed",
                candidates_scanned=res.candidates_scanned,
                new_tools_added=res.new_tools_added,
                rejected_fake_free=res.rejected_fake_free,
                duplicates_skipped=res.duplicates_skipped,
                pricing_changes_detected=res.pricing_changes_detected,
                sources_succeeded=res.sources_succeeded,
                sources_failed=res.sources_failed + [str(exc)],
                summary=f"Weekly run failed: {exc}",
            )
            if send_notifications:
                self.notifier.notify_failure("Weekly Intelligence", str(exc))
            raise
