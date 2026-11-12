"""Persistent SQLite database, history tracking, backups, and static JSON sync."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .config import BACKUPS_DIR, CATALOG_JSON_PATH, DATA_DIR, DB_PATH, DOCS_DIR
from .models import (
    PersonalizationProfile,
    ScoreBreakdown,
    ToolRecord,
    utc_now_iso,
)


SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    official_website TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    short_description TEXT NOT NULL,
    main_capabilities TEXT NOT NULL,      -- JSON list
    what_makes_it_useful TEXT NOT NULL,
    free_plan_details TEXT NOT NULL,
    free_usage_limits TEXT NOT NULL,
    credit_card_required TEXT NOT NULL,
    registration_required TEXT NOT NULL,
    open_source_status TEXT NOT NULL,
    github_repository TEXT NOT NULL,
    supported_os TEXT NOT NULL,           -- JSON list
    api_availability TEXT NOT NULL,
    local_installation_available TEXT NOT NULL,
    important_limitations TEXT NOT NULL,  -- JSON list
    privacy_considerations TEXT NOT NULL,
    last_verification_date TEXT NOT NULL,
    official_documentation TEXT NOT NULL,
    best_student_use_case TEXT NOT NULL,
    free_tier_type TEXT NOT NULL,
    is_genuinely_free INTEGER NOT NULL DEFAULT 1,
    india_available TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    score_breakdown TEXT NOT NULL,        -- JSON dict
    personalization TEXT NOT NULL,        -- JSON dict
    sources TEXT NOT NULL,                -- JSON list
    tags TEXT NOT NULL,                   -- JSON list
    stars INTEGER NOT NULL DEFAULT 0,
    license_name TEXT NOT NULL,
    discovery_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    user_rating INTEGER,
    is_saved INTEGER NOT NULL DEFAULT 0,
    previous_pricing_info TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
CREATE INDEX IF NOT EXISTS idx_tools_score ON tools(score DESC);
CREATE INDEX IF NOT EXISTS idx_tools_discovery_date ON tools(discovery_date DESC);
CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);

CREATE TABLE IF NOT EXISTS pricing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    old_free_plan TEXT NOT NULL,
    new_free_plan TEXT NOT NULL,
    old_limits TEXT NOT NULL,
    new_limits TEXT NOT NULL,
    change_type TEXT NOT NULL, -- 'initial' | 'improved' | 'reduced' | 'removed' | 'updated' | 'discontinued'
    source_url TEXT NOT NULL,
    detected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pricing_history_key ON pricing_history(canonical_key);
CREATE INDEX IF NOT EXISTS idx_pricing_history_date ON pricing_history(detected_at DESC);

CREATE TABLE IF NOT EXISTS discovery_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL, -- 'daily' | 'weekly' | 'verify'
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,   -- 'running' | 'success' | 'partial' | 'failed'
    candidates_scanned INTEGER NOT NULL DEFAULT 0,
    new_tools_added INTEGER NOT NULL DEFAULT 0,
    rejected_fake_free INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped INTEGER NOT NULL DEFAULT 0,
    pricing_changes_detected INTEGER NOT NULL DEFAULT 0,
    sources_succeeded TEXT NOT NULL DEFAULT '[]',
    sources_failed TEXT NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS weekly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_label TEXT NOT NULL UNIQUE,
    generated_at TEXT NOT NULL,
    markdown_path TEXT NOT NULL,
    pdf_path TEXT NOT NULL,
    json_path TEXT NOT NULL,
    top_10_keys TEXT NOT NULL, -- JSON list
    highlights TEXT NOT NULL   -- JSON dict
);

CREATE TABLE IF NOT EXISTS rejected_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    reason TEXT NOT NULL,
    fake_free_flags TEXT NOT NULL, -- JSON list
    rejected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class PramanaDatabase:
    """Thread-safe persistent store for discovered tools, history, and reports."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def create_backup(self, max_backups: int = 7) -> Optional[Path]:
        """Create a safe timestamped SQLite backup before write operations."""
        if not self.db_path.exists():
            return None
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_file = BACKUPS_DIR / f"pramana-{stamp}.db"
        shutil.copy2(self.db_path, backup_file)
        backups = sorted(BACKUPS_DIR.glob("pramana-*.db"))
        while len(backups) > max_backups:
            oldest = backups.pop(0)
            oldest.unlink(missing_ok=True)
        return backup_file

    def has_canonical_key(self, canonical_key: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM tools WHERE canonical_key = ? LIMIT 1",
                (canonical_key,),
            ).fetchone()
            return row is not None

    def get_all_canonical_keys(self) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT canonical_key FROM tools").fetchall()
            return {r["canonical_key"] for r in rows}

    def get_all_names_and_urls(self) -> List[Dict[str, str]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT canonical_key, name, official_website, github_repository FROM tools"
            ).fetchall()
            return [dict(r) for r in rows]

    def upsert_tool(self, tool: ToolRecord) -> str:
        """Insert a new tool or update an existing one while recording pricing history.

        Returns: 'inserted' | 'updated' | 'pricing_changed'
        """
        now = utc_now_iso()
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT * FROM tools WHERE canonical_key = ?",
                (tool.canonical_key,),
            ).fetchone()

            payload = {
                "canonical_key": tool.canonical_key,
                "name": tool.name,
                "official_website": tool.official_website,
                "category": tool.category,
                "subcategory": tool.subcategory,
                "short_description": tool.short_description,
                "main_capabilities": json.dumps(tool.main_capabilities),
                "what_makes_it_useful": tool.what_makes_it_useful,
                "free_plan_details": tool.free_plan_details,
                "free_usage_limits": tool.free_usage_limits,
                "credit_card_required": tool.credit_card_required,
                "registration_required": tool.registration_required,
                "open_source_status": tool.open_source_status,
                "github_repository": tool.github_repository,
                "supported_os": json.dumps(tool.supported_os),
                "api_availability": tool.api_availability,
                "local_installation_available": tool.local_installation_available,
                "important_limitations": json.dumps(tool.important_limitations),
                "privacy_considerations": tool.privacy_considerations,
                "last_verification_date": tool.last_verification_date,
                "official_documentation": tool.official_documentation,
                "best_student_use_case": tool.best_student_use_case,
                "free_tier_type": tool.free_tier_type,
                "is_genuinely_free": 1 if tool.is_genuinely_free else 0,
                "india_available": tool.india_available,
                "score": float(tool.score),
                "score_breakdown": json.dumps(
                    tool.score_breakdown.__dict__
                    if isinstance(tool.score_breakdown, ScoreBreakdown)
                    else tool.score_breakdown
                ),
                "personalization": json.dumps(
                    tool.personalization.__dict__
                    if isinstance(tool.personalization, PersonalizationProfile)
                    else tool.personalization
                ),
                "sources": json.dumps(tool.sources),
                "tags": json.dumps(tool.tags),
                "stars": int(tool.stars),
                "license_name": tool.license_name,
                "discovery_date": tool.discovery_date,
                "status": tool.status,
                "user_rating": tool.user_rating,
                "is_saved": 1 if tool.is_saved else 0,
                "previous_pricing_info": tool.previous_pricing_info,
                "updated_at": now,
            }

            if existing is None:
                payload["created_at"] = now
                cols = ", ".join(payload.keys())
                placeholders = ", ".join(f":{k}" for k in payload.keys())
                conn.execute(
                    f"INSERT INTO tools ({cols}) VALUES ({placeholders})",
                    payload,
                )
                conn.execute(
                    """
                    INSERT INTO pricing_history
                    (canonical_key, tool_name, old_free_plan, new_free_plan, old_limits, new_limits, change_type, source_url, detected_at)
                    VALUES (?, ?, '', ?, '', ?, 'initial', ?, ?)
                    """,
                    (
                        tool.canonical_key,
                        tool.name,
                        tool.free_plan_details,
                        tool.free_usage_limits,
                        tool.official_website,
                        now,
                    ),
                )
                return "inserted"

            # Preserve user-curated state on re-verification
            payload["is_saved"] = existing["is_saved"]
            payload["user_rating"] = existing["user_rating"]
            payload["discovery_date"] = existing["discovery_date"]

            old_plan = existing["free_plan_details"]
            old_limits = existing["free_usage_limits"]
            pricing_changed = (
                old_plan != tool.free_plan_details or old_limits != tool.free_usage_limits
            )
            if pricing_changed:
                payload["previous_pricing_info"] = f"{old_plan} | Limits: {old_limits}"
                change_type = "updated"
                if existing["is_genuinely_free"] == 1 and not tool.is_genuinely_free:
                    change_type = "removed"
                    payload["status"] = "pricing_changed"
                elif tool.status == "discontinued":
                    change_type = "discontinued"
                conn.execute(
                    """
                    INSERT INTO pricing_history
                    (canonical_key, tool_name, old_free_plan, new_free_plan, old_limits, new_limits, change_type, source_url, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tool.canonical_key,
                        tool.name,
                        old_plan,
                        tool.free_plan_details,
                        old_limits,
                        tool.free_usage_limits,
                        change_type,
                        tool.official_website,
                        now,
                    ),
                )

            assignments = ", ".join(f"{k} = :{k}" for k in payload.keys())
            conn.execute(
                f"UPDATE tools SET {assignments} WHERE canonical_key = :canonical_key",
                payload,
            )
            return "pricing_changed" if pricing_changed else "updated"

    def record_rejected(self, canonical_key: str, name: str, url: str, reason: str, flags: List[str]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO rejected_candidates (canonical_key, name, url, reason, fake_free_flags, rejected_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_key) DO UPDATE SET
                    reason = excluded.reason,
                    fake_free_flags = excluded.fake_free_flags,
                    rejected_at = excluded.rejected_at
                """,
                (canonical_key, name, url, reason, json.dumps(flags), utc_now_iso()),
            )

    def start_run(self, run_type: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO discovery_runs (run_type, started_at, status) VALUES (?, ?, 'running')",
                (run_type, utc_now_iso()),
            )
            return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        candidates_scanned: int,
        new_tools_added: int,
        rejected_fake_free: int,
        duplicates_skipped: int,
        pricing_changes_detected: int,
        sources_succeeded: List[str],
        sources_failed: List[str],
        summary: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE discovery_runs SET
                    finished_at = ?,
                    status = ?,
                    candidates_scanned = ?,
                    new_tools_added = ?,
                    rejected_fake_free = ?,
                    duplicates_skipped = ?,
                    pricing_changes_detected = ?,
                    sources_succeeded = ?,
                    sources_failed = ?,
                    summary = ?
                WHERE id = ?
                """,
                (
                    utc_now_iso(),
                    status,
                    candidates_scanned,
                    new_tools_added,
                    rejected_fake_free,
                    duplicates_skipped,
                    pricing_changes_detected,
                    json.dumps(sources_succeeded),
                    json.dumps(sources_failed),
                    summary,
                    run_id,
                ),
            )

    def save_weekly_report_meta(
        self,
        week_label: str,
        markdown_path: str,
        pdf_path: str,
        json_path: str,
        top_10_keys: List[str],
        highlights: Dict[str, Any],
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO weekly_reports (week_label, generated_at, markdown_path, pdf_path, json_path, top_10_keys, highlights)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(week_label) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    markdown_path = excluded.markdown_path,
                    pdf_path = excluded.pdf_path,
                    json_path = excluded.json_path,
                    top_10_keys = excluded.top_10_keys,
                    highlights = excluded.highlights
                """,
                (
                    week_label,
                    utc_now_iso(),
                    markdown_path,
                    pdf_path,
                    json_path,
                    json.dumps(top_10_keys),
                    json.dumps(highlights),
                ),
            )

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for json_col in (
            "main_capabilities",
            "supported_os",
            "important_limitations",
            "score_breakdown",
            "personalization",
            "sources",
            "tags",
        ):
            try:
                d[json_col] = json.loads(d[json_col])
            except Exception:
                pass
        d["is_genuinely_free"] = bool(d["is_genuinely_free"])
        d["is_saved"] = bool(d["is_saved"])
        return d

    def list_tools(
        self,
        *,
        category: Optional[str] = None,
        only_free: bool = False,
        only_open_source: bool = False,
        only_saved: bool = False,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []
        if category and category.lower() != "all":
            clauses.append("category = ?")
            params.append(category)
        if only_free:
            clauses.append("is_genuinely_free = 1")
        if only_open_source:
            clauses.append("open_source_status LIKE 'Open Source%'")
        if only_saved:
            clauses.append("is_saved = 1")
        if status:
            clauses.append("status = ?")
            params.append(status)
        if search:
            q = f"%{search.lower()}%"
            clauses.append(
                "(LOWER(name) LIKE ? OR LOWER(short_description) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(subcategory) LIKE ?)"
            )
            params.extend([q, q, q, q])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        limit_sql = f"LIMIT {int(limit)}" if limit else ""
        sql = f"SELECT * FROM tools {where_sql} ORDER BY score DESC, discovery_date DESC {limit_sql}"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_tool(self, canonical_key: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM tools WHERE canonical_key = ?", (canonical_key,)
            ).fetchone()
            return self._row_to_dict(row) if row else None

    def set_saved(self, canonical_key: str, saved: bool) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE tools SET is_saved = ?, updated_at = ? WHERE canonical_key = ?",
                (1 if saved else 0, utc_now_iso(), canonical_key),
            )
            return cur.rowcount > 0

    def set_rating(self, canonical_key: str, rating: int) -> bool:
        clamped = max(1, min(5, int(rating)))
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE tools SET user_rating = ?, updated_at = ? WHERE canonical_key = ?",
                (clamped, utc_now_iso(), canonical_key),
            )
            return cur.rowcount > 0

    def get_pricing_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM pricing_history ORDER BY detected_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_discovery_runs(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM discovery_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                for col in ("sources_succeeded", "sources_failed"):
                    try:
                        d[col] = json.loads(d[col])
                    except Exception:
                        pass
                out.append(d)
            return out

    def get_rejected_candidates(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM rejected_candidates ORDER BY rejected_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["fake_free_flags"] = json.loads(d["fake_free_flags"])
                except Exception:
                    pass
                out.append(d)
            return out

    def get_weekly_reports(self, limit: int = 12) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM weekly_reports ORDER BY generated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                for col in ("top_10_keys", "highlights"):
                    try:
                        d[col] = json.loads(d[col])
                    except Exception:
                        pass
                out.append(d)
            return out

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, utc_now_iso()),
            )

    def get_all_settings(self) -> Dict[str, str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {r["key"]: r["value"] for r in rows}

    def export_catalog_snapshot(self, target_path: Path = CATALOG_JSON_PATH) -> Path:
        """Export complete database snapshot for static GitHub Pages & zero-backend dashboards."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tools = self.list_tools()
        snapshot = {
            "generated_at": utc_now_iso(),
            "stats": {
                "total_tools": len(tools),
                "genuinely_free": sum(1 for t in tools if t["is_genuinely_free"]),
                "open_source": sum(
                    1 for t in tools if str(t["open_source_status"]).startswith("Open Source")
                ),
                "free_api_count": sum(
                    1 for t in tools if "Free" in str(t["api_availability"]) or "Local" in str(t["api_availability"])
                ),
                "average_score": round(
                    sum(t["score"] for t in tools) / len(tools), 1
                )
                if tools
                else 0.0,
            },
            "tools": tools,
            "pricing_history": self.get_pricing_history(limit=120),
            "discovery_runs": self.get_discovery_runs(limit=20),
            "rejected_candidates": self.get_rejected_candidates(limit=40),
            "weekly_reports": self.get_weekly_reports(limit=8),
        }
        text = json.dumps(snapshot, indent=2, ensure_ascii=False)
        target_path.write_text(text, encoding="utf-8")
        # Also mirror into docs/data/catalog.json for GitHub Pages static deployment
        docs_data = DOCS_DIR / "data"
        docs_data.mkdir(parents=True, exist_ok=True)
        (docs_data / "catalog.json").write_text(text, encoding="utf-8")
        return target_path
