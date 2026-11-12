"""Hugging Face Hub (Models, Spaces, Daily Papers) discovery source."""

from __future__ import annotations

from typing import List

from ..models import RawCandidate
from .base import SafeHttpClient


class HuggingFaceDiscoverySource:
    name = "Hugging Face"

    def __init__(self, client: SafeHttpClient) -> None:
        self.client = client

    def discover(self, limit: int = 12) -> List[RawCandidate]:
        candidates: List[RawCandidate] = []

        # 1. Trending/popular interactive Spaces (free hosted AI tools)
        spaces = self.client.fetch_json(
            "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=10"
        )
        if isinstance(spaces, list):
            for sp in spaces:
                sp_id = sp.get("id", "")
                if not sp_id:
                    continue
                sdk = sp.get("sdk", "gradio")
                title = sp.get("cardData", {}).get("title") if isinstance(sp.get("cardData"), dict) else None
                name = title or sp_id.split("/")[-1]
                url = f"https://huggingface.co/spaces/{sp_id}"
                tags = list(sp.get("tags") or [])
                candidates.append(
                    RawCandidate(
                        name=str(name),
                        url=url,
                        source_name="Hugging Face Spaces",
                        source_url=url,
                        summary=f"Free hosted Hugging Face {sdk} Space ({sp_id}) with {sp.get('likes', 0)} likes.",
                        topics=tags[:8],
                        license_name="Open Space / Check Model Card",
                        category_hint="AI and Machine Learning",
                        subcategory_hint="AI model hosting",
                        stars=int(sp.get("likes", 0)),
                        extra={"hf_type": "space", "sdk": sdk, "hf_id": sp_id},
                    )
                )

        # 2. Trending open-weights models (especially compact/student-friendly models)
        models = self.client.fetch_json(
            "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=10"
        )
        if isinstance(models, list):
            for m in models:
                mid = m.get("id", "")
                if not mid:
                    continue
                url = f"https://huggingface.co/{mid}"
                tags = list(m.get("tags") or [])
                pipeline_tag = m.get("pipeline_tag", "text-generation")
                subcat = "Open-source AI models"
                cat = "AI and Machine Learning"
                if "text-to-image" in pipeline_tag or "image" in pipeline_tag:
                    cat, subcat = "Image and Design", "AI image generation"
                elif "speech" in pipeline_tag or "audio" in pipeline_tag:
                    cat, subcat = "Audio and Voice", "Text-to-speech"

                candidates.append(
                    RawCandidate(
                        name=mid.split("/")[-1],
                        url=url,
                        source_name="Hugging Face Models",
                        source_url=url,
                        summary=f"Trending open-weights model ({mid}) for {pipeline_tag}; {m.get('downloads', 0):,} downloads.",
                        topics=tags[:8],
                        license_name=next((t.replace("license:", "") for t in tags if t.startswith("license:")), "Open Weights"),
                        category_hint=cat,
                        subcategory_hint=subcat,
                        stars=int(m.get("likes", 0)),
                        extra={"hf_type": "model", "pipeline_tag": pipeline_tag, "hf_id": mid},
                    )
                )

        return candidates[:limit]
