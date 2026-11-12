"""Agent 6: PersonalizationAgent — evaluates fit for 3rd-yr CE student & RTX 4050 6GB VRAM."""

from __future__ import annotations

import re
from typing import List, Tuple

from ..config import STUDENT_PROFILE
from ..models import PersonalizationProfile, PricingVerification, RawCandidate, UNKNOWN
from .opensource import OpenSourceReport
from .research import ResearchDossier


PARAM_SIZE_RE = re.compile(r"\b(\d{1,3})\s*[bB]\b")


class PersonalizationAgent:
    """Tailors every tool to the student's Windows 11 + Ryzen 7 + RTX 4050 (6GB VRAM) setup."""

    def evaluate(
        self,
        candidate: RawCandidate,
        dossier: ResearchDossier,
        pricing: PricingVerification,
        os_report: OpenSourceReport,
    ) -> Tuple[PersonalizationProfile, str, str]:
        """Returns (PersonalizationProfile, what_makes_it_useful, best_student_use_case)."""
        blob = f"{candidate.name} {dossier.description} {' '.join(candidate.topics)}".lower()
        vram_limit = STUDENT_PROFILE.hardware.vram_gb  # 6.0 GB

        # Determine RTX 4050 6GB VRAM / local execution fit
        param_matches = [int(m) for m in PARAM_SIZE_RE.findall(candidate.name + " " + candidate.summary)]
        max_b = max(param_matches) if param_matches else 0

        if dossier.local_installation_available == "Yes":
            if max_b >= 13:
                can_run = "Partial (Needs Cloud or Heavy Quantization >6GB VRAM)"
                cloud_req = "Recommended for >13B weights"
                hw_note = f"{max_b}B parameter model exceeds 6GB RTX 4050 VRAM at standard precision; offload layers to 16GB system RAM or use free cloud APIs."
            elif 4 <= max_b <= 9:
                can_run = "Yes (Quantized Q4_K_M fits 6GB VRAM)"
                cloud_req = "No"
                hw_note = f"Fits cleanly in RTX 4050 6GB VRAM using 4-bit GGUF/QLoRA quantization (~4.2-5.4 GB VRAM) + 16GB RAM."
            elif 1 <= max_b <= 3 or "kokoro" in blob or "faster-whisper" in blob:
                can_run = "Yes (Native Fast on RTX 4050 6GB)"
                cloud_req = "No"
                hw_note = "Lightweight footprint runs at high speed directly on RTX 4050 6GB VRAM."
            elif "Web" in dossier.supported_os and "Windows" not in dossier.supported_os and not os_report.is_open_source:
                can_run = "Yes (Browser)"
                cloud_req = "Yes"
                hw_note = "Runs in Windows 11 browser; compute handled on free cloud tier."
            elif "Windows" in dossier.supported_os or os_report.primary_language.lower() in ("python", "javascript", "typescript", "go", "rust"):
                can_run = "Yes (Native Windows 11)"
                cloud_req = "No" if os_report.is_open_source else "Optional"
                hw_note = f"Compatible with Windows 11 ({STUDENT_PROFILE.hardware.cpu}, 16GB RAM, RTX 4050 6GB)."
            else:
                can_run = "Yes (Check Docker/WSL2 on Windows 11)"
                cloud_req = "Optional"
                hw_note = "Runs locally via WSL2 / Docker Desktop on Windows 11 (16GB RAM)."
        elif "Web" in dossier.supported_os or "huggingface.co/spaces" in dossier.final_url.lower():
            can_run = "Yes (Zero-Install Cloud Web)"
            cloud_req = "Yes"
            hw_note = f"Zero local VRAM/RAM load on your {vram_limit:.0f}GB RTX 4050; runs via cloud free tier."
        else:
            can_run = UNKNOWN
            cloud_req = UNKNOWN
            hw_note = "Verify local Windows 11 / VRAM requirements in official docs."

        # Determine Priority Track & Skills
        skills: List[str] = []
        if any(k in blob for k in ("agent", "multi-agent", "langgraph", "crewai", "mcp")):
            track = "Agentic AI & Multi-Agent Systems"
            skills.extend(["Multi-Agent Orchestration", "Tool Calling & MCP", "Autonomous Workflows"])
        elif any(k in blob for k in ("rag", "vector", "qdrant", "fine-tun", "unsloth", "ollama", "llm", "inference")):
            track = "AI Engineering & Applied ML"
            skills.extend(["LLM Systems Engineering", "RAG / Vector Search", "Model Optimization"])
        elif any(k in blob for k in ("coding", "code", "git", "supabase", "workers", "api", "playwright")):
            track = "Full-Stack & Dev Automation"
            skills.extend(["Software Engineering", "API & Backend Design", "Developer Productivity"])
        elif any(k in blob for k in ("dsa", "neetcode", "roadmap", "kaggle", "notebooklm", "zotero")):
            track = "Portfolio, Research & Placements"
            skills.extend(["DSA & Interview Prep", "Academic Research", "Hackathon Prototyping"])
        else:
            track = "Creative & Multimodal AI"
            skills.extend(["Multimodal Prototyping", "Demo & Pitch Creation"])

        if "python" in blob or os_report.primary_language.lower() == "python":
            skills.append("Python")
        if "c++" in blob or os_report.primary_language.lower() in ("c++", "c"):
            skills.append("C++ / Systems")

        helps_career = dossier.category in (
            "AI and Machine Learning",
            "Coding and Development",
            "Career and Education",
            "Emerging AI",
        )
        helps_startup = (
            pricing.is_genuinely_free
            and ("Free API" in dossier.api_availability or os_report.is_open_source or "Workers" in candidate.name or "Supabase" in candidate.name)
        )
        useful_college = True
        improves_prod = True

        how_to_use = (
            f"Integrate {candidate.name} into your {track.lower()} stack on Windows 11. "
            f"{hw_note} Use its {pricing.free_tier_type.lower()} access to prototype without burning your student budget."
        )
        what_makes_useful = (
            f"Eliminates paywalls via {pricing.free_tier_type}; delivers strong {dossier.subcategory.lower()} utility "
            f"with {dossier.api_availability if dossier.api_availability != UNKNOWN else 'direct'} workflow support."
        )
        best_use_case = (
            f"Build a portfolio-grade {dossier.subcategory.lower()} module or 24-hour hackathon MVP on your RTX 4050 laptop."
            if not helps_startup
            else f"Ship a zero-infrastructure-cost hackathon MVP or SaaS prototype using {candidate.name}'s {pricing.free_tier_type}."
        )

        profile = PersonalizationProfile(
            how_to_use=how_to_use,
            skills_developed=list(dict.fromkeys(skills))[:5],
            helps_ai_engineering_career=helps_career,
            useful_for_college_projects=useful_college,
            helps_startup_building=helps_startup,
            improves_productivity=improves_prod,
            can_run_on_laptop=can_run,
            cloud_usage_necessary=cloud_req,
            hardware_fit_notes=hw_note,
            priority_track=track,
        )
        return profile, what_makes_useful, best_use_case
