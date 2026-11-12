"""Hacker News Algolia API discovery source (Show HN AI tools & open-source launches)."""

from __future__ import annotations

from typing import List
from urllib.parse import quote_plus

from ..models import RawCandidate
from .base import SafeHttpClient


class HackerNewsDiscoverySource:
    name = "Hacker News"

    def __init__(self, client: SafeHttpClient) -> None:
        self.client = client

    def discover(self, limit: int = 12) -> List[RawCandidate]:
        queries = [
            "Show HN AI free open source",
            "Show HN LLM agent coding",
        ]
        candidates: List[RawCandidate] = []
        seen_urls: set[str] = set()

        for q in queries:
            api_url = (
                f"https://hn.algolia.com/api/v1/search_by_date"
                f"?query={quote_plus(q)}&tags=show_hn&hitsPerPage=10"
            )
            data = self.client.fetch_json(api_url)
            if not isinstance(data, dict):
                continue
            for hit in data.get("hits", []):
                url = (hit.get("url") or "").strip()
                title = (hit.get("title") or "").strip()
                if not url or not title or url in seen_urls:
                    continue
                seen_urls.add(url)
                clean_name = (
                    title.replace("Show HN:", "")
                    .replace("Show HN -", "")
                    .split("–")[0]
                    .split("-")[0]
                    .split(":")[0]
                    .strip()
                )
                if len(clean_name) > 55:
                    clean_name = clean_name[:52].strip()
                hn_thread = f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                gh_repo = url if "github.com/" in url.lower() else ""
                candidates.append(
                    RawCandidate(
                        name=clean_name or title[:40],
                        url=url,
                        source_name="Hacker News (Show HN)",
                        source_url=hn_thread,
                        summary=title,
                        github_repo=gh_repo,
                        stars=int(hit.get("points") or 0),
                        topics=["show-hn", "ai"],
                        extra={"hn_comments": hit.get("num_comments", 0)},
                    )
                )
        return candidates[:limit]
