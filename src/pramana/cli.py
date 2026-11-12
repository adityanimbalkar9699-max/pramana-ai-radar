"""Command-line interface for Pramana AI Radar (used locally and in GitHub Actions)."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys

from .agents import OrchestratorAgent, ReportGenerationAgent
from .config import DASHBOARD_DIR, DOCS_DIR, RuntimeConfig, load_dotenv_if_present
from .database import PramanaDatabase
from .server import run_server


def sync_static_pages(db: PramanaDatabase) -> None:
    """Copy dashboard assets and exported data/reports into docs/ for GitHub Pages."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for fname in ("index.html", "styles.css", "app.js"):
        src = DASHBOARD_DIR / fname
        if src.exists():
            shutil.copy2(src, DOCS_DIR / fname)
    db.export_catalog_snapshot()


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        prog="pramana",
        description="Pramana AI Radar — Autonomous Free AI Tools Discovery & Intelligence System",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_daily = sub.add_parser("daily", help="Run daily autonomous discovery, verification & notifications")
    p_daily.add_argument("--target", type=int, default=None, help="Target number of new tools")
    p_daily.add_argument("--no-notify", action="store_true", help="Suppress Telegram/Email delivery")

    p_weekly = sub.add_parser("weekly", help="Run weekly deep intelligence report, Top 10, PDF/CSV/XLSX")
    p_weekly.add_argument("--no-notify", action="store_true", help="Suppress Telegram/Email delivery")

    sub.add_parser("export", help="Export catalog JSON, CSV, XLSX, and sync GitHub Pages docs/")

    p_serve = sub.add_parser("serve", help="Launch local dashboard & REST API server")
    p_serve.add_argument("--port", type=int, default=None, help="Port to listen on")

    sub.add_parser("doctor", help="Inspect DB health, sources, and configuration")

    args = parser.parse_args(argv)
    cfg = RuntimeConfig()
    db = PramanaDatabase()

    if args.command == "daily":
        orch = OrchestratorAgent(db, cfg)
        res = orch.run_daily(
            target_new=args.target,
            bootstrap_if_empty=True,
            send_notifications=not args.no_notify,
        )
        sync_static_pages(db)
        print(json.dumps({
            "status": res.status,
            "candidates_scanned": res.candidates_scanned,
            "new_tools_added": res.new_tools_added,
            "rejected_fake_free": res.rejected_fake_free,
            "duplicates_skipped": res.duplicates_skipped,
            "pricing_changes_detected": res.pricing_changes_detected,
            "sources_succeeded": res.sources_succeeded,
            "sources_failed": res.sources_failed,
            "emerging_categories": res.emerging_categories,
        }, indent=2))
        return 0

    if args.command == "weekly":
        orch = OrchestratorAgent(db, cfg)
        res = orch.run_weekly(send_notifications=not args.no_notify)
        sync_static_pages(db)
        print(json.dumps({
            "status": res.status,
            "week_label": res.weekly_report.get("week_label") if res.weekly_report else "",
            "pdf_path": res.weekly_report.get("pdf_path") if res.weekly_report else "",
            "new_tools_added": res.new_tools_added,
            "total_tools_in_db": len(db.list_tools()),
        }, indent=2))
        return 0

    if args.command == "export":
        rep = ReportGenerationAgent(db)
        csv_p = rep.export_csv()
        xlsx_p = rep.export_excel()
        weekly = rep.generate_weekly_report()
        sync_static_pages(db)
        print(json.dumps({
            "csv": str(csv_p),
            "xlsx": str(xlsx_p),
            "pdf": weekly["pdf_path"],
            "docs_synced": True,
        }, indent=2))
        return 0

    if args.command == "serve":
        sync_static_pages(db)
        run_server(port=args.port)
        return 0

    if args.command == "doctor":
        tools = db.list_tools()
        print(json.dumps({
            "db_path": str(db.db_path),
            "total_tools": len(tools),
            "genuinely_free": sum(1 for t in tools if t["is_genuinely_free"]),
            "telegram_configured": bool(cfg.telegram_bot_token and cfg.telegram_chat_id),
            "email_configured": bool(cfg.smtp_user and cfg.smtp_pass and cfg.notify_email_to),
            "github_token_configured": bool(cfg.github_token),
        }, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
