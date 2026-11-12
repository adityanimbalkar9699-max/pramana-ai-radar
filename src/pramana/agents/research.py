"""Agent 2: ResearchAgent — inspects live websites, documentation, capabilities, OS & API support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ..config import CATEGORY_TAXONOMY
from ..models import RawCandidate, UNKNOWN
from ..sources.base import SafeHttpClient, extract_html_metadata


CATEGORY_KEYWORD_RULES: List[Tuple[str, str, Tuple[str, ...]]] = [
    ("AI and Machine Learning", "Multi-agent orchestration", ("multi-agent", "langgraph", "crewai", "autogen", "swarm")),
    ("AI and Machine Learning", "AI agents and agent frameworks", ("ai agent", "agent framework", "autonomous agent", "tool calling")),
    ("AI and Machine Learning", "RAG and vector databases", ("vector database", "rag", "qdrant", "pgvector", "retrieval", "embedding")),
    ("AI and Machine Learning", "Free LLM APIs", ("llm api", "inference api", "openrouter", "groq", "openai-compatible")),
    ("AI and Machine Learning", "Fine-tuning tools", ("fine-tun", "lora", "qlora", "unsloth", "peft")),
    ("AI and Machine Learning", "AI evaluation and observability", ("observability", "tracing", "eval", "phoenix", "langfuse")),
    ("AI and Machine Learning", "AI inference platforms", ("ollama", "vllm", "llama.cpp", "inference", "local llm", "lm studio")),
    ("Coding and Development", "AI coding agents", ("coding agent", "cline", "swe-agent", "autonomous coding")),
    ("Coding and Development", "AI coding assistants", ("coding assistant", "copilot", "autocomplete", "continue", "code editor")),
    ("Coding and Development", "Database tools", ("postgres", "supabase", "database", "sqlite", "turso")),
    ("Coding and Development", "Backend development", ("serverless", "workers", "backend", "edge compute", "api gateway")),
    ("Image and Design", "3D generation", ("3d", "blender", "mesh", "gaussian splatting", "nerf")),
    ("Image and Design", "AI image generation", ("image generation", "stable diffusion", "flux", "comfyui", "diffusion")),
    ("Image and Design", "UI/UX design", ("whiteboard", "diagram", "ui/ux", "figma", "excalidraw", "design")),
    ("Video and Content", "Screen recording", ("screen record", "obs", "streaming")),
    ("Video and Content", "AI video generation", ("text-to-video", "video generation", "image-to-video", "video edit")),
    ("Audio and Voice", "Speech-to-text", ("whisper", "speech-to-text", "transcription", "stt", "asr")),
    ("Audio and Voice", "Text-to-speech", ("text-to-speech", "tts", "voice cloning", "kokoro", "speech synthesis")),
    ("Productivity and Research", "Workflow automation", ("workflow automation", "n8n", "zapier", "automation engine")),
    ("Productivity and Research", "Browser automation", ("playwright", "browser automation", "puppeteer", "web scraping")),
    ("Productivity and Research", "PDF analysis", ("pdf", "notebooklm", "document analysis", "paper")),
    ("Productivity and Research", "Academic research", ("zotero", "citation", "arxiv", "literature review")),
    ("Career and Education", "DSA practice", ("dsa", "leetcode", "neetcode", "interview")),
    ("Career and Education", "Programming education", ("roadmap", "course", "tutorial", "certification")),
    ("Career and Education", "Hackathon tools", ("kaggle", "hackathon", "competition", "gpu notebook")),
    ("Emerging AI", "MCP Servers & Toolchains", ("model context protocol", "mcp server", "mcp")),
]


@dataclass
class ResearchDossier:
    final_url: str
    http_ok: bool
    http_status: int
    title: str = ""
    description: str = ""
    visible_text: str = ""
    category: str = "AI and Machine Learning"
    subcategory: str = "AI tools"
    main_capabilities: List[str] = field(default_factory=list)
    supported_os: List[str] = field(default_factory=lambda: [UNKNOWN])
    api_availability: str = UNKNOWN
    local_installation_available: str = UNKNOWN
    official_documentation: str = UNKNOWN
    pricing_links: List[str] = field(default_factory=list)
    discovered_github: str = ""
    privacy_considerations: str = UNKNOWN
    limitations: List[str] = field(default_factory=list)


def classify_category(candidate: RawCandidate, text_blob: str) -> Tuple[str, str]:
    if candidate.category_hint in CATEGORY_TAXONOMY:
        sub = candidate.subcategory_hint or CATEGORY_TAXONOMY[candidate.category_hint][0]
        return candidate.category_hint, sub

    low = f"{candidate.name} {candidate.summary} {' '.join(candidate.topics)} {text_blob[:4000]}".lower()
    for cat, subcat, keywords in CATEGORY_KEYWORD_RULES:
        if any(kw in low for kw in keywords):
            return cat, subcat
    return "AI and Machine Learning", "AI chatbots and assistants"


class ResearchAgent:
    """Performs live website inspection and structured metadata extraction."""

    def __init__(self, client: SafeHttpClient) -> None:
        self.client = client

    def investigate(self, candidate: RawCandidate) -> ResearchDossier:
        fetch_res = self.client.fetch(candidate.url)
        meta: Dict[str, object] = {
            "title": "",
            "description": "",
            "visible_text": "",
            "pricing_links": [],
            "docs_links": [],
            "github_links": [],
        }
        if fetch_res.ok and fetch_res.text:
            meta = extract_html_metadata(fetch_res.text, fetch_res.final_url)

        visible_text = str(meta.get("visible_text", ""))
        description = (
            candidate.summary
            or str(meta.get("description", ""))
            or str(meta.get("title", ""))
            or UNKNOWN
        )
        combined_low = f"{candidate.name} {description} {' '.join(candidate.topics)} {visible_text}".lower()

        cat, subcat = classify_category(candidate, combined_low)

        # Supported OS detection from actual text/repo signals
        os_list: List[str] = []
        if any(k in combined_low for k in ("windows", "win32", "winget", ".exe", "cross-platform")):
            os_list.append("Windows")
        if any(k in combined_low for k in ("linux", "ubuntu", "docker", "cross-platform")):
            os_list.append("Linux")
        if any(k in combined_low for k in ("macos", "mac os", "homebrew", "darwin", "cross-platform")):
            os_list.append("macOS")
        if any(k in combined_low for k in ("web app", "browser", "cloud", "saas", "aistudio", "huggingface.co/spaces", "notebooklm")):
            os_list.append("Web")
        if candidate.language.lower() in ("python", "javascript", "typescript", "rust", "go"):
            for p in ("Windows", "Linux", "macOS"):
                if p not in os_list:
                    os_list.append(p)
        if not os_list:
            os_list = [UNKNOWN]

        # API availability
        if any(k in combined_low for k in ("free api", "free tier api", "openai-compatible", "rest api", "sdk", "api key")):
            if "free" in combined_low and "api" in combined_low:
                api_avail = "Free API"
            elif "local" in combined_low or "localhost" in combined_low:
                api_avail = "Local OpenAI-Compatible API"
            else:
                api_avail = "API Available (Check Tier)"
        elif candidate.language.lower() == "python":
            api_avail = "Python Library / Local SDK"
        else:
            api_avail = UNKNOWN

        # Local install availability
        if any(k in combined_low for k in ("pip install", "npm install", "docker", "ollama", "download", "self-host", "git clone", "local")) or bool(candidate.github_repo):
            local_avail = "Yes"
        elif any(k in combined_low for k in ("cloud-only", "web-based", "saas")) and not candidate.github_repo:
            local_avail = "No"
        else:
            local_avail = UNKNOWN

        # Docs link
        docs_links = list(meta.get("docs_links") or [])
        if docs_links:
            official_docs = str(docs_links[0])
        elif candidate.github_repo:
            official_docs = f"{candidate.github_repo.rstrip('/')}/blob/main/README.md"
        else:
            official_docs = UNKNOWN

        # Capabilities synthesis strictly from observed summary/topics
        caps: List[str] = []
        if candidate.topics:
            caps.extend([t.replace("-", " ").title() for t in candidate.topics[:4]])
        if description != UNKNOWN and len(caps) < 3:
            caps.append(description[:110].rstrip(".") + ".")
        if not caps:
            caps = [f"Core {subcat} capabilities"]

        # Privacy consideration note
        if local_avail == "Yes" and ("github.com" in (candidate.github_repo or candidate.url) or "local" in combined_low):
            privacy = "Runs locally on device; data stays private unless optional cloud APIs are connected."
        elif "google" in fetch_res.final_url.lower() or "free" in combined_low:
            privacy = "Cloud service: verify whether free-tier inputs are used for model improvement before uploading sensitive data."
        else:
            privacy = UNKNOWN

        gh_links = list(meta.get("github_links") or [])
        discovered_gh = candidate.github_repo or (str(gh_links[0]) if gh_links else "")

        limitations: List[str] = []
        if not fetch_res.ok:
            limitations.append(f"Official URL returned HTTP {fetch_res.status_code or 'error'} during automated check.")

        return ResearchDossier(
            final_url=fetch_res.final_url or candidate.url,
            http_ok=fetch_res.ok,
            http_status=fetch_res.status_code,
            title=str(meta.get("title", "")),
            description=description,
            visible_text=visible_text,
            category=cat,
            subcategory=subcat,
            main_capabilities=caps[:5],
            supported_os=os_list,
            api_availability=api_avail,
            local_installation_available=local_avail,
            official_documentation=official_docs,
            pricing_links=list(meta.get("pricing_links") or []),
            discovered_github=discovered_gh,
            privacy_considerations=privacy,
            limitations=limitations,
        )
