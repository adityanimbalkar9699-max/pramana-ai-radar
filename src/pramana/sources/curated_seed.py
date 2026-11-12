"""Verified baseline directory of high-impact free AI tools across all 7+ categories.

Note: Every candidate here is still passed through the live HTTP Verification,
Pricing Verification, Open-Source, Scoring, and Personalization pipeline so
statuses, pricing changes, stars, and availability are verified live.
"""

from __future__ import annotations

from typing import List

from ..models import RawCandidate


def get_verified_seed_candidates() -> List[RawCandidate]:
    """Diverse, high-utility student-first AI tools spanning Categories A-H."""
    specs = [
        # A. AI & ML
        ("Ollama", "https://ollama.com", "https://github.com/ollama/ollama",
         "AI and Machine Learning", "AI inference platforms",
         "Run open-weight LLMs (Llama, Qwen, DeepSeek, Gemma) locally on Windows with GPU acceleration and OpenAI-compatible API."),
        ("GroqCloud", "https://groq.com", "",
         "AI and Machine Learning", "Free LLM APIs",
         "Ultra-low-latency LPU inference platform offering a generous free API tier for Llama, Gemma, and Whisper models."),
        ("Google AI Studio", "https://aistudio.google.com", "",
         "AI and Machine Learning", "LLM platforms",
         "Official Gemini prototyping console and free-tier developer API with large context window and multimodal support."),
        ("OpenRouter", "https://openrouter.ai", "",
         "AI and Machine Learning", "Free LLM APIs",
         "Unified OpenAI-compatible LLM gateway hosting dozens of permanently `:free` community and open-weight models."),
        ("LangGraph", "https://www.langchain.com/langgraph", "https://github.com/langchain-ai/langgraph",
         "AI and Machine Learning", "Multi-agent orchestration",
         "Open-source stateful multi-agent orchestration framework built for cyclic, durable, human-in-the-loop agent workflows."),
        ("Qdrant", "https://qdrant.tech", "https://github.com/qdrant/qdrant",
         "AI and Machine Learning", "RAG and vector databases",
         "High-performance Rust vector database with local Docker/binary mode and a permanent 1 GB free cloud cluster."),
        ("LM Studio", "https://lmstudio.ai", "",
         "AI and Machine Learning", "AI model hosting",
         "Desktop GUI for discovering, downloading, and serving quantized GGUF models locally on Windows/RTX GPUs."),
        ("Arize Phoenix", "https://phoenix.arize.com", "https://github.com/Arize-ai/phoenix",
         "AI and Machine Learning", "AI evaluation and observability",
         "Open-source AI observability, OpenTelemetry tracing, and RAG/agent evaluation suite runnable locally via pip."),
        ("Unsloth", "https://unsloth.ai", "https://github.com/unslothai/unsloth",
         "AI and Machine Learning", "Fine-tuning tools",
         "Memory-efficient LoRA/QLoRA fine-tuning library enabling 2x faster training and fitting 7B-8B fine-tunes into 6GB VRAM."),

        # B. Coding & Development
        ("Continue.dev", "https://www.continue.dev", "https://github.com/continuedev/continue",
         "Coding and Development", "AI coding assistants",
         "Open-source VS Code and JetBrains AI coding assistant supporting Ollama local models and free APIs."),
        ("GitHub Student Developer Pack", "https://education.github.com/pack", "",
         "Coding and Development", "AI coding assistants",
         "Official student program granting free GitHub Copilot Pro, cloud credits, domains, and developer tooling to verified students."),
        ("Supabase", "https://supabase.com", "https://github.com/supabase/supabase",
         "Coding and Development", "Database tools",
         "Open-source Firebase alternative with Postgres, pgvector for RAG, auth, and edge functions with a permanent free tier."),
        ("Cloudflare Workers", "https://workers.cloudflare.com", "",
         "Coding and Development", "Backend development",
         "Serverless edge compute and cron triggers with 100,000 free requests/day and Workers AI free neuron allocation."),
        ("Cline", "https://cline.bot", "https://github.com/cline/cline",
         "Coding and Development", "AI coding agents",
         "Autonomous open-source VS Code coding agent supporting MCP tools, terminal commands, and custom free/local API keys."),

        # C. Image & Design
        ("ComfyUI", "https://www.comfy.org", "https://github.com/comfyanonymous/ComfyUI",
         "Image and Design", "AI image generation",
         "Node-based open-source Stable Diffusion & Flux workflow engine with low-VRAM (--lowvram) support for 6GB GPUs."),
        ("Excalidraw", "https://excalidraw.com", "https://github.com/excalidraw/excalidraw",
         "Image and Design", "UI/UX design",
         "Open-source virtual whiteboard with built-in AI diagram/Mermaid generation for system architecture and hackathon pitches."),
        ("Blender", "https://www.blender.org", "https://github.com/blender/blender",
         "Image and Design", "3D generation",
         "100% free open-source 3D creation suite with CUDA/OptiX RTX 4050 acceleration and Python scripting API."),

        # D. Video & Content
        ("OBS Studio", "https://obsproject.com", "https://github.com/obsproject/obs-studio",
         "Video and Content", "Screen recording",
         "Free open-source screen recording and streaming studio with NVIDIA NVENC hardware encoding for project demos."),
        ("yt-dlp", "https://github.com/yt-dlp/yt-dlp", "https://github.com/yt-dlp/yt-dlp",
         "Video and Content", "Subtitle generation",
         "Open-source CLI tool to fetch video/audio and transcripts cleanly for local Whisper summarization pipelines."),

        # E. Audio & Voice
        ("Faster-Whisper", "https://github.com/SYSTRAN/faster-whisper", "https://github.com/SYSTRAN/faster-whisper",
         "Audio and Voice", "Speech-to-text",
         "CTranslate2-accelerated Whisper inference up to 4x faster, running Whisper small/medium effortlessly in 6GB VRAM."),
        ("Kokoro TTS", "https://github.com/hexgrad/kokoro", "https://github.com/hexgrad/kokoro",
         "Audio and Voice", "Text-to-speech",
         "Ultra-lightweight 82M-parameter open-weight Apache-2.0 text-to-speech model producing natural voices locally."),

        # F. Productivity & Research
        ("Google NotebookLM", "https://notebooklm.google.com", "",
         "Productivity and Research", "PDF analysis",
         "Free AI research workspace grounded strictly in uploaded PDFs, lecture notes, and textbooks with Audio Overviews."),
        ("Zotero", "https://www.zotero.org", "https://github.com/zotero/zotero",
         "Productivity and Research", "Academic research",
         "Free open-source research paper manager with PDF annotation and AI plugin ecosystem for literature reviews."),
        ("n8n", "https://n8n.io", "https://github.com/n8n-io/n8n",
         "Productivity and Research", "Workflow automation",
         "Source-available workflow & AI agent automation engine self-hostable for free via Docker or npm."),
        ("Playwright", "https://playwright.dev", "https://github.com/microsoft/playwright",
         "Productivity and Research", "Browser automation",
         "Open-source cross-browser automation framework by Microsoft for headless scraping, E2E testing, and web agents."),

        # G. Career & Education
        ("Kaggle", "https://www.kaggle.com", "",
         "Career and Education", "Hackathon tools",
         "Free cloud notebooks providing 30 hours/week of NVIDIA T4/P100 GPUs, datasets, competitions, and micro-courses."),
        ("NeetCode", "https://neetcode.io", "",
         "Career and Education", "DSA practice",
         "Structured DSA roadmap, video explanations, and coding interview preparation with free core tracks."),
        ("roadmap.sh", "https://roadmap.sh", "https://github.com/kamranahmedse/developer-roadmap",
         "Career and Education", "Programming education",
         "Open-source community-curated engineering and AI Engineer learning roadmaps with AI study guides."),

        # H. Emerging AI
        ("Model Context Protocol (MCP) SDK", "https://modelcontextprotocol.io", "https://github.com/modelcontextprotocol/python-sdk",
         "Emerging AI", "MCP Servers & Toolchains",
         "Open protocol standardizing how AI agents connect to external tools, databases, and local filesystems."),
        ("CrewAI", "https://www.crewai.com", "https://github.com/crewAIInc/crewAI",
         "AI and Machine Learning", "Multi-agent orchestration",
         "Open-source Python framework for orchestrating role-playing autonomous AI agent teams."),
    ]

    return [
        RawCandidate(
            name=name,
            url=url,
            source_name="Pramana Verified Directory",
            source_url=url,
            summary=summary,
            github_repo=gh,
            category_hint=cat,
            subcategory_hint=subcat,
        )
        for name, url, gh, cat, subcat, summary in specs
    ]
