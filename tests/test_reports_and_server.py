"""Tests for PDF/CSV/Excel report generation, notification suppression, and Flask REST API."""

from pathlib import Path

from pramana.agents.reporting import ReportGenerationAgent
from pramana.config import RuntimeConfig
from pramana.database import PramanaDatabase
from pramana.models import PersonalizationProfile, ScoreBreakdown, ToolRecord
from pramana.notifications import NotificationManager
from pramana.server import create_app


def _seed_db(tmp_path: Path) -> PramanaDatabase:
    db = PramanaDatabase(tmp_path / "api_test.db")
    for idx in range(1, 5):
        db.upsert_tool(
            ToolRecord(
                name=f"Tool-{idx}",
                official_website=f"https://tool{idx}.example.org",
                category="AI and Machine Learning",
                subcategory="AI agents and agent frameworks",
                short_description=f"Verified free AI tool #{idx}",
                free_plan_details="Open Source MIT",
                free_usage_limits="Unlimited local",
                credit_card_required="No",
                registration_required="No",
                open_source_status="Open Source (MIT)",
                api_availability="Free API",
                local_installation_available="Yes",
                official_documentation="https://docs.example.org",
                best_student_use_case="Hackathon prototype",
                canonical_key=f"web:tool{idx}.example.org",
                free_tier_type="Free Open Source",
                is_genuinely_free=True,
                india_available="Yes",
                score=95.0 - idx * 2,
                score_breakdown=ScoreBreakdown(free_functionality=24, total_score=95.0 - idx * 2),
                personalization=PersonalizationProfile(can_run_on_laptop="Yes (Native Windows 11)"),
            )
        )
    return db


def test_reports_generate_pdf_csv_xlsx_and_suppress_empty_notify(tmp_path):
    db = _seed_db(tmp_path)
    rep = ReportGenerationAgent(db, reports_dir=tmp_path / "reports")

    csv_p = rep.export_csv()
    xlsx_p = rep.export_excel()
    weekly = rep.generate_weekly_report("2026-W46")

    assert csv_p.exists() and csv_p.stat().st_size > 100
    assert xlsx_p.exists() and xlsx_p.stat().st_size > 1000
    assert Path(weekly["pdf_path"]).exists() and Path(weekly["pdf_path"]).stat().st_size > 1500
    assert len(weekly["top_10"]) == 4

    # Empty daily notification must be suppressed
    notifier = NotificationManager(RuntimeConfig(), db)
    empty_digest = rep.build_daily_digest([])
    res = notifier.notify_daily(empty_digest)
    assert res["suppressed"] is True


def test_flask_api_endpoints(tmp_path):
    db = _seed_db(tmp_path)
    app = create_app(db=db, config=RuntimeConfig())
    client = app.test_client()

    r_health = client.get("/api/health")
    assert r_health.status_code == 200

    r_cat = client.get("/api/catalog")
    assert r_cat.status_code == 200
    data = r_cat.get_json()
    assert data["stats"]["total_tools"] == 4

    r_save = client.post("/api/tools/save", json={"canonical_key": "web:tool1.example.org", "saved": True})
    assert r_save.status_code == 200
    assert r_save.get_json()["saved"] is True

    r_csv = client.get("/api/export/csv")
    assert r_csv.status_code == 200
    assert b"Tool-1" in r_csv.data
