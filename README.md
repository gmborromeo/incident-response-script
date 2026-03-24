# Automated Incident Response System

A lightweight incident detection and auto-remediation tool that mirrors real-world SRE on-call workflows. Monitors system health every 60 seconds, logs structured incidents, auto-restarts failed services, and fires Slack alerts — all from a single Python daemon scheduled via cron.

**Stack:** Python · Bash · systemd · cron · Slack API · jq

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Linux / WSL                       │
│                                                     │
│   cron (every 60s)                                  │
│        │                                            │
│        ▼                                            │
│   monitor.py ──── threshold breach? ────────────►  │
│        │               │              incident.log  │
│        │               │                            │
│        │          service down?                     │
│        │               │                            │
│        │               ├──► restart.sh              │
│        │               │    (exponential backoff)   │
│        │               │                            │
│        │               └──► Slack webhook           │
│        │                    (warning / critical)    │
│        │                                            │
│   healthcheck.sh                                    │
│   (exit 0 = healthy, exit 1 = degraded)             │
└─────────────────────────────────────────────────────┘
```

---

## Features

- Polls CPU, memory, disk, and systemd service status every 60 seconds via cron
- Writes structured JSON log entries per incident for machine-readable querying with `jq`
- Auto-restarts failed systemd services with exponential backoff (5s → 10s → 20s)
- Sends Slack notifications with warning/critical severity labels
- `healthcheck.sh` wrapper exits 0/1 for integration with external monitoring tools
- Slack webhook URL stored securely as a GitHub Secret — never hardcoded

---

## Alert Thresholds

| Check | Warning | Critical |
|---|---|---|
| CPU usage | > 80% | > 95% |
| Memory usage | > 85% | > 95% |
| Disk usage | > 90% | > 98% |
| Systemd service | — | not active |

---

## Screenshots

**monitor.py — warning alert firing in terminal**

<img width="550" height="186" alt="image" src="https://github.com/user-attachments/assets/c4df9d77-8141-41df-a1ed-a40a9cfc36e8" />

**incident.log — structured JSON entries**

<img width="1112" height="284" alt="image" src="https://github.com/user-attachments/assets/27575209-b045-4fdb-8872-a51cd1474b9c" />

**Slack — alert notification**

<img width="529" height="369" alt="image" src="https://github.com/user-attachments/assets/f32dce4b-ca3c-45d4-a47c-6661ffb83a3e" />

**healthcheck.sh — system status output**

<img width="462" height="105" alt="image" src="https://github.com/user-attachments/assets/19ef8958-b504-4ab8-aad5-949d5b9c6697" />

---

## Prerequisites

- Python 3.10+
- pip packages: `psutil`, `requests`, `python-dotenv`
- A Slack workspace with an Incoming Webhook URL
  - Create one at: https://api.slack.com/apps → Incoming Webhooks

---

## Local Setup (WSL / Linux)

### 1. Clone the repository

```bash
git clone https://github.com/gmborromeo/incident-response-script
cd incident-response-script
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install psutil requests python-dotenv
```

> Always activate the venv before running: `source venv/bin/activate`
> To exit the venv: `deactivate`

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your Slack webhook URL:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

> `.env` is listed in `.gitignore` and will never be committed to git.

### 4. Run manually to verify

```bash
python3 monitor.py
```

Check the log was written:

```bash
cat logs/incident.log | jq .
```

### 5. Make scripts executable

```bash
chmod +x restart.sh healthcheck.sh
```

### 6. Schedule via cron (runs every 60 seconds)

```bash
crontab -e
```

Add this line (replace with your actual username):

```
* * * * * cd /home/YOUR_USER/incident-response-script && venv/bin/python3 monitor.py >> logs/cron.log 2>&1
```

### 7. Access the services

| Script | Purpose |
|---|---|
| `monitor.py` | Main daemon — polls metrics and fires alerts |
| `restart.sh <service>` | Auto-restart a systemd service with backoff |
| `healthcheck.sh` | Quick health summary, exit 0/1 |

---

## GitHub Actions — CI/CD with Secrets

The Slack webhook URL is never stored in the repository. It is injected at runtime via GitHub Actions.

### Adding the secret to GitHub

1. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** and add:

| Secret Name | Value |
|---|---|
| `SLACK_WEBHOOK_URL` | Your full Slack webhook URL |

### How it works

`.env` in the repo contains a placeholder:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/REPLACE/WITH/YOUR_WEBHOOK
```

The GitHub Actions workflow injects the real value at deploy time:

```yaml
# .github/workflows/deploy.yml
- name: Create .env from GitHub Secrets
  run: echo "SLACK_WEBHOOK_URL=${{ secrets.SLACK_WEBHOOK_URL }}" > .env
```

---

## Project Files

```
incident-response-script/
├── monitor.py              # Main Python daemon — polls metrics, logs, alerts
├── restart.sh              # Bash auto-restart with exponential backoff
├── healthcheck.sh          # Bash health summary wrapper (exit 0/1)
├── .env.example            # Template — copy to .env, never commit .env
├── .gitignore
└── README.md
```

---

## .env.example

```env
# Copy this file to .env and fill in your own values
# Never commit .env to git

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/REPLACE/WITH/YOUR_WEBHOOK
```

---

## .gitignore

```
.env
logs/
venv/
__pycache__/
*.pyc
```

---

## Querying Incident Logs with jq

Since logs are structured JSON, you can query them precisely:

```bash
# Pretty print all entries
cat logs/incident.log | jq .

# Show only critical alerts
cat logs/incident.log | jq 'select(.level == "critical")'

# Show only CPU checks
cat logs/incident.log | jq 'select(.check == "cpu")'

# Show timestamp and message only
cat logs/incident.log | jq '{timestamp, level, message}'

# Count incidents by level
cat logs/incident.log | jq '.level' | sort | uniq -c
```

---

## Testing Alerts

Trigger a CPU spike to verify the full alerting pipeline end-to-end:

```bash
sudo apt install -y stress
stress --cpu 2 --timeout 60s &

# Run monitor immediately to fire the alert
source venv/bin/activate
python3 monitor.py

# Slack notification should arrive within seconds
# Check the log
cat logs/incident.log | jq .

killall stress
```

Test the auto-restart script:

```bash
# Test with a real service
./restart.sh docker

# Test the failure path
./restart.sh fake-service-name
cat logs/incident.log | jq 'select(.check == "restart")'
```
