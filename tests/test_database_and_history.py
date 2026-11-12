"""Tests for SQLite persistent DB, pricing history tracking, and snapshot exports."""

from pramana.database import PramanaDatabase
from pramana.models import PersonalizationProfile, ScoreBreakdown, ToolRecord


def _sample_tool(name="Qdrant", plan="1 GB free cloud cluster", limits="1 GB RAM"):
    return ToolRecord(
        name=name,
        official_website="https://qdrant.tech",
        category="AI and Machine Learning",
        subcategory="RAG and vector databases",
        short_description="High-performance vector database.",
        main_capabilities=["Vector Search", "Hybrid RAG"],
        what_makes_it_useful="Permanent free cluster + Docker local mode",
        free_plan_details=plan,
        free_usage_limits=limits,
        credit_card_required="No",
        registration_required="Yes",
        open_source_status="Open Source (Apache-2.0)",
        github_repository="https://github.com/qdrant/qdrant",
        supported_os=["Windows", "Linux", "macOS"],
        api_availability="Free API",
        local_installation_available="Yes",
        important_limitations=["1 GB free cloud RAM limit"],
        privacy_considerations="Runs locally via Docker",
        official_documentation="https://qdrant.tech/documentation/",
        best_student_use_case="Build RAG backend for college project",
        canonical_key="gh:qdrant/qdrant",
        free_tier_type="Free Open Source",
        is_genuinely_free=True,
        india_available="Yes",
        score=91.5,
        score_breakdown=ScoreBreakdown(free_functionality=24, practical_usefulness=19, total_score=91.5),
        personalization=PersonalizationProfile(can_run_on_laptop="Yes (Native Windows 11)"),
        sources=["https://qdrant.tech"],
        tags=["rag", "vector"],
    )


def test_upsert_tracks_pricing_history_and_preserves_saved(tmp_path):
    db = PramanaDatabase(tmp_path / "test.db")
    t1 = _sample_tool()
    assert db.upsert_tool(t1) == "inserted"
    assert db.set_saved("gh:qdrant/qdrant", True) is True

    # Simulate pricing change update
    t2 = _sample_tool(plan="2 GB free cloud cluster", limits="2 GB RAM")
    assert db.upsert_tool(t2) == "pricing_changed"

    loaded = db.get_tool("gh:qdrant/qdrant")
    assert loaded is not None
    assert loaded["is_saved"] is True  # User bookmark preserved!
    assert "1 GB free cloud cluster" in loaded["previous_pricing_info"]

    history = db.get_pricing_history()
    assert len(history) == 2
    assert history[0]["change_type"] == "updated"
