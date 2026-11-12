"""Agent 7: DeduplicationAgent — prevents duplicate tools via URL, repo, and fuzzy name matching."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid",
}


def canonicalize_url(raw_url: str) -> str:
    """Normalize a URL for reliable deduplication."""
    raw = (raw_url or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or ""
    clean_qs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(clean_qs)
    return urlunparse(("https", host, path, "", query, ""))


def extract_github_slug(url: str) -> str:
    """Return lowercase 'owner/repo' if URL points to a GitHub repository."""
    if not url or "github.com/" not in url.lower():
        return ""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2:
        owner, repo = parts[0].lower(), parts[1].lower()
        if repo.endswith(".git"):
            repo = repo[:-4]
        return f"{owner}/{repo}"
    return ""


def make_canonical_key(name: str, url: str, github_repo: str = "") -> str:
    """Generate a deterministic canonical key for persistent identity."""
    gh_slug = extract_github_slug(github_repo) or extract_github_slug(url)
    if gh_slug:
        return f"gh:{gh_slug}"
    canon = canonicalize_url(url)
    if canon:
        parsed = urlparse(canon)
        path_part = parsed.path.strip("/").lower()
        key = f"{parsed.netloc}/{path_part}" if path_part else parsed.netloc
        return f"web:{key}"
    slug = "".join(ch for ch in name.lower() if ch.isalnum())
    return f"name:{slug}"


def normalize_name(name: str) -> str:
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


class DeduplicationAgent:
    """Filters out duplicates against database history and current batch."""

    def __init__(self, existing_records: List[Dict[str, str]]) -> None:
        self.existing_keys: set[str] = set()
        self.existing_urls: set[str] = set()
        self.existing_gh: set[str] = set()
        self.existing_names: List[str] = []

        for rec in existing_records:
            if rec.get("canonical_key"):
                self.existing_keys.add(rec["canonical_key"])
            if rec.get("official_website"):
                self.existing_urls.add(canonicalize_url(rec["official_website"]))
            if rec.get("github_repository"):
                slug = extract_github_slug(rec["github_repository"])
                if slug:
                    self.existing_gh.add(slug)
            if rec.get("name"):
                self.existing_names.append(normalize_name(rec["name"]))

    def is_duplicate(self, name: str, url: str, github_repo: str = "") -> Tuple[bool, str]:
        key = make_canonical_key(name, url, github_repo)
        if key in self.existing_keys:
            return True, f"Exact canonical_key match ({key})"

        canon_url = canonicalize_url(url)
        if canon_url and canon_url in self.existing_urls:
            return True, f"Duplicate canonical URL ({canon_url})"

        gh_slug = extract_github_slug(github_repo) or extract_github_slug(url)
        if gh_slug and gh_slug in self.existing_gh:
            return True, f"Duplicate GitHub repository ({gh_slug})"

        norm = normalize_name(name)
        if len(norm) >= 4:
            for existing_norm in self.existing_names:
                if existing_norm == norm:
                    return True, f"Exact normalized name match ({name})"
                if len(existing_norm) >= 5 and SequenceMatcher(None, norm, existing_norm).ratio() >= 0.92:
                    # Also require same domain if names are merely similar
                    return True, f"High name similarity ({name})"

        # Register into seen set for intra-batch deduplication
        self.existing_keys.add(key)
        if canon_url:
            self.existing_urls.add(canon_url)
        if gh_slug:
            self.existing_gh.add(gh_slug)
        if norm:
            self.existing_names.append(norm)
        return False, ""
