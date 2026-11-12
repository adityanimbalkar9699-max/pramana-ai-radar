"""Tests for URL canonicalization, canonical keys, and DeduplicationAgent."""

from pramana.agents.deduplication import (
    DeduplicationAgent,
    canonicalize_url,
    extract_github_slug,
    make_canonical_key,
)


def test_canonicalize_url_strips_tracking_and_www():
    u1 = canonicalize_url("https://www.Example.com/tool/?utm_source=hn&ref=daily&tab=docs/")
    u2 = canonicalize_url("http://example.com/tool?tab=docs/")
    assert u1 == "https://example.com/tool?tab=docs%2F"
    assert canonicalize_url("https://www.qdrant.tech/?utm_medium=social") == "https://qdrant.tech"


def test_extract_github_slug():
    assert extract_github_slug("https://github.com/Ollama/Ollama.git") == "ollama/ollama"
    assert extract_github_slug("https://ollama.com") == ""


def test_deduplication_catches_url_repo_and_fuzzy_name():
    existing = [
        {
            "canonical_key": "gh:ollama/ollama",
            "name": "Ollama",
            "official_website": "https://ollama.com",
            "github_repository": "https://github.com/ollama/ollama",
        }
    ]
    agent = DeduplicationAgent(existing)

    # Same GitHub repo under different homepage URL
    dup1, _ = agent.is_duplicate("Ollama CLI", "https://ollama.ai", "https://github.com/ollama/ollama")
    assert dup1 is True

    # Same URL with tracking query
    dup2, _ = agent.is_duplicate("Different Name", "https://www.ollama.com/?utm_source=reddit", "")
    assert dup2 is True

    # Genuinely new tool
    dup3, _ = agent.is_duplicate("Qdrant", "https://qdrant.tech", "https://github.com/qdrant/qdrant")
    assert dup3 is False

    # Intra-batch duplicate rejected on second appearance
    dup4, _ = agent.is_duplicate("Qdrant", "https://qdrant.tech/", "")
    assert dup4 is True
