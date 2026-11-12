"""Flask REST API & Dashboard server for Pramana AI Radar."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request, send_file, send_from_directory

from .agents import OrchestratorAgent, ReportGenerationAgent
from .config import (
    CATEGORY_TAXONOMY,
    DASHBOARD_DIR,
    REPORTS_DIR,
    RuntimeConfig,
    STUDENT_PROFILE,
    load_dotenv_if_present,
)
from .database import PramanaDatabase


def create_app(db: PramanaDatabase | None = None, config: RuntimeConfig | None = None) -> Flask:
    load_dotenv_if_present()
    cfg = config or RuntimeConfig()
    database = db or PramanaDatabase()
    reporter = ReportGenerationAgent(database)

    app = Flask(__name__, static_folder=str(DASHBOARD_DIR), static_url_path="")

    @app.get("/")
    def index() -> Any:
        return send_from_directory(str(DASHBOARD_DIR), "index.html")

    @app.get("/api/health")
    def health() -> Any:
        return jsonify({"status": "ok", "service": "Pramana AI Radar"})

    @app.get("/api/catalog")
    def catalog() -> Any:
        tools = database.list_tools()
        return jsonify(
            {
                "stats": {
                    "total_tools": len(tools),
                    "genuinely_free": sum(1 for t in tools if t["is_genuinely_free"]),
                    "open_source": sum(
                        1 for t in tools if str(t["open_source_status"]).startswith("Open Source")
                    ),
                    "free_api_count": sum(
                        1
                        for t in tools
                        if "Free" in str(t["api_availability"]) or "Local" in str(t["api_availability"])
                    ),
                    "average_score": round(sum(t["score"] for t in tools) / len(tools), 1)
                    if tools
                    else 0.0,
                },
                "profile": {
                    "academic_year": STUDENT_PROFILE.academic_year,
                    "country": STUDENT_PROFILE.country,
                    "hardware": {
                        "os": STUDENT_PROFILE.hardware.os_name,
                        "cpu": STUDENT_PROFILE.hardware.cpu,
                        "ram_gb": STUDENT_PROFILE.hardware.ram_gb,
                        "gpu": STUDENT_PROFILE.hardware.gpu_name,
                        "vram_gb": STUDENT_PROFILE.hardware.vram_gb,
                    },
                },
                "taxonomy": CATEGORY_TAXONOMY,
                "tools": tools,
                "pricing_history": database.get_pricing_history(limit=120),
                "discovery_runs": database.get_discovery_runs(limit=25),
                "rejected_candidates": database.get_rejected_candidates(limit=50),
                "weekly_reports": database.get_weekly_reports(limit=10),
                "settings": database.get_all_settings(),
            }
        )

    @app.get("/api/tools")
    def list_tools() -> Any:
        category = request.args.get("category")
        only_free = request.args.get("only_free", "false").lower() == "true"
        only_os = request.args.get("only_open_source", "false").lower() == "true"
        only_saved = request.args.get("only_saved", "false").lower() == "true"
        search = request.args.get("search")
        return jsonify(
            {
                "tools": database.list_tools(
                    category=category,
                    only_free=only_free,
                    only_open_source=only_os,
                    only_saved=only_saved,
                    search=search,
                )
            }
        )

    @app.post("/api/tools/save")
    def save_tool() -> Any:
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        key = str(body.get("canonical_key", ""))
        saved = bool(body.get("saved", True))
        ok = database.set_saved(key, saved)
        if ok:
            database.export_catalog_snapshot()
        return jsonify({"ok": ok, "canonical_key": key, "saved": saved}), (200 if ok else 404)

    @app.post("/api/tools/rate")
    def rate_tool() -> Any:
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        key = str(body.get("canonical_key", ""))
        rating = int(body.get("rating", 5))
        ok = database.set_rating(key, rating)
        if ok:
            database.export_catalog_snapshot()
        return jsonify({"ok": ok, "canonical_key": key, "rating": rating}), (200 if ok else 404)

    @app.get("/api/settings")
    def get_settings() -> Any:
        return jsonify({"settings": database.get_all_settings()})

    @app.post("/api/settings")
    def update_settings() -> Any:
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        for k, v in body.items():
            database.set_setting(str(k), str(v))
        return jsonify({"ok": True, "settings": database.get_all_settings()})

    @app.post("/api/run/daily")
    def trigger_daily() -> Any:
        orch = OrchestratorAgent(database, cfg)
        res = orch.run_daily(send_notifications=False)
        return jsonify(
            {
                "ok": True,
                "status": res.status,
                "new_tools_added": res.new_tools_added,
                "rejected_fake_free": res.rejected_fake_free,
                "duplicates_skipped": res.duplicates_skipped,
                "sources_succeeded": res.sources_succeeded,
                "sources_failed": res.sources_failed,
            }
        )

    @app.post("/api/run/weekly")
    def trigger_weekly() -> Any:
        orch = OrchestratorAgent(database, cfg)
        res = orch.run_weekly(send_notifications=False)
        return jsonify(
            {
                "ok": True,
                "status": res.status,
                "week_label": res.weekly_report.get("week_label") if res.weekly_report else "",
                "new_tools_added": res.new_tools_added,
            }
        )

    @app.get("/api/export/csv")
    def export_csv() -> Any:
        path = reporter.export_csv()
        return send_file(str(path), as_attachment=True, download_name=path.name)

    @app.get("/api/export/xlsx")
    def export_xlsx() -> Any:
        path = reporter.export_excel()
        return send_file(str(path), as_attachment=True, download_name=path.name)

    @app.get("/api/export/pdf")
    def export_pdf() -> Any:
        pdfs = sorted(REPORTS_DIR.glob("weekly-*.pdf"))
        if not pdfs:
            weekly = reporter.generate_weekly_report()
            pdf_path = Path(weekly["pdf_path"])
        else:
            pdf_path = pdfs[-1]
        return send_file(str(pdf_path), as_attachment=True, download_name=pdf_path.name)

    return app


def run_server(port: int | None = None) -> None:
    load_dotenv_if_present()
    cfg = RuntimeConfig()
    app = create_app(config=cfg)
    app.run(host="127.0.0.1", port=port or cfg.dashboard_port, debug=False)
