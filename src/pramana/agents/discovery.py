"""Agent 1: DiscoveryAgent — concurrent multi-source discovery + emerging category detection."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Tuple

from ..models import RawCandidate
from ..sources import (
    GitHubDiscoverySource,
    HackerNewsDiscoverySource,
    HuggingFaceDiscoverySource,
    ProductHuntDiscoverySource,
    RedditDiscoverySource,
    SafeHttpClient,
    get_verified_seed_candidates,
    get_verified_web_free_apps,
)

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryBatch:
    candidates: List[RawCandidate] = field(default_factory=list)
    sources_succeeded: List[str] = field(default_factory=list)
    sources_failed: List[str] = field(default_factory=list)
    emerging_categories_detected: List[str] = field(default_factory=list)


EMERGING_CATEGORY_SIGNALS: List[Tuple[str, Tuple[str, ...]]] = [
    ("MCP Servers & Toolchains", ("mcp", "model-context-protocol", "model context protocol")),
    ("Browser & Computer-Use Agents", ("browser-use", "computer-use", "web-agent", "playwright-agent")),
    ("Local AI & Edge Inference", ("gguf", "mlx", "ollama", "llama.cpp", "vllm", "edge-ai", "quantized")),
    ("Robotics & Embodied AI", ("robotics", "ros2", "embodied", "vla", "lerobot")),
    ("Synthetic Data & Benchmarks", ("synthetic-data", "benchmark", "eval-harness", "red-team")),
]


def detect_emerging_categories(candidates: List[RawCandidate]) -> List[str]:
    """Automatically surface emerging AI categories from live candidate streams."""
    found: List[str] = []
    for c in candidates:
        blob = " ".join([c.name, c.summary, " ".join(c.topics)]).lower()
        for label, keywords in EMERGING_CATEGORY_SIGNALS:
            if any(kw in blob for kw in keywords):
                if label not in found:
                    found.append(label)
                if not c.category_hint:
                    c.category_hint = "Emerging AI"
                    c.subcategory_hint = label
    return found


class DiscoveryAgent:
    """Fetches raw tool candidates concurrently across independent public sources."""

    def __init__(self, client: SafeHttpClient, github_token: str = "") -> None:
        self.client = client
        self.github_token = github_token

    def run(self, include_seed_when_empty_db: bool = False, per_source_limit: int = 12) -> DiscoveryBatch:
        batch = DiscoveryBatch()
        sources = [
            GitHubDiscoverySource(self.client, github_token=self.github_token),
            HuggingFaceDiscoverySource(self.client),
            HackerNewsDiscoverySource(self.client),
            RedditDiscoverySource(self.client),
            ProductHuntDiscoverySource(self.client),
        ]

        with ThreadPoolExecutor(max_workers=5) as pool:
            future_map = {
                pool.submit(src.discover, per_source_limit): src.name for src in sources
            }
            for fut in as_completed(future_map):
                src_name = future_map[fut]
                try:
                    items = fut.result(timeout=25)
                    if items:
                        batch.candidates.extend(items)
                        batch.sources_succeeded.append(src_name)
                    else:
                        batch.sources_failed.append(f"{src_name} (0 items)")
                except Exception as exc:
                    logger.warning("Discovery source %s failed: %s", src_name, exc)
                    batch.sources_failed.append(f"{src_name} ({exc})")

        if include_seed_when_empty_db:
            batch.candidates.extend(get_verified_seed_candidates())
            batch.sources_succeeded.append("Pramana Verified Directory")

        # Always pass un-ingested Web-Only Free Apps through Deduplication + Live Pricing Verification
        batch.candidates.extend(get_verified_web_free_apps())

        batch.emerging_categories_detected = detect_emerging_categories(batch.candidates)
        return batch
