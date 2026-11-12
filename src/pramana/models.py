"""Strongly-typed domain models for tools, verification, scoring, and personalization."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


UNKNOWN = "UNKNOWN"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass
class RawCandidate:
    """Raw candidate discovered by a Discovery source before deep verification."""

    name: str
    url: str
    source_name: str
    source_url: str
    summary: str = ""
    github_repo: str = ""
    stars: int = 0
    topics: List[str] = field(default_factory=list)
    language: str = ""
    license_name: str = ""
    category_hint: str = ""
    subcategory_hint: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PricingVerification:
    """Verified pricing & free-tier truth extracted from official sources."""

    free_tier_type: str = UNKNOWN  # Completely Free | Open Source | Free Tier | Free Student Plan | Freemium | Trial Only | Paid
    is_genuinely_free: bool = False
    free_plan_details: str = UNKNOWN
    free_usage_limits: str = UNKNOWN
    credit_card_required: str = UNKNOWN  # "No" | "Yes" | "UNKNOWN"
    registration_required: str = UNKNOWN  # "No" | "Yes" | "UNKNOWN"
    is_trial_only: bool = False
    is_one_time_credits_only: bool = False
    free_quota_cadence: str = UNKNOWN  # "Unlimited" | "Daily Reset" | "Monthly Reset" | "Starter Credits" | "UNKNOWN"
    india_available: str = UNKNOWN  # "Yes" | "Restricted" | "UNKNOWN"
    fake_free_flags: List[str] = field(default_factory=list)
    pricing_url: str = ""
    verification_notes: str = ""
    verified_at: str = field(default_factory=utc_now_iso)


@dataclass
class ScoreBreakdown:
    """100-point rubric breakdown plus transparent penalties."""

    free_functionality: float = 0.0  # /25
    practical_usefulness: float = 0.0  # /20
    reliability: float = 0.0  # /15
    student_value: float = 0.0  # /15
    ease_of_use: float = 0.0  # /10
    performance: float = 0.0  # /10
    documentation: float = 0.0  # /5
    penalties: float = 0.0
    penalty_reasons: List[str] = field(default_factory=list)
    total_score: float = 0.0
    explanation: str = ""

    def compute_total(self) -> float:
        raw = (
            self.free_functionality
            + self.practical_usefulness
            + self.reliability
            + self.student_value
            + self.ease_of_use
            + self.performance
            + self.documentation
        )
        self.total_score = round(max(0.0, min(100.0, raw - self.penalties)), 1)
        return self.total_score


@dataclass
class PersonalizationProfile:
    """Tailored evaluation for 3rd-year CE student with RTX 4050 6GB VRAM."""

    how_to_use: str = ""
    skills_developed: List[str] = field(default_factory=list)
    helps_ai_engineering_career: bool = True
    useful_for_college_projects: bool = True
    helps_startup_building: bool = False
    improves_productivity: bool = True
    can_run_on_laptop: str = UNKNOWN  # "Yes (Native)" | "Yes (Quantized / Fits 6GB VRAM)" | "CPU Only" | "No (Cloud Required)" | "UNKNOWN"
    cloud_usage_necessary: str = UNKNOWN  # "No" | "Optional" | "Yes" | "UNKNOWN"
    hardware_fit_notes: str = ""
    priority_track: str = ""  # e.g., "Agentic AI & Multi-Agent", "AI Engineering", "DSA & Portfolio"


@dataclass
class ToolRecord:
    """Complete 20-field verified tool record + scoring + personalization + lineage."""

    # 20 Mandatory Discovery Fields
    name: str
    official_website: str
    category: str
    subcategory: str
    short_description: str
    main_capabilities: List[str] = field(default_factory=list)
    what_makes_it_useful: str = UNKNOWN
    free_plan_details: str = UNKNOWN
    free_usage_limits: str = UNKNOWN
    credit_card_required: str = UNKNOWN
    registration_required: str = UNKNOWN
    open_source_status: str = UNKNOWN  # "Open Source (MIT)" | "Open Source" | "Closed Source" | "Open Weights" | "UNKNOWN"
    github_repository: str = ""
    supported_os: List[str] = field(default_factory=lambda: [UNKNOWN])
    api_availability: str = UNKNOWN  # "Free API" | "Local API" | "Paid API" | "No" | "UNKNOWN"
    local_installation_available: str = UNKNOWN  # "Yes" | "No" | "UNKNOWN"
    important_limitations: List[str] = field(default_factory=list)
    privacy_considerations: str = UNKNOWN
    last_verification_date: str = field(default_factory=today_iso)
    official_documentation: str = UNKNOWN
    best_student_use_case: str = UNKNOWN

    # Verification, Scoring, Personalization, Memory
    canonical_key: str = ""
    free_tier_type: str = UNKNOWN
    is_genuinely_free: bool = True
    india_available: str = UNKNOWN
    score: float = 0.0
    score_breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    personalization: PersonalizationProfile = field(default_factory=PersonalizationProfile)
    sources: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    stars: int = 0
    license_name: str = UNKNOWN
    discovery_date: str = field(default_factory=today_iso)
    status: str = "active"  # active | pricing_changed | discontinued | rejected_fake_free
    user_rating: Optional[int] = None
    is_saved: bool = False
    previous_pricing_info: str = ""
    direct_app_url: str = ""
    pricing_url: str = ""
    web_only: bool = False
    free_quota_cadence: str = UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
