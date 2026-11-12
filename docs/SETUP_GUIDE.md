# Local Setup & Operations Guide (Windows 11)

## Prerequisites
- Python 3.10+ (`python --version`)
- Git & GitHub CLI (`gh`)

## Installation

```powershell
cd S:\Antigravity\projects\pramana-ai-radar
python -m pip install -r requirements.txt
python -m pip install -e .
Copy-Item .env.example .env
```

## CLI Commands

- `python -m pramana.cli daily --target 3` — Run live multi-source discovery, pricing verification, 100-pt scoring, RTX 4050 personalization, and daily digest.
- `python -m pramana.cli weekly` — Generate the 16-section Weekly Intelligence Report, Weekly Top 10, editorial PDF, CSV, and Excel workbook.
- `python -m pramana.cli serve` — Start the Flask API + Dashboard at `http://127.0.0.1:8765`.
- `python -m pramana.cli export` — Regenerate CSV, XLSX, PDF, and sync `docs/` for GitHub Pages.
- `python -m pramana.cli doctor` — Print DB counts and notification/token configuration health.

## Testing

```powershell
python -m pytest -v
```
