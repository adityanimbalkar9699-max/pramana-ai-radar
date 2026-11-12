"""Configurable Telegram & SMTP Email notification delivery with anti-noise suppression."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .config import RuntimeConfig
from .database import PramanaDatabase

logger = logging.getLogger(__name__)


class NotificationManager:
    """Delivers daily, weekly, and failure notifications via configured free channels."""

    def __init__(self, config: RuntimeConfig, db: Optional[PramanaDatabase] = None) -> None:
        self.config = config
        self.db = db

    def _is_channel_enabled(self, channel_key: str, default: bool = True) -> bool:
        if not self.db:
            return default
        val = self.db.get_setting(channel_key, "true" if default else "false").lower()
        return val in ("true", "1", "yes", "on")

    def send_telegram(self, text: str) -> bool:
        token = self.config.telegram_bot_token
        chat_id = self.config.telegram_chat_id
        if not token or not chat_id:
            return False
        if not self._is_channel_enabled("notify_telegram_enabled", True):
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        # Telegram max message length is 4096 chars
        chunks = [text[i : i + 3900] for i in range(0, len(text), 3900)] or [text]
        all_ok = True
        for chunk in chunks:
            try:
                resp = requests.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": chunk,
                        "disable_web_page_preview": True,
                    },
                    timeout=12,
                )
                if not resp.ok:
                    all_ok = False
                    logger.warning("Telegram send failed: %s", resp.text)
            except Exception as exc:
                all_ok = False
                logger.warning("Telegram error: %s", exc)
        return all_ok

    def send_email(
        self,
        subject: str,
        body_text: str,
        attachment_path: Optional[Path] = None,
    ) -> bool:
        if not (self.config.smtp_user and self.config.smtp_pass and self.config.notify_email_to):
            return False
        if not self._is_channel_enabled("notify_email_enabled", True):
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.config.smtp_user
        msg["To"] = self.config.notify_email_to
        msg.set_content(body_text)

        if attachment_path and Path(attachment_path).exists():
            data = Path(attachment_path).read_bytes()
            msg.add_attachment(
                data,
                maintype="application",
                subtype="pdf",
                filename=Path(attachment_path).name,
            )

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=15) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_pass)
                server.send_message(msg)
            return True
        except Exception as exc:
            logger.warning("Email send failed: %s", exc)
            return False

    def notify_daily(self, digest: Dict[str, Any]) -> Dict[str, bool]:
        """Send daily notification ONLY if meaningful new discoveries exist."""
        if not digest.get("has_discoveries"):
            logger.info("No meaningful daily discoveries — notification suppressed.")
            return {"telegram": False, "email": False, "suppressed": True}

        tools: List[Dict[str, Any]] = digest.get("tools", [])
        lines = [f"Pramana Daily AI Radar ({digest.get('date')}) — Top {len(tools)} New Free Tools:\n"]
        for i, t in enumerate(tools, 1):
            p = t.get("personalization", {})
            lines.append(
                f"{i}. {t['name']} ({t['score']}/100)\n"
                f"   Category: {t['category']} > {t['subcategory']}\n"
                f"   Free Tier: {t['free_tier_type']} (CC: {t['credit_card_required']})\n"
                f"   RTX 4050 Fit: {p.get('can_run_on_laptop', 'UNKNOWN')}\n"
                f"   Why useful: {t['what_makes_it_useful']}\n"
                f"   Link: {t['official_website']}\n"
            )
        message = "\n".join(lines)
        return {
            "telegram": self.send_telegram(message),
            "email": self.send_email(
                f"[Pramana Radar] {len(tools)} Verified Free AI Tools — {digest.get('date')}",
                message,
            ),
            "suppressed": False,
        }

    def notify_weekly(self, weekly_report: Dict[str, Any]) -> Dict[str, bool]:
        top_10 = weekly_report.get("top_10", [])
        lines = [
            f"Pramana Weekly AI Intelligence ({weekly_report.get('week_label')})\n",
            "Top 10 Ranked Free AI Tools:",
        ]
        for idx, t in enumerate(top_10, 1):
            lines.append(f"#{idx}. {t['name']} — {t['score']}/100 ({t['free_tier_type']}) | {t['official_website']}")
        summary_msg = "\n".join(lines)
        pdf_path = Path(weekly_report["pdf_path"]) if weekly_report.get("pdf_path") else None

        return {
            "telegram": self.send_telegram(summary_msg),
            "email": self.send_email(
                f"[Pramana Weekly Intelligence] {weekly_report.get('week_label')} — Top 10 Report",
                weekly_report.get("markdown", summary_msg),
                attachment_path=pdf_path,
            ),
        }

    def notify_failure(self, context: str, error_msg: str) -> None:
        msg = f"[Pramana Radar ALERT] Automation failure during {context}:\n{error_msg}"
        self.send_telegram(msg)
        self.send_email(f"[Pramana ALERT] {context} failed", msg)
