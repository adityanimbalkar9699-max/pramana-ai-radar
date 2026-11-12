"""Tests for PersonalizationAgent and RTX 4050 (6GB VRAM) hardware fit classification."""

from pramana.agents.opensource import OpenSourceReport
from pramana.agents.personalization import PersonalizationAgent
from pramana.agents.research import ResearchDossier
from pramana.models import PricingVerification, RawCandidate


def _make_pricing():
    return PricingVerification(
        free_tier_type="Free Open Source",
        is_genuinely_free=True,
        credit_card_required="No",
        india_available="Yes",
    )


def test_8b_model_fits_rtx_4050_quantized():
    agent = PersonalizationAgent()
    cand = RawCandidate(
        name="Qwen-8B-Instruct",
        url="https://huggingface.co/Qwen/Qwen-8B-Instruct",
        source_name="HF",
        source_url="https://huggingface.co/Qwen/Qwen-8B-Instruct",
        summary="8B open-weights LLM with tool calling support",
        topics=["llm", "agent"],
    )
    dossier = ResearchDossier(
        final_url=cand.url,
        http_ok=True,
        http_status=200,
        description=cand.summary,
        category="AI and Machine Learning",
        subcategory="Open-source AI models",
        local_installation_available="Yes",
        supported_os=["Windows", "Linux"],
    )
    os_rep = OpenSourceReport(is_open_source=True, open_source_status="Open Weights", primary_language="Python")
    prof, _, _ = agent.evaluate(cand, dossier, _make_pricing(), os_rep)
    assert "6GB VRAM" in prof.can_run_on_laptop
    assert prof.cloud_usage_necessary == "No"


def test_70b_model_flags_cloud_or_offload():
    agent = PersonalizationAgent()
    cand = RawCandidate(
        name="Llama-70B",
        url="https://huggingface.co/meta/Llama-70B",
        source_name="HF",
        source_url="https://huggingface.co/meta/Llama-70B",
        summary="70B parameter reasoning model",
    )
    dossier = ResearchDossier(
        final_url=cand.url,
        http_ok=True,
        http_status=200,
        description=cand.summary,
        category="AI and Machine Learning",
        subcategory="Open-source AI models",
        local_installation_available="Yes",
        supported_os=["Windows", "Linux"],
    )
    os_rep = OpenSourceReport(is_open_source=True, open_source_status="Open Weights")
    prof, _, _ = agent.evaluate(cand, dossier, _make_pricing(), os_rep)
    assert "exceeds 6GB" in prof.hardware_fit_notes
    assert "Partial" in prof.can_run_on_laptop
