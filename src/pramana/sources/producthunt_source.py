"""Product Hunt official RSS discovery source for newly launched AI web apps."""

from __future__ import annotations

import re
from typing import List
from lxml import etree

from ..models import RawCandidate
from .base import SafeHttpClient


AI_LAUNCH_KEYWORDS = (
    "ai", "llm", "gpt", "agent", "video", "slide", "ppt", "presentation",
    "image", "voice", "code", "coding", "chat", "pdf", "design", "audio",
    "generator", "studio", "copilot", "automation", "workflow",
)

HTML_TAG_RE = re.compile(r"<[^>]+>")


class ProductHuntDiscoverySource:
    name = "Product Hunt"

    def __init__(self, client: SafeHttpClient) -> None:
        self.client = client

    def discover(self, limit: int = 12) -> List[RawCandidate]:
        feed_urls = [
            "https://www.producthunt.com/feed?category=artificial-intelligence",
            "https://www.producthunt.com/feed",
        ]
        candidates: List[RawCandidate] = []
        seen: set[str] = set()

        for feed_url in feed_urls:
            res = self.client.fetch(feed_url)
            if not res.ok or not res.text:
                continue
            try:
                root = etree.fromstring(res.text.encode("utf-8", errors="ignore"))
            except Exception:
                continue

            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.xpath("//atom:entry", namespaces=ns)
            if not entries:
                # Try RSS 2.0 <item>
                entries = root.xpath("//item")

            for entry in entries:
                title_el = entry.find("atom:title", ns) if entry.tag.endswith("entry") else entry.find("title")
                link_el = entry.find("atom:link", ns) if entry.tag.endswith("entry") else entry.find("link")
                content_el = entry.find("atom:content", ns) if entry.tag.endswith("entry") else entry.find("description")

                title = (title_el.text or "").strip() if title_el is not None else ""
                if link_el is not None:
                    url = (link_el.get("href") or link_el.text or "").strip()
                else:
                    url = ""
                raw_desc = (content_el.text or "") if content_el is not None else ""
                clean_desc = " ".join(HTML_TAG_RE.sub(" ", raw_desc).split())[:260]

                if not title or not url or url in seen:
                    continue
                blob = f"{title} {clean_desc}".lower()
                if not any(kw in blob for kw in AI_LAUNCH_KEYWORDS):
                    continue
                seen.add(url)

                name = title.split(" - ")[0].split("—")[0].split(":")[0].strip()[:48]
                candidates.append(
                    RawCandidate(
                        name=name or title[:40],
                        url=url,
                        source_name="Product Hunt Feed",
                        source_url=url,
                        summary=clean_desc or title,
                        topics=["web-app", "new-launch", "product-hunt"],
                        extra={"web_launch": True},
                    )
                )
            if candidates:
                break

        return candidates[:limit]
