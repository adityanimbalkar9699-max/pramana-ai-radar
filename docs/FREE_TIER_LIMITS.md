# Free-Tier Infrastructure Limits & Mitigations

| Component | Free Platform | Official Free-Tier Limits | Pramana Mitigation |
| :--- | :--- | :--- | :--- |
| Cloud Scheduler | GitHub Actions (Public Repo) | Unlimited minutes for standard runners on public repos; max 6h/job; scheduled crons pause after **60 days** of zero repo commits. | Daily commits of `data/pramana.db` keep the repo active automatically, preventing the 60-day pause. |
| Cloud Scheduler (Private Repo) | GitHub Actions (Free Plan) | **2,000 minutes/month** + 500 MB artifact storage. | Each daily run takes ~45–90 seconds (~45 min/month total, <3% of quota). |
| GitHub API | GitHub REST Search & Repo API | **60 req/hr** unauthenticated; **1,000–5,000 req/hr** with `GITHUB_TOKEN`. | Workflows inject `${{ secrets.GITHUB_TOKEN }}`; per-run inspection budget is capped cleanly. |
| Dashboard Hosting | GitHub Pages | 1 GB site size, 100 GB bandwidth/month, static HTML/JS/JSON/PDF. | `docs/` holds lightweight static assets + `catalog.json` + latest PDF/CSV/XLSX (<10 MB). |
| Persistent Storage | Git-backed SQLite + JSON | GitHub soft repo limit ~1 GB–5 GB. | Rotating DB backups (`max_backups=7`) are excluded from Git via `.gitignore`; only compact `pramana.db` is committed. |
| Notifications | Telegram Bot API & Gmail SMTP | Telegram: ~30 msg/sec; Gmail SMTP: ~500 emails/day. | Pramana sends at most 1 daily digest (suppressed when empty) + 1 weekly report. |
