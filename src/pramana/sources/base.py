"""Rate-limited, fault-tolerant HTTP client and safe HTML/XML extraction."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from lxml import html as lxml_html
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

USER_AGENT = (
    "PramanaAIRadar/1.0 (+https://github.com/adityanimbalkar9699-max/pramana-ai-radar; "
    "student-research-bot; respectful-crawling)"
)


@dataclass
class HttpFetchResult:
    url: str
    final_url: str
    status_code: int
    text: str
    headers: Dict[str, str]
    ok: bool
    error: str = ""


class DomainCircuitBreaker:
    """Prevents repeated hammering of failing or rate-limited domains."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 120.0) -> None:
        self._lock = threading.Lock()
        self._failures: Dict[str, int] = {}
        self._open_until: Dict[str, float] = {}
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

    def is_open(self, domain: str) -> bool:
        with self._lock:
            until = self._open_until.get(domain, 0.0)
            if until > time.monotonic():
                return True
            if until > 0.0:
                self._open_until.pop(domain, None)
                self._failures[domain] = 0
            return False

    def record_success(self, domain: str) -> None:
        with self._lock:
            self._failures[domain] = 0
            self._open_until.pop(domain, None)

    def record_failure(self, domain: str) -> None:
        with self._lock:
            count = self._failures.get(domain, 0) + 1
            self._failures[domain] = count
            if count >= self.failure_threshold:
                self._open_until[domain] = time.monotonic() + self.cooldown_seconds


class SafeHttpClient:
    """Thread-safe HTTP client with per-domain rate limiting, retries, and circuit breaker."""

    def __init__(self, timeout: int = 12, min_delay_per_domain: float = 0.6) -> None:
        self.timeout = timeout
        self.min_delay = min_delay_per_domain
        self._domain_last_call: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._breaker = DomainCircuitBreaker()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def _respect_rate_limit(self, domain: str) -> None:
        with self._lock:
            last = self._domain_last_call.get(domain, 0.0)
            elapsed = time.monotonic() - last
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
            self._domain_last_call[domain] = time.monotonic()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.8, min=0.5, max=3.0),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
        reraise=True,
    )
    def _do_get(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        return self._session.get(
            url,
            headers=headers,
            timeout=self.timeout,
            allow_redirects=True,
        )

    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> HttpFetchResult:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain or parsed.scheme not in ("http", "https"):
            return HttpFetchResult(url=url, final_url=url, status_code=0, text="", headers={}, ok=False, error="Invalid URL scheme")

        if self._breaker.is_open(domain):
            return HttpFetchResult(url=url, final_url=url, status_code=429, text="", headers={}, ok=False, error="Circuit breaker open")

        self._respect_rate_limit(domain)
        try:
            resp = self._do_get(url, headers=headers)
            if resp.status_code >= 500 or resp.status_code == 429:
                self._breaker.record_failure(domain)
            else:
                self._breaker.record_success(domain)
            text = resp.text if len(resp.content) <= 1_500_000 else resp.text[:400_000]
            return HttpFetchResult(
                url=url,
                final_url=str(resp.url),
                status_code=resp.status_code,
                text=text,
                headers={k.lower(): v for k, v in resp.headers.items()},
                ok=200 <= resp.status_code < 400,
                error="" if 200 <= resp.status_code < 400 else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            self._breaker.record_failure(domain)
            logger.debug("Fetch failed for %s: %s", url, exc)
            return HttpFetchResult(url=url, final_url=url, status_code=0, text="", headers={}, ok=False, error=str(exc))

    def fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
        res = self.fetch(url, headers=headers)
        if not res.ok:
            return None
        try:
            import json
            return json.loads(res.text)
        except Exception:
            return None


def extract_html_metadata(html_text: str, base_url: str) -> Dict[str, Any]:
    """Safely extract title, description, visible text, and pricing/docs links from HTML."""
    if not html_text or "<" not in html_text:
        return {"title": "", "description": "", "visible_text": "", "pricing_links": [], "docs_links": [], "github_links": []}
    try:
        doc = lxml_html.fromstring(html_text)
    except Exception:
        return {"title": "", "description": "", "visible_text": "", "pricing_links": [], "docs_links": [], "github_links": []}

    title_list = doc.xpath("//title/text()")
    title = title_list[0].strip() if title_list else ""

    desc_list = doc.xpath("//meta[@name='description']/@content | //meta[@property='og:description']/@content")
    description = desc_list[0].strip() if desc_list else ""

    # Remove script/style/noscript noise before extracting visible text
    for bad in doc.xpath("//script | //style | //noscript | //svg"):
        parent = bad.getparent()
        if parent is not None:
            parent.remove(bad)

    visible_text = " ".join(doc.text_content().split())[:20_000]

    pricing_links: List[str] = []
    docs_links: List[str] = []
    github_links: List[str] = []

    for a in doc.xpath("//a[@href]"):
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        full = urljoin(base_url, href)
        low_href = full.lower()
        low_text = " ".join(a.text_content().split()).lower()
        if any(k in low_href or k in low_text for k in ("pricing", "plans", "free-tier", "billing")):
            if full not in pricing_links:
                pricing_links.append(full)
        if any(k in low_href or k in low_text for k in ("/docs", "docs.", "documentation", "guide", "quickstart")):
            if full not in docs_links:
                docs_links.append(full)
        if "github.com/" in low_href and len(urlparse(full).path.strip("/").split("/")) >= 2:
            if full not in github_links:
                github_links.append(full)

    return {
        "title": title,
        "description": description,
        "visible_text": visible_text,
        "pricing_links": pricing_links[:5],
        "docs_links": docs_links[:5],
        "github_links": github_links[:5],
    }
