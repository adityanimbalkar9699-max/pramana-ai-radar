"""Independent live discovery sources for Pramana AI Radar."""

from .base import SafeHttpClient, extract_html_metadata
from .github_source import GitHubDiscoverySource
from .huggingface_source import HuggingFaceDiscoverySource
from .hackernews_source import HackerNewsDiscoverySource
from .reddit_source import RedditDiscoverySource
from .producthunt_source import ProductHuntDiscoverySource
from .curated_seed import get_verified_seed_candidates, get_verified_web_free_apps

__all__ = [
    "SafeHttpClient",
    "extract_html_metadata",
    "GitHubDiscoverySource",
    "HuggingFaceDiscoverySource",
    "HackerNewsDiscoverySource",
    "RedditDiscoverySource",
    "ProductHuntDiscoverySource",
    "get_verified_seed_candidates",
    "get_verified_web_free_apps",
]
