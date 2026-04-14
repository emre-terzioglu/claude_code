# Morning Briefing — AI-Powered Daily Podcast

Every weekday at 07:15 (Europe/Berlin) this system:

1. Fetches the latest news (last 24 h) across three domains
2. Scores and ranks top articles
3. Runs two Gemini calls (strategic analysis → podcast script)
4. Converts the script to MP3 via Google TTS
5. Emails the result (text summary + MP3) to you

---

## File Structure

```
morning_briefing/
├── main.py               # Orchestration — run this
├── news_fetcher.py       # Google News RSS → article dicts
├── scorer.py             # Dedup, score (+3/+2/+2), rank top 5
├── gemini_analyzer.py    # Gemini: analysis + podcast script
├── tts_generator.py      # Google TTS → MP3 (auto-chunked)
├── email_sender.py       # Gmail SMTP, optional MP3 attachment
├── requirements.txt
├── .env.example          # Template — copy to .env
├── setup.sh              # One-time setup script
└── README.md
```

---

## Prerequisites

| What | Where to get it |
|------|----------------|
| Python 3.11+ | `python3 --version` to check |
| Gemini API key | [aistudio.google.com](https://aistudio.google.com/app/apikey) — free tier is enough |
| Google Cloud project with TTS API enabled | [console.cloud.google.com](https://console.cloud.google.com) |
| Service account JSON key (for TTS) | GCP → IAM → Service Accounts → Create key |
| Gmail account with 2FA | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |

---

## Step-by-Step Setup

### 1. Clone / navigate to the project

```bash
cd morning_briefing/
```

### 2. Run setup script

```bash
bash setup.sh
```

This creates `venv/` and installs all dependencies.

### 3. Configure API keys

```bash
cp .env.example .env
nano .env   # or your editor of choice
```

Fill in:

```dotenv
GEMINI_API_KEY=AIza...
GOOGLE_APPLICATION_CREDENTIALS=/home/youruser/keys/tts-service-account.json
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

**Gmail App Password** — do **not** use your main Google password:
1. Enable 2-Step Verification on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Click **Create** → select "Mail" → copy the 16-character password

**Google TTS service account**:
1. [console.cloud.google.com](https://console.cloud.google.com) → select/create a project
2. APIs & Services → Enable **Cloud Text-to-Speech API**
3. IAM → Service Accounts → Create → role: **Cloud Text-to-Speech User**
4. Keys tab → Add Key → JSON → download and save the file
5. Set `GOOGLE_APPLICATION_CREDENTIALS` to its absolute path

### 4. Test a manual run

```bash
source venv/bin/activate
python main.py
```

Watch `morning_briefing.log` for progress. A successful run takes ~30–60 seconds.

---

## Cron Job Setup

### Option A — System crontab (recommended for servers)

```bash
crontab -e
```

Add this line (replace paths with your actual paths):

```cron
TZ=Europe/Berlin
15 7 * * 1-5 /home/youruser/morning_briefing/venv/bin/python /home/youruser/morning_briefing/main.py >> /home/youruser/morning_briefing/cron.log 2>&1
```

- `TZ=Europe/Berlin` — sets timezone for this cron block
- `1-5` — Monday through Friday only
- `>> cron.log 2>&1` — cron captures all output (stdout + stderr)

Verify the cron is scheduled:

```bash
crontab -l
```

### Option B — systemd timer (more robust on modern Linux)

Create `/etc/systemd/system/morning-briefing.service`:

```ini
[Unit]
Description=Morning Briefing AI Pipeline
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=youruser
WorkingDirectory=/home/youruser/morning_briefing
EnvironmentFile=/home/youruser/morning_briefing/.env
ExecStart=/home/youruser/morning_briefing/venv/bin/python main.py
StandardOutput=append:/home/youruser/morning_briefing/morning_briefing.log
StandardError=append:/home/youruser/morning_briefing/morning_briefing.log
```

Create `/etc/systemd/system/morning-briefing.timer`:

```ini
[Unit]
Description=Run Morning Briefing at 07:15 Berlin time on weekdays

[Timer]
OnCalendar=Mon..Fri *-*-* 07:15:00 Europe/Berlin
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now morning-briefing.timer
systemctl list-timers morning-briefing.timer   # verify
```

---

## Voice Configuration

Edit `tts_generator.py` to change the TTS voice:

| Voice name | Gender | Style |
|------------|--------|-------|
| `en-US-Neural2-D` | Male | Default — clear, professional |
| `en-US-Neural2-F` | Female | Clear, professional |
| `en-US-Studio-O` | Male | Studio tier — highest quality |
| `en-US-Studio-Q` | Female | Studio tier — highest quality |

Studio voices consume more free-tier quota. Check pricing at [cloud.google.com/text-to-speech/pricing](https://cloud.google.com/text-to-speech/pricing).

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No articles fetched | Google News RSS can throttle. Wait 5 min and retry. Check internet connectivity. |
| Gemini 429 error | Free tier quota hit. The system retries 3× with backoff. Check [aistudio.google.com](https://aistudio.google.com). |
| TTS auth error | Verify `GOOGLE_APPLICATION_CREDENTIALS` path. Run `gcloud auth application-default login` as a fallback. |
| Gmail auth error | Ensure App Password (not main password). Confirm 2FA is on. |
| Empty MP3 sent | TTS chunking issue — check `morning_briefing.log` for chunk errors. |
| Cron not firing | Confirm `TZ=Europe/Berlin` is in crontab, not just a comment. |

Log file: `morning_briefing/morning_briefing.log`
