"""Agent 8: ReportGenerationAgent — Daily Digests, Weekly Top 10 Intelligence, PDF, CSV & Excel."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..config import DOCS_DIR, REPORTS_DIR
from ..database import PramanaDatabase
from ..models import today_iso, utc_now_iso


# Editorial Color Palette (Apple / Pentagram-inspired: rich obsidian & slate, never harsh #000)
INK_PRIMARY = colors.HexColor("#0F172A")
INK_MUTED = colors.HexColor("#475569")
ACCENT_COBALT = colors.HexColor("#1D4ED8")
ACCENT_EMERALD = colors.HexColor("#047857")
SURFACE_SUBTLE = colors.HexColor("#F8FAFC")
BORDER_HAIRLINE = colors.HexColor("#CBD5E1")


def current_week_label() -> str:
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


class ReportGenerationAgent:
    """Generates Daily Digests, 16-section Weekly Intelligence Reports, PDFs, CSV & XLSX."""

    def __init__(self, db: PramanaDatabase, reports_dir: Path = REPORTS_DIR) -> None:
        self.db = db
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def build_daily_digest(self, new_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        top_three = sorted(new_tools, key=lambda x: x.get("score", 0), reverse=True)[:3]
        if not top_three:
            return {
                "date": today_iso(),
                "has_discoveries": False,
                "tools": [],
                "markdown": "",
            }

        lines = [
            f"# Pramana Daily AI Discovery — {today_iso()}",
            "",
            f"Verified **{len(top_three)}** genuinely free AI tools today for your 3rd-Year CE & AI Engineering stack:",
            "",
        ]
        for idx, t in enumerate(top_three, 1):
            p = t.get("personalization", {})
            lines.extend(
                [
                    f"## {idx}. {t['name']} — Score {t['score']}/100",
                    f"- **Category**: {t['category']} › {t['subcategory']}",
                    f"- **Official Link**: {t['official_website']}",
                    f"- **Free Verification**: {t['free_tier_type']} | Credit Card: `{t['credit_card_required']}` | India: `{t['india_available']}`",
                    f"- **Free Limits**: {t['free_usage_limits']}",
                    f"- **Why Useful**: {t['what_makes_it_useful']}",
                    f"- **RTX 4050 (6GB VRAM) Fit**: {p.get('can_run_on_laptop', 'UNKNOWN')}",
                    f"- **Student Use Case**: {t['best_student_use_case']}",
                    "",
                ]
            )
        md_text = "\n".join(lines)
        daily_file = self.reports_dir / f"daily-{today_iso()}.md"
        daily_file.write_text(md_text, encoding="utf-8")

        return {
            "date": today_iso(),
            "has_discoveries": True,
            "tools": top_three,
            "markdown": md_text,
            "markdown_path": str(daily_file),
        }

    def export_csv(self, filename: str = "pramana_tools_export.csv") -> Path:
        tools = self.db.list_tools()
        out = self.reports_dir / filename
        headers = [
            "Name", "Score", "Category", "Subcategory", "Official Website",
            "Free Tier Type", "Genuinely Free", "Credit Card Required",
            "Registration Required", "Open Source Status", "GitHub Repository",
            "API Availability", "Local Install", "RTX 4050 Fit", "India Available",
            "Free Plan Details", "Free Usage Limits", "Best Student Use Case",
            "Discovery Date", "Last Verification Date", "Status",
        ]
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for t in tools:
                p = t.get("personalization", {})
                writer.writerow([
                    t["name"], t["score"], t["category"], t["subcategory"], t["official_website"],
                    t["free_tier_type"], "Yes" if t["is_genuinely_free"] else "No",
                    t["credit_card_required"], t["registration_required"],
                    t["open_source_status"], t["github_repository"],
                    t["api_availability"], t["local_installation_available"],
                    p.get("can_run_on_laptop", "UNKNOWN"), t["india_available"],
                    t["free_plan_details"], t["free_usage_limits"], t["best_student_use_case"],
                    t["discovery_date"], t["last_verification_date"], t["status"],
                ])
        if self.reports_dir.resolve() == REPORTS_DIR.resolve():
            docs_rep = DOCS_DIR / "reports"
            docs_rep.mkdir(parents=True, exist_ok=True)
            (docs_rep / filename).write_bytes(out.read_bytes())
        return out

    def export_excel(self, filename: str = "pramana_tools_export.xlsx") -> Path:
        tools = self.db.list_tools()
        out = self.reports_dir / filename
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Verified Free AI Tools"

        headers = [
            "Name", "Score (/100)", "Category", "Subcategory", "Official Website",
            "Free Tier Type", "Credit Card?", "Open Source", "GitHub Repo",
            "API Availability", "RTX 4050 6GB Fit", "Free Usage Limits",
            "Best Student Use Case", "Verified Date",
        ]
        header_fill = PatternFill("solid", fgColor="0F172A")
        header_font = Font(color="FFFFFF", bold=True, size=10)
        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for t in tools:
            p = t.get("personalization", {})
            ws.append([
                t["name"], t["score"], t["category"], t["subcategory"], t["official_website"],
                t["free_tier_type"], t["credit_card_required"], t["open_source_status"],
                t["github_repository"], t["api_availability"],
                p.get("can_run_on_laptop", "UNKNOWN"), t["free_usage_limits"],
                t["best_student_use_case"], t["last_verification_date"],
            ])

        widths = [24, 12, 24, 24, 34, 20, 12, 22, 34, 22, 26, 40, 42, 14]
        for idx, w in enumerate(widths, 1):
            col_letter = openpyxl.utils.get_column_letter(idx)
            ws.column_dimensions[col_letter].width = w
        ws.freeze_panes = "A2"

        # Sheet 2: Pricing History
        ws_hist = wb.create_sheet("Pricing History")
        ws_hist.append(["Tool Name", "Change Type", "Old Plan", "New Plan", "Detected At", "Source URL"])
        for h in self.db.get_pricing_history(100):
            ws_hist.append([
                h["tool_name"], h["change_type"], h["old_free_plan"],
                h["new_free_plan"], h["detected_at"], h["source_url"],
            ])

        wb.save(out)
        if self.reports_dir.resolve() == REPORTS_DIR.resolve():
            docs_rep = DOCS_DIR / "reports"
            docs_rep.mkdir(parents=True, exist_ok=True)
            (docs_rep / filename).write_bytes(out.read_bytes())
        return out

    def generate_weekly_report(self, week_label: str | None = None) -> Dict[str, Any]:
        week_label = week_label or current_week_label()
        all_tools = self.db.list_tools(only_free=True)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        newly_discovered = [t for t in all_tools if t.get("discovery_date", "") >= cutoff]
        if not newly_discovered:
            newly_discovered = all_tools[:10]

        pricing_hist = self.db.get_pricing_history(limit=80)
        reduced_or_removed = [h for h in pricing_hist if h["change_type"] in ("reduced", "removed")]
        newly_free_or_improved = [h for h in pricing_hist if h["change_type"] in ("improved", "updated")]
        discontinued = self.db.list_tools(status="discontinued")

        def by_sub_or_cat(cat_substr: str, sub_substr: str = "", limit: int = 5) -> List[Dict[str, Any]]:
            matches = [
                t for t in all_tools
                if cat_substr.lower() in t["category"].lower()
                and (not sub_substr or sub_substr.lower() in t["subcategory"].lower() or sub_substr.lower() in t["short_description"].lower())
            ]
            return matches[:limit]

        top_10 = all_tools[:10]

        sections = {
            "Best Newly Discovered Free AI Tools": newly_discovered[:6],
            "Best Free Coding Assistants": by_sub_or_cat("Coding", "assistant") or by_sub_or_cat("Coding"),
            "Best Free AI APIs and LLMs": by_sub_or_cat("AI and Machine Learning", "API") or by_sub_or_cat("AI and Machine Learning", "LLM"),
            "Best Video Editing and Generation Tools": by_sub_or_cat("Video"),
            "Best Image Generation Tools": by_sub_or_cat("Image"),
            "Best Voice and Audio Tools": by_sub_or_cat("Audio"),
            "Best AI Agent Frameworks": by_sub_or_cat("AI and Machine Learning", "agent") or by_sub_or_cat("Emerging", "MCP"),
            "Best Productivity Tools": by_sub_or_cat("Productivity"),
            "Best Research and Educational Tools": by_sub_or_cat("Career and Education") + by_sub_or_cat("Productivity", "research", 2),
            "Best Tools for Students (Zero Budget + RTX 4050)": [
                t for t in all_tools
                if t.get("personalization", {}).get("helps_ai_engineering_career")
            ][:6],
            "Newly Released Open-Source Projects": [
                t for t in newly_discovered
                if str(t.get("open_source_status", "")).startswith("Open Source")
            ][:6],
            "Significant Updates to Existing Tools": newly_free_or_improved[:5],
            "Newly Available Free Plans": newly_free_or_improved[:5],
            "Tools That Reduced or Removed Free Plans": reduced_or_removed[:5],
            "Discontinued Tools": discontinued[:5],
            "Emerging AI Technologies Worth Watching": by_sub_or_cat("Emerging AI"),
        }

        # Build Markdown
        md_lines = [
            f"# Pramana Weekly AI Intelligence Report — {week_label}",
            f"_Generated: {utc_now_iso()} | Tailored for 3rd-Year Computer Engineering (Windows 11, Ryzen 7 7435HS, 16GB RAM, RTX 4050 6GB VRAM)_",
            "",
            "---",
            "",
            "## Weekly Top 10 Ranked Free AI Tools",
            "",
        ]
        for rank, t in enumerate(top_10, 1):
            bd = t.get("score_breakdown", {})
            p = t.get("personalization", {})
            why = (
                f"Ranked #{rank} at **{t['score']}/100** ({t['free_tier_type']}). "
                f"Free access ({bd.get('free_functionality', '-')}/25), usefulness ({bd.get('practical_usefulness', '-')}/20), "
                f"reliability ({bd.get('reliability', '-')}/15), and student impact ({bd.get('student_value', '-')}/15). "
                f"{p.get('hardware_fit_notes', '')}"
            )
            md_lines.extend([
                f"### #{rank}. {t['name']} — {t['score']}/100",
                f"- **Official URL**: {t['official_website']}",
                f"- **Category**: {t['category']} › {t['subcategory']}",
                f"- **Why It Deserves #{rank}**: {why}",
                f"- **Best Student Action**: {t['best_student_use_case']}",
                "",
            ])

        md_lines.extend(["---", "", "## Category & Ecosystem Intelligence", ""])
        for sec_title, items in sections.items():
            md_lines.append(f"### {sec_title}")
            if not items:
                md_lines.append("- No new changes detected in this window.")
            else:
                for item in items:
                    if "official_website" in item:
                        md_lines.append(
                            f"- **{item['name']}** ({item['score']}/100, {item['free_tier_type']}) — {item['short_description']} [{item['official_website']}]"
                        )
                    else:
                        md_lines.append(
                            f"- **{item.get('tool_name', 'Tool')}**: {item.get('change_type', 'update')} — {item.get('new_free_plan', '')}"
                        )
            md_lines.append("")

        md_path = self.reports_dir / f"weekly-{week_label}.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        json_payload = {
            "week_label": week_label,
            "generated_at": utc_now_iso(),
            "top_10": top_10,
            "sections": {
                k: [
                    {"name": i.get("name") or i.get("tool_name"), "score": i.get("score"), "url": i.get("official_website") or i.get("source_url"), "summary": i.get("short_description") or i.get("new_free_plan")}
                    for i in v
                ]
                for k, v in sections.items()
            },
        }
        json_path = self.reports_dir / f"weekly-{week_label}.json"
        json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

        pdf_path = self._render_weekly_pdf(week_label, top_10, sections)

        # Mirror latest PDF & markdown to docs/reports for GitHub Pages download
        if self.reports_dir.resolve() == REPORTS_DIR.resolve():
            docs_rep = DOCS_DIR / "reports"
            docs_rep.mkdir(parents=True, exist_ok=True)
            (docs_rep / "latest-weekly-report.pdf").write_bytes(pdf_path.read_bytes())
            (docs_rep / "latest-weekly-report.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

        self.db.save_weekly_report_meta(
            week_label=week_label,
            markdown_path=str(md_path),
            pdf_path=str(pdf_path),
            json_path=str(json_path),
            top_10_keys=[t["canonical_key"] for t in top_10],
            highlights={"total_verified": len(all_tools), "new_this_week": len(newly_discovered)},
        )

        # Refresh CSV and XLSX alongside weekly report
        self.export_csv()
        self.export_excel()

        return {
            "week_label": week_label,
            "markdown_path": str(md_path),
            "pdf_path": str(pdf_path),
            "json_path": str(json_path),
            "top_10": top_10,
            "markdown": "\n".join(md_lines),
        }

    def _render_weekly_pdf(
        self,
        week_label: str,
        top_10: List[Dict[str, Any]],
        sections: Dict[str, List[Dict[str, Any]]],
    ) -> Path:
        pdf_path = self.reports_dir / f"weekly-{week_label}.pdf"
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"Pramana Weekly AI Intelligence — {week_label}",
        )
        base = getSampleStyleSheet()
        h1 = ParagraphStyle("PramanaH1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=20, textColor=INK_PRIMARY, spaceAfter=6)
        sub = ParagraphStyle("PramanaSub", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, textColor=INK_MUTED, spaceAfter=14)
        h2 = ParagraphStyle("PramanaH2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=ACCENT_COBALT, spaceBefore=12, spaceAfter=6)
        body = ParagraphStyle("PramanaBody", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INK_PRIMARY, spaceAfter=5)
        small = ParagraphStyle("PramanaSmall", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=INK_MUTED)

        story: List[Any] = [
            Paragraph(f"PRAMANA WEEKLY AI INTELLIGENCE — {week_label}", h1),
            Paragraph(
                "Autonomous Free AI Tools Discovery & Verification Department • Tailored for 3rd-Yr Computer Engineering "
                "(Windows 11 • Ryzen 7 7435HS • 16GB RAM • RTX 4050 6GB VRAM)",
                sub,
            ),
            HRFlowable(width="100%", thickness=0.75, color=BORDER_HAIRLINE, spaceAfter=12),
            Paragraph("Weekly Top 10 Verified Free AI Tools", h2),
        ]

        table_rows = [["#", "Tool", "Category", "Free Tier", "Score", "RTX 4050 Fit"]]
        for rank, t in enumerate(top_10, 1):
            fit = t.get("personalization", {}).get("can_run_on_laptop", "UNKNOWN")
            table_rows.append([
                str(rank),
                Paragraph(f"<b>{t['name']}</b>", small),
                Paragraph(t["category"], small),
                Paragraph(t["free_tier_type"], small),
                f"{t['score']}/100",
                Paragraph(fit[:28], small),
            ])

        tbl = Table(table_rows, colWidths=[0.35 * inch, 1.35 * inch, 1.45 * inch, 1.25 * inch, 0.7 * inch, 1.45 * inch])
        tbl.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), INK_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE_SUBTLE]),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER_HAIRLINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(tbl)
        story.append(Spacer(1, 12))

        for rank, t in enumerate(top_10[:5], 1):
            p = t.get("personalization", {})
            story.append(Paragraph(f"<b>#{rank} {t['name']} ({t['score']}/100)</b> — {t['official_website']}", body))
            story.append(Paragraph(f"{t['short_description']} <i>Use Case:</i> {t['best_student_use_case']} ({p.get('hardware_fit_notes', '')})", small))
            story.append(Spacer(1, 4))

        story.append(PageBreak())
        story.append(Paragraph("Ecosystem Breakdown (All 16 Intelligence Categories)", h2))
        for sec_title, items in sections.items():
            story.append(Paragraph(f"<b>{sec_title}</b>", body))
            if not items:
                story.append(Paragraph("• No significant changes recorded in this cycle.", small))
            else:
                for item in items[:4]:
                    nm = item.get("name") or item.get("tool_name", "Tool")
                    desc = item.get("short_description") or item.get("new_free_plan", "")
                    url = item.get("official_website") or item.get("source_url", "")
                    story.append(Paragraph(f"• <b>{nm}</b>: {desc[:150]} ({url})", small))
            story.append(Spacer(1, 5))

        doc.build(story)
        return pdf_path
