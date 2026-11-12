"""Specialized multi-agent modules for Pramana AI Radar."""

from .deduplication import DeduplicationAgent, canonicalize_url, make_canonical_key
from .discovery import DiscoveryAgent
from .monitoring import MonitoringAgent
from .opensource import OpenSourceAgent
from .orchestrator import OrchestratorAgent
from .personalization import PersonalizationAgent
from .pricing import PricingVerificationAgent
from .quality import QualityEvaluationAgent
from .reporting import ReportGenerationAgent
from .research import ResearchAgent

__all__ = [
    "DeduplicationAgent",
    "DiscoveryAgent",
    "MonitoringAgent",
    "OpenSourceAgent",
    "OrchestratorAgent",
    "PersonalizationAgent",
    "PricingVerificationAgent",
    "QualityEvaluationAgent",
    "ReportGenerationAgent",
    "ResearchAgent",
    "canonicalize_url",
    "make_canonical_key",
]
