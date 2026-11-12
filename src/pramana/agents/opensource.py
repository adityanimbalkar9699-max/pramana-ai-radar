"""Agent 4: OpenSourceAgent — inspects GitHub repositories, licenses, stars, and maintenance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..models import RawCandidate, UNKNOWN
from ..sources.base import SafeHttpClient
from .deduplication import extract_github_slug


OSI_LICENSES = {
    "MIT", "Apache-2.0", "GPL-3.0", "GPL-2.0", "AGPL-3.0",
    "BSD-3-Clause", "BSD-2-Clause", "MPL-2.0", "ISC", "Unlicense", "CC0-1.0",
}


@dataclass
class OpenSourceReport:
    is_open_source: bool = False
    open_source_status: str = "Closed Source"
    github_repository: str = ""
    stars: int = 0
    forks: int = 0
    license_name: str = UNKNOWN
    archived: bool = False
    last_pushed_at: str = ""
    primary_language: str = ""
    homepage: str = ""


class OpenSourceAgent:
    """Verifies GitHub repository health, license, and open-source status."""

    def __init__(self, client: SafeHttpClient, github_token: str = "") -> None:
        self.client = client
        self.github_token = github_token

    def inspect(self, candidate: RawCandidate, discovered_github: str = "") -> OpenSourceReport:
        gh_url = candidate.github_repo or discovered_github
        slug = extract_github_slug(gh_url) or extract_github_slug(candidate.url)
        if not slug:
            # Check if Hugging Face open-weights
            if "huggingface.co/" in candidate.url.lower() and "/spaces/" not in candidate.url.lower():
                return OpenSourceReport(
                    is_open_source=True,
                    open_source_status="Open Weights",
                    stars=candidate.stars,
                    license_name=candidate.license_name or "Open Weights",
                )
            return OpenSourceReport(
                is_open_source=False,
                open_source_status="Closed Source / Free Service",
                stars=candidate.stars,
                license_name="Proprietary",
            )

        headers: Dict[str, str] = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        data = self.client.fetch_json(f"https://api.github.com/repos/{slug}", headers=headers)
        if isinstance(data, dict) and "stargazers_count" in data:
            lic = data.get("license") or {}
            spdx = lic.get("spdx_id") or lic.get("name") or candidate.license_name or UNKNOWN
            if spdx == "NOASSERTION":
                spdx = "Source Available / Custom License"
            is_osi = spdx in OSI_LICENSES or "GPL" in spdx or "MIT" in spdx or "Apache" in spdx
            status = f"Open Source ({spdx})" if is_osi else f"Source Available ({spdx})"
            return OpenSourceReport(
                is_open_source=True,
                open_source_status=status,
                github_repository=data.get("html_url", f"https://github.com/{slug}"),
                stars=int(data.get("stargazers_count", candidate.stars)),
                forks=int(data.get("forks_count", 0)),
                license_name=spdx,
                archived=bool(data.get("archived", False)),
                last_pushed_at=str(data.get("pushed_at", "")),
                primary_language=str(data.get("language") or candidate.language or ""),
                homepage=str(data.get("homepage") or ""),
            )

        # Graceful fallback if GitHub API unauthenticated quota is temporarily hit
        lic_fallback = candidate.license_name or UNKNOWN
        return OpenSourceReport(
            is_open_source=True,
            open_source_status=f"Open Source ({lic_fallback})" if lic_fallback != UNKNOWN else "Open Source",
            github_repository=f"https://github.com/{slug}",
            stars=candidate.stars,
            license_name=lic_fallback,
            primary_language=candidate.language,
        )
