# Pramana AI Radar

**Autonomous Free AI Tools Discovery, Pricing Forensics & Student Intelligence Department**

Pramana continuously discovers, verifies, scores, personalizes, and archives genuinely free AI tools and APIs worldwide—without ads, without fake-free trial traps, and without requiring your laptop to stay powered on.

Tailored specifically for a **3rd-Year Computer Engineering student (India)** running **Windows 11 • AMD Ryzen 7 7435HS • 16 GB RAM • NVIDIA RTX 4050 (6 GB VRAM)**.

## Key Capabilities

- **10-Agent Autonomous Pipeline**:
  1. `DiscoveryAgent` — Parallel discovery across GitHub Search API, Hugging Face Hub, Hacker News (`Show HN`), and Reddit RSS (`r/LocalLLaMA`, `r/opensource`) + emerging category detection.
  2. `ResearchAgent` — Live website & documentation inspection across all 20 required intelligence fields (explicitly marks unverifiable fields `UNKNOWN`).
  3. `PricingVerificationAgent` — Audits official pricing pages to detect trial-only traps, credit-card gates, one-time credit gimmicks, and India availability.
  4. `OpenSourceAgent` — Inspects GitHub stars, SPDX licenses (OSI vs source-available), maintenance activity, and archived status.
  5. `QualityEvaluationAgent` — Transparent 100-point rubric (`25 Free + 20 Usefulness + 15 Reliability + 15 Student Value + 10 Ease + 10 Performance + 5 Docs`) with explicit penalties.
  6. `PersonalizationAgent` — Evaluates RTX 4050 6 GB VRAM local execution fit (`Native`, `Quantized Q4_K_M`, `Cloud Required`) and career/startup/hackathon relevance.
  7. `DeduplicationAgent` — URL canonicalization, GitHub slug normalization, and fuzzy name matching.
  8. `ReportGenerationAgent` — Daily digests, 16-section Weekly Intelligence Reports + Weekly Top 10, publication-grade PDF (`ReportLab`), CSV, and Excel (`.xlsx`).
  9. `MonitoringAgent` — Re-verifies existing tools to log pricing changes, removed free tiers, and discontinued tools.
  10. `OrchestratorAgent` — Coordinates parallel execution, rotating SQLite backups, static Pages sync, and notifications.
- **18-Section Interactive Dashboard + 3D WebGL Spatial Constellation**:
  - Apple Luminary Gallery default studio + Sunset Apex & Midnight Carbon themes.
  - Side-by-side 4-tool comparison matrix, 20-field inspector modal, saved favorites, and one-click PDF/CSV/Excel exports.
  - Works dynamically via Flask API locally AND statically 24/7 via GitHub Pages.
- **100% Laptop-Independent Cloud Execution**:
  - GitHub Actions runs daily (`02:30 UTC` / `08:00 IST`) and weekly (`Sunday 03:30 UTC` / `09:00 IST`), commits updated data & PDFs, updates GitHub Pages, and pushes Telegram/Email alerts.

## Quick Start

```bash
pip install -r requirements.txt
pip install -e .

# Run a live daily discovery & verification pass
python -m pramana.cli daily --target 3

# Generate the Weekly Top 10 Intelligence Report (Markdown + JSON + PDF + CSV + XLSX)
python -m pramana.cli weekly

# Launch the interactive dashboard locally at http://127.0.0.1:8765
python -m pramana.cli serve
```

See [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md), [docs/CLOUD_DEPLOYMENT.md](docs/CLOUD_DEPLOYMENT.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [docs/FREE_TIER_LIMITS.md](docs/FREE_TIER_LIMITS.md).
