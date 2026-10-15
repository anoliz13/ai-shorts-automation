# AI Shorts Automation

Fully automated pipeline that monitors YouTube channels, generates viral-worthy shorts with AI, and uploads them to TikTok & YouTube Shorts — all controlled through a Web UI.

## Features

- Monitor multiple YouTube channels for new videos
- Auto-detect unprocessed videos
- Generate viral-worthy shorts using AI (LLM highlight detection + Whisper transcription + auto-crop)
- Auto-upload to TikTok & YouTube Shorts
- Anti-spam protection: rate limiting, staggered uploads, daily limits
- Web UI dashboard for monitoring & control
- Daily automatic check (configurable schedule)

## Prerequisites

- Python 3.10+
- ffmpeg on PATH
- API keys:
  - `MUAPI_API_KEY` - for video processing (or use local mode with `OPENAI_API_KEY`)
  - `OPENAI_API_KEY` or `GEMINI_API_KEY` - for LLM highlight detection
- YouTube OAuth credentials (`data/youtube_credentials.json`)
- TikTok account (login via browser on first run)

## Quick Start

```bash
# Clone
git clone https://github.com/your-username/ai-shorts-automation.git
cd ai-shorts-automation

# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python backend/app.py
# Open http://localhost:8000
```

## Web UI Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Overview stats, upload usage, system status, "Run Now" button |
| **Channels** | Add/remove/monitor YouTube channels |
| **Videos** | View detected videos and their processing status |
| **Shorts** | View generated shorts with scores, hooks, manual upload |
| **Uploads** | Upload history and daily usage per platform |
| **Settings** | Schedule, anti-spam limits, generation mode |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MUAPI_API_KEY` | — | MuAPI key for download/transcribe/clip |
| `OPENAI_API_KEY` | — | OpenAI API key for LLM |
| `GEMINI_API_KEY` | — | Gemini API key (alternative) |
| `LLM_PROVIDER` | `openai` | `openai` or `gemini` |
| `CHECK_HOUR` | `20` | Daily check hour (0-23) |
| `CHECK_MINUTE` | `0` | Daily check minute (0-59) |
| `MAX_SHORTS_PER_VIDEO` | `5` | Max shorts generated per video |
| `MAX_UPLOADS_PER_DAY_TIKTOK` | `5` | Daily TikTok upload limit |
| `MAX_UPLOADS_PER_DAY_YOUTUBE` | `5` | Daily YouTube upload limit |
| `MIN_GAP_MINUTES` | `30` | Minimum gap between uploads |
| `SHORTS_MODE` | `api` | `api` (MuAPI) or `local` (offline) |

## Anti-Spam Protection

- Maximum uploads per platform per day (configurable)
- Minimum gap between uploads (configurable)
- Daily limit enforcement with automatic deferral
- Duplicate detection prevents re-uploading

## Project Structure

```
ai-shorts-automation/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── config.py              # Settings management
│   ├── database.py            # SQLite setup & models
│   ├── scheduler.py           # APScheduler jobs
│   ├── api/                   # REST API endpoints
│   └── services/              # Business logic
│       ├── monitor.py         # YouTube channel monitoring
│       ├── generator.py       # Short generation
│       ├── uploader.py        # Upload pipeline
│       ├── anti_spam.py       # Rate limiting
│       ├── tiktok_uploader.py # Playwright TikTok uploader
│       └── youtube_uploader.py# YouTube API uploader
├── frontend/                  # Web UI
│   ├── index.html             # Dashboard
│   ├── channels.html
│   ├── videos.html
│   ├── shorts.html
│   ├── uploads.html
│   ├── settings.html
│   ├── css/style.css
│   └── js/app.js
├── shorts_generator/          # Short generation pipeline
├── data/                      # SQLite database (created on first run)
├── logs/                      # Application logs
├── docs/
│   └── superpowers/
│       ├── specs/             # Design document
│       └── plans/             # Implementation plan
├── requirements.txt
├── .env.example
└── README.md
```

## Troubleshooting

**TikTok login required:** First run opens a browser. Log in and the session is saved for future runs.

**YouTube quota exceeded:** YouTube Data API has daily quota. Monitor usage in Google Cloud Console.

**yt-dlp errors:** Update yt-dlp: `pip install -U yt-dlp`. YouTube frequently changes their API.

**ffmpeg not found:** Install ffmpeg and ensure it's on your PATH.

## License

MIT
