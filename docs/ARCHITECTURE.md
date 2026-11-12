# Pramana Architecture & 10-Agent Specification

## Execution Flow (DAG)

```text
[Scheduled Cloud Trigger: GitHub Actions / CLI]
        │
        ▼
[OrchestratorAgent] ──► Creates rotating SQLite backup (data/backups/)
        │
        ├──► [DiscoveryAgent] (ThreadPoolExecutor across GitHub, HuggingFace, HN, Reddit)
        │           └──► Emerging Category Detector (MCP, Local AI, Browser Agents, Robotics)
        │
        ├──► [DeduplicationAgent] (Canonical URL + GitHub slug + Fuzzy name >= 0.92)
        │
        ├──► Parallel Verification Pool (per unique candidate):
        │       ├── [ResearchAgent] (HTTP fetch, lxml extraction, OS, API, Docs, Privacy)
        │       ├── [OpenSourceAgent] (GitHub Repo API: stars, SPDX license, archived check)
        │       ├── [PricingVerificationAgent] (/pricing probe, trial-trap & CC regex, India check)
        │       ├── [QualityEvaluationAgent] (100-pt rubric - penalties)
        │       └── [PersonalizationAgent] (RTX 4050 6GB VRAM fit + 3rd-yr CE alignment)
        │
        ├──► [PramanaDatabase] (SQLite WAL + pricing_history + rejected_candidates)
        │
        ├──► [MonitoringAgent] (Re-verifies oldest-checked active tools for drift/404)
        │
        ├──► [ReportGenerationAgent] (Daily MD, Weekly 16-section MD/JSON/PDF, CSV, XLSX)
        │
        └──► [NotificationManager] (Telegram + SMTP Email w/ PDF; suppressed if 0 discoveries)
```

## Persistence & Zero-Cost Storage Model

- Primary transactional store: `data/pramana.db` (SQLite with `tools`, `pricing_history`, `discovery_runs`, `weekly_reports`, `rejected_candidates`, `settings`).
- Static cloud mirror: `docs/data/catalog.json` + `docs/reports/` — automatically synced after every daily/weekly run so GitHub Pages serves live verified data 24/7 with zero paid database hosting.
