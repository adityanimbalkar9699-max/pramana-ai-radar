# Cloud Deployment Guide (100% Laptop-Independent)

Local scripts and Antigravity sessions **cannot** execute when your Windows 11 laptop is shut down. Pramana solves this using **GitHub Actions + GitHub Pages** on 100% free infrastructure.

## Step 1: Push Repository to GitHub

```bash
git init
git add .
git commit -m "feat: initial Pramana AI Radar autonomous intelligence system"
gh repo create adityanimbalkar9699-max/pramana-ai-radar --public --source=. --remote=origin --push
```

## Step 2: Enable GitHub Pages & Actions Write Permissions

1. Open your GitHub repository → **Settings → Actions → General → Workflow permissions**.
2. Select **Read and write permissions** and save (allows the daily/weekly workflows to commit updated `data/pramana.db` and `docs/`).
3. Open **Settings → Pages → Build and deployment → Source** and select **GitHub Actions**.

## Step 3: Configure Notification Secrets (Optional, Free)

In **Settings → Secrets and variables → Actions → New repository secret**, add whichever channels you want:

| Secret Name | Purpose | How to Get (Free) |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Daily & weekly Telegram alerts | Message `@BotFather` on Telegram → `/newbot` |
| `TELEGRAM_CHAT_ID` | Your Telegram chat destination | Message `@userinfobot` on Telegram |
| `SMTP_USER` | Sender Gmail address | Your Gmail address |
| `SMTP_PASS` | SMTP password | Google Account → Security → 2FA → App Passwords |
| `NOTIFY_EMAIL_TO` | Recipient email address | Your personal/student email |

`GITHUB_TOKEN` is injected automatically by GitHub Actions.

## Step 4: Verify Cloud Runs

1. Go to the **Actions** tab → **Pramana Daily AI Discovery** → **Run workflow**.
2. Go to **Pramana Weekly AI Intelligence Report** → **Run workflow**.
3. Your live cloud dashboard will be available 24/7 at:
   `https://adityanimbalkar9699-max.github.io/pramana-ai-radar/`
