"""GitHub Search & Trending AI tools discovery source."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List
from urllib.parse import quote_plus

from ..models import RawCandidate
from .base import SafeHttpClient


ROTATING_GITHUB_TOPICS = [
    ("ai-agent OR multi-agent OR agent-framework", "AI and Machine Learning", "AI agents and agent frameworks"),
    ("local-llm OR ollama OR inference-engine", "AI and Machine Learning", "AI inference platforms"),
    ("coding-assistant OR ai-code-editor OR mcp-server", "Coding and Development", "AI coding assistants"),
    ("rag OR vector-database OR knowledge-graph", "AI and Machine Learning", "RAG and vector databases"),
    ("text-to-speech OR voice-cloning OR whisper", "Audio and Voice", "Text-to-speech"),
    ("image-generation OR video-editing OR 3d-generation", "Image and Design", "AI image generation"),
    ("workflow-automation OR browser-automation OR research-assistant", "Productivity and Research", "Browser automation"),
]


class GitHubDiscoverySource:
    name = "GitHub"

    def __init__(self, client: SafeHttpClient, github_token: str = "") -> None:
        self.client = client
        self.github_token = github_token

    def discover(self, limit: int = 15) -> List[RawCandidate]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        day_idx = datetime.now(timezone.utc).timetuple().tm_yday
        # Query 2 rotating topics + 1 recent high-velocity AI repo query
        queries = [
            ROTATING_GITHUB_TOPICS[day_idx % len(ROTATING_GITHUB_TOPICS)],
            ROTATING_GITHUB_TOPICS[(day_idx + 3) % len(ROTATING_GITHUB_TOPICS)],
        ]

        since_date = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        candidates: List[RawCandidate] = []
        seen_repos: set[str] = set()

        for query_expr, cat_hint, subcat_hint in queries:
            q = f"({query_expr}) stars:>150 pushed:>{since_date} archived:false"
            url = (
                f"https://api.github.com/search/repositories"
                f"?q={quote_plus(q)}&sort=stars&order=desc&per_page={min(10, limit)}"
            )
            data = self.client.fetch_json(url, headers=headers)
            if not isinstance(data, dict) or "items" not in data:
                continue
            for item in data.get("items", []):
                full_name = item.get("full_name", "")
                if not full_name or full_name in seen_repos:
                    continue
                seen_repos.add(full_name)
                homepage = (item.get("homepage") or "").strip()
                html_url = item.get("html_url", "")
                target_url = homepage if homepage.startswith(("http://", "https://")) else html_url
                lic = item.get("license") or {}
                lic_name = lic.get("spdx_id") or lic.get("name") or ""
                if lic_name == "NOASSERTION":
                    lic_name = "Custom / Check Repo"
                candidates.append(
                    RawCandidate(
                        name=item.get("name", full_name.split("/")[-1]),
                        url=target_url,
                        source_name="GitHub API",
                        source_url=html_url,
                        summary=item.get("description") or "",
                        github_repo=html_url,
                        stars=int(item.get("stargazers_count", 0)),
                        topics=list(item.get("topics") or []),
                        language=item.get("language") or "",
                        license_name=lic_name,
                        category_hint=cat_hint,
                        subcategory_hint=subcat_hint,
                        extra={
                            "open_issues": item.get("open_issues_count", 0),
                            "pushed_at": item.get("pushed_at", ""),
                            "forks": item.get("forks_count", 0),
                        },
                    )
                )
        return candidates[:limit]
