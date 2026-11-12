"""Tests for Fake-Free pricing forensics and 100-point QualityEvaluationAgent."""

from pramana.agents.opensource import OpenSourceReport
from pramana.agents.pricing import PricingVerificationAgent
from pramana.agents.quality import QualityEvaluationAgent
from pramana.agents.research import ResearchDossier
from pramana.models import RawCandidate, UNKNOWN
from pramana.sources.base import SafeHttpClient


class FakeClient(SafeHttpClient):
    def __init__(self, text_by_url):
        super().__init__(timeout=2, min_delay_per_domain=0.0)
        self.text_by_url = text_by_url

    def fetch(self, url, headers=None):
        from pramana.sources.base import HttpFetchResult
        html = self.text_by_url.get(url, "")
        return HttpFetchResult(
            url=url,
            final_url=url,
            status_code=200 if html else 404,
            text=html,
            headers={},
            ok=bool(html),
        )


def test_trial_only_with_credit_card_is_rejected():
    client = FakeClient({
        "https://fakefree.ai/pricing": "<html><body><h1>Pricing</h1><p>Start your 14-day free trial today. Credit card required to start trial. No free plan.</p></body></html>"
    })
    agent = PricingVerificationAgent(client)
    cand = RawCandidate(name="FakeFreeAI", url="https://fakefree.ai", source_name="Test", source_url="https://fakefree.ai")
    dossier = ResearchDossier(
        final_url="https://fakefree.ai",
        http_ok=True,
        http_status=200,
        visible_text="AI workspace",
        pricing_links=["https://fakefree.ai/pricing"],
    )
    ver = agent.verify(cand, dossier, verified_license="Proprietary")
    assert ver.is_genuinely_free is False
    assert ver.is_trial_only is True
    assert ver.free_tier_type == "Trial Only"
    assert len(ver.fake_free_flags) >= 1


def test_open_source_tool_passes_and_scores_high():
    client = FakeClient({})
    pricing_agent = PricingVerificationAgent(client)
    quality_agent = QualityEvaluationAgent()

    cand = RawCandidate(
        name="LocalAgent",
        url="https://github.com/example/localagent",
        source_name="GitHub API",
        source_url="https://github.com/example/localagent",
        github_repo="https://github.com/example/localagent",
        topics=["ai-agent", "python", "local-llm"],
        language="Python",
        stars=5400,
    )
    dossier = ResearchDossier(
        final_url="https://github.com/example/localagent",
        http_ok=True,
        http_status=200,
        description="Open-source multi-agent Python framework running locally",
        visible_text="MIT License pip install localagent local",
        category="AI and Machine Learning",
        subcategory="Multi-agent orchestration",
        supported_os=["Windows", "Linux", "macOS"],
        api_availability="Python Library / Local SDK",
        local_installation_available="Yes",
        official_documentation="https://github.com/example/localagent/blob/main/README.md",
    )
    os_rep = OpenSourceReport(
        is_open_source=True,
        open_source_status="Open Source (MIT)",
        github_repository="https://github.com/example/localagent",
        stars=5400,
        license_name="MIT",
        primary_language="Python",
    )
    ver = pricing_agent.verify(cand, dossier, verified_license="MIT")
    assert ver.is_genuinely_free is True
    assert ver.credit_card_required == "No"

    score = quality_agent.score(cand, dossier, ver, os_rep)
    assert 75.0 <= score.total_score <= 100.0
    assert score.penalties == 0.0


def test_unverifiable_page_marks_unknown():
    client = FakeClient({})
    agent = PricingVerificationAgent(client)
    cand = RawCandidate(name="MysteryTool", url="https://mystery.example.org", source_name="Test", source_url="https://mystery.example.org")
    dossier = ResearchDossier(
        final_url="https://mystery.example.org",
        http_ok=False,
        http_status=404,
        visible_text="",
    )
    ver = agent.verify(cand, dossier, verified_license="Proprietary")
    assert ver.is_genuinely_free is False
    assert ver.free_tier_type == UNKNOWN
