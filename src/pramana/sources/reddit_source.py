"""Reddit AI & Open Source community RSS/JSON discovery source."""

from __future__ import annotations

import re
from typing import List
from lxml import etree

from ..models import RawCandidate
from .base import SafeHttpClient


SUBREDDITS = [
    ("LocalLLaMA", "AI and Machine Learning", "Local AI & Edge Inference"),
    ("opensource", "Coding and Development", "GitHub automation"),
]

URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")


class RedditDiscoverySource:
    name = "Reddit"

    def __init__(self, client: SafeHttpClient) -> None:
        self.client = client

    def discover(self, limit: int = 10) -> List[RawCandidate]:
        candidates: List[RawCandidate] = []
        seen_urls: set[str] = set()

        for sub, cat_hint, subcat_hint in SUBREDDITS:
            rss_url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=15"
            res = self.client.fetch(rss_url)
            if not res.ok or not res.text:
                continue
            try:
                root = etree.fromstring(res.text.encode("utf-8", errors="ignore"))
            except Exception:
                continue

            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.xpath("//atom:entry", namespaces=ns)
            for entry in entries:
                title_el = entry.find("atom:title", ns)
                content_el = entry.find("atom:content", ns)
                link_el = entry.find("atom:link", ns)
                title = (title_el.text or "").strip() if title_el is not None else ""
                content = (content_el.text or "") if content_el is not None else ""
                post_link = link_el.get("href", "") if link_el is not None else ""

                # Look for external tool URLs (GitHub, HuggingFace, project sites) inside post content
                found_urls = [
                    u for u in URL_RE.findall(content)
                    if "reddit.com" not in u and "redd.it" not in u and not u.endswith((".png", ".jpg", ".gif"))
                ]
                if not found_urls:
                    continue
                target_url = found_urls[0].rstrip(".,;:")
                if target_url in seen_urls:
                    continue
                seen_urls.add(target_url)

                # Prioritize links that look like actual tools/repos
                if not any(
                    k in title.lower() or k in target_url.lower()
                    for k in ("github.com", "huggingface.co", "release", "open source", "free", "tool", "agent", "local", "v0", "v1", "v2")
                ):
                    continue

                name = title.split(":")[0].split("-")[0].strip()[:48]
                candidates.append(
                    RawCandidate(
                        name=name or f"{sub}-tool",
                        url=target_url,
                        source_name=f"Reddit r/{sub}",
                        source_url=post_link or rss_url,
                        summary=title,
                        github_repo=target_url if "github.com/" in target_url.lower() else "",
                        topics=[sub.lower(), "community"],
                        category_hint=cat_hint,
                        subcategory_hint=subcat_hint,
                    )
                )
        return candidates[:limit]
