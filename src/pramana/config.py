"""Configuration, student profile, hardware constraints, and category taxonomy."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


def get_project_root() -> Path:
    """Resolve project root reliably on both Windows and Linux CI runners."""
    env_root = os.environ.get("PRAMANA_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "pramana.db"
CATALOG_JSON_PATH = DATA_DIR / "catalog.json"
REPORTS_DIR = DATA_DIR / "weekly_reports"
BACKUPS_DIR = DATA_DIR / "backups"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
DOCS_DIR = PROJECT_ROOT / "docs"
LOGS_DIR = PROJECT_ROOT / "logs"


@dataclass(frozen=True)
class HardwareProfile:
    os_name: str = "Windows 11"
    cpu: str = "AMD Ryzen 7 7435HS"
    ram_gb: int = 16
    gpu_name: str = "NVIDIA RTX 4050 Laptop GPU"
    vram_gb: float = 6.0


@dataclass(frozen=True)
class StudentProfile:
    academic_year: str = "3rd Year Computer Engineering"
    country: str = "India"
    budget_tier: str = "Zero / Student Budget"
    hardware: HardwareProfile = field(default_factory=HardwareProfile)
    core_interests: tuple[str, ...] = (
        "Artificial Intelligence",
        "Machine Learning",
        "Data Science",
        "AI Engineering",
        "Autonomous Agents",
        "Multi-Agent Systems",
        "Robotics",
        "Automation",
        "Python",
        "C++",
        "DSA",
        "Web Development",
        "Software Engineering",
        "Startups",
        "Research Projects",
        "Hackathons",
    )
    preference_order: tuple[str, ...] = (
        "Completely Free",
        "Free Open Source",
        "Generous Free Tier",
        "Free Student Plan",
        "Freemium Useful Free",
    )


STUDENT_PROFILE = StudentProfile()


# Exact 100-point rubric weights as specified
SCORE_WEIGHTS: Dict[str, int] = {
    "free_functionality": 25,
    "practical_usefulness": 20,
    "reliability": 15,
    "student_value": 15,
    "ease_of_use": 10,
    "performance": 10,
    "documentation": 5,
}


# Comprehensive Category Taxonomy (Sections A-H)
CATEGORY_TAXONOMY: Dict[str, List[str]] = {
    "AI and Machine Learning": [
        "AI chatbots and assistants",
        "LLM platforms",
        "Free LLM APIs",
        "Open-source AI models",
        "AI model hosting",
        "AI inference platforms",
        "AI research assistants",
        "AI agents and agent frameworks",
        "Multi-agent orchestration",
        "RAG and vector databases",
        "Fine-tuning tools",
        "AI evaluation and observability",
        "AI coding agents",
    ],
    "Coding and Development": [
        "AI coding assistants",
        "AI code editors",
        "Free IDEs",
        "Code generation",
        "Debugging assistants",
        "GitHub automation",
        "Website and application builders",
        "Backend development",
        "API development",
        "Database tools",
        "Testing and deployment",
        "DevOps and CI/CD",
    ],
    "Image and Design": [
        "AI image generation",
        "Image editing",
        "Background removal",
        "Logo generation",
        "UI/UX design",
        "Presentation generation",
        "Graphic design",
        "3D generation",
        "Animation",
    ],
    "Video and Content": [
        "AI video generation",
        "Video editing",
        "Text-to-video",
        "Image-to-video",
        "AI avatars",
        "Subtitle generation",
        "Video summarization",
        "Screen recording",
        "YouTube automation",
        "Content repurposing",
    ],
    "Audio and Voice": [
        "Text-to-speech",
        "Speech-to-text",
        "Voice cloning",
        "AI voice generation",
        "Voice changers",
        "Audio enhancement",
        "Noise removal",
        "Podcast production",
        "Music generation",
        "Real-time transcription",
    ],
    "Productivity and Research": [
        "AI note-taking",
        "PDF analysis",
        "Research paper discovery",
        "Academic research",
        "Document automation",
        "Spreadsheet AI",
        "Presentation creation",
        "Mind mapping",
        "Knowledge management",
        "Browser automation",
        "Workflow automation",
    ],
    "Career and Education": [
        "Free AI courses",
        "AI certifications",
        "Programming education",
        "DSA practice",
        "Interview preparation",
        "Resume building",
        "Portfolio development",
        "GitHub tools",
        "Internship discovery tools",
        "Hackathon tools",
    ],
    "Emerging AI": [
        "Local AI & Edge Inference",
        "MCP Servers & Toolchains",
        "Robotics & Embodied AI",
        "Browser & Computer-Use Agents",
        "Synthetic Data & Benchmarks",
    ],
}


@dataclass
class RuntimeConfig:
    daily_target: int = int(os.environ.get("PRAMANA_DAILY_TARGET", "3"))
    min_score: float = float(os.environ.get("PRAMANA_MIN_SCORE", "55"))
    request_timeout: int = int(os.environ.get("PRAMANA_REQUEST_TIMEOUT", "12"))
    dashboard_port: int = int(os.environ.get("PRAMANA_DASHBOARD_PORT", "8765"))
    github_token: str = os.environ.get("GITHUB_TOKEN", "")
    groq_api_key: str = os.environ.get("GROQ_API_KEY", "")
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    telegram_bot_token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.environ.get("TELEGRAM_CHAT_ID", "")
    smtp_host: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user: str = os.environ.get("SMTP_USER", "")
    smtp_pass: str = os.environ.get("SMTP_PASS", "")
    notify_email_to: str = os.environ.get("NOTIFY_EMAIL_TO", "")


def load_dotenv_if_present() -> None:
    """Load .env file into os.environ without overwriting existing env vars."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
