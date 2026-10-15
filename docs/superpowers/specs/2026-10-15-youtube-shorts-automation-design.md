# YouTube Shorts Automation Pipeline - Design Document

**Date:** 2026-10-15
**Author:** Predator (with AI assistant)
**Status:** Draft - Awaiting Review

---

## 1. Intent & Why

### What It Is
A fully automated pipeline that monitors YouTube channels for new videos, generates viral-worthy short clips (9:16 vertical), and uploads them to TikTok & YouTube Shorts — all controlled through a Web UI.

### Why This Exists
- **Manual repurposing is slow** - creators spend hours clipping long videos into shorts
- **Existing tools (Opus Clip, Klap) are expensive** - $20-300/month
- **No open-source alternative offers end-to-end automation** - generate + upload in one pipeline
- **Multi-platform posting is tedious** - posting the same short to TikTok + YouTube manually

### Success Looks Like
- User adds YouTube channel URLs → system does everything else
- New video detected at night → shorts generated & uploaded by morning
- Zero manual intervention required
- User just checks Web UI dashboard to see results

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals (What We're Building)
- ✅ Monitor multiple YouTube channels for new videos
- ✅ Auto-detect unprocessed videos (track what's already been done)
- ✅ Generate viral-worthy shorts using AI-Youtube-Shorts-Generator
- ✅ Auto-upload to TikTok & YouTube Shorts
- ✅ Web UI dashboard for monitoring & control
- ✅ Anti-spam: rate limiting, staggered uploads, daily limits
- ✅ Daily check schedule (default: night time)
- ✅ Full automation: zero manual steps after initial setup
- ✅ Git-pushed: continue work from any machine

### Non-Goals (What We're NOT Building)
- ❌ Real-time monitoring (checking every 15 min) - too resource heavy
- ❌ Monetization/billing features
- ❌ Multi-user support (single user only)
- ❌ Mobile app (Web UI is responsive enough)
- ❌ Video editing beyond auto-crop (no custom overlays, branding, etc.)
- ❌ Instagram Reels, Facebook, Twitter (future expansion)

### Anti-Goals (What Would Make This a Failure)
- ❌ Getting accounts banned for spam
- ❌ Uploading the same content twice
- ❌ Generating low-quality, non-viral shorts
- ❌ Complex setup that requires dev expertise
- ❌ Unreliable scheduling that misses videos
- ❌ Web UI that crashes or is confusing to use

---

## 3. Constraints

### Technical Constraints
- **Python 3.10+** (already required by AI-Youtube-Shorts-Generator)
- **ffmpeg** on PATH (for local mode & processing)
- **API Keys needed:**
  - `MUAPI_API_KEY` - for video download, transcription, highlight detection
  - TikTok credentials (for upload) - via browser automation
  - Google OAuth (for YouTube upload) - via YouTube Data API
- **No cloud hosting** - runs locally on user's machine
- **SQLite** - local database, no external DB needed

### Platform Constraints
- **TikTok upload:** Via browser automation (Playwright/Selenium) - no official API for personal accounts
- **YouTube upload:** Via YouTube Data API v3 (official API, reliable)
- **Rate limits:** TikTok ~5-10 uploads/day for new accounts, YouTube ~100 videos/day (but we'll stay well below)

### Time Constraints
- Daily check: Once per night (configurable hour)
- Upload window: Staggered over several hours to avoid spam detection

---

## 4. Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB UI (FastAPI + HTML/JS)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │  Channel Mgmt│  │  Settings    │      │
│  │  - Status    │  │  - Add/Remove│  │  - Schedule  │      │
│  │  - History   │  │  - List      │  │  - Limits    │      │
│  │  - Uploads   │  │              │  │  - API Keys  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   SCHEDULER (APScheduler)                   │
│  - Daily channel check (configurable hour)                  │
│  - Trigger: scan_channels_job                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   ORCHESTRATOR (Python)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Monitor   │  │  Generator  │  │   Uploader  │        │
│  │  - YouTube  │→ │  - AI Shorts│→ │  - TikTok   │        │
│  │  - RSS/yt-dlp│ │  - Highlight │  │  - YouTube  │        │
│  │  - New?     │  │  - Crop     │  │  - Stagger  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                │                │                  │
│         ▼                ▼                ▼                  │
│  ┌──────────────────────────────────────────────┐          │
│  │              SQLITE DATABASE                   │          │
│  │  - channels  - videos  - shorts  - uploads    │          │
│  │  - schedules  - settings  - daily_limits     │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema (SQLite)

```sql
-- Channels being monitored
CREATE TABLE channels (
    id INTEGER PRIMARY KEY,
    channel_url TEXT UNIQUE NOT NULL,
    channel_name TEXT,
    platform TEXT DEFAULT 'youtube',
    check_enabled INTEGER DEFAULT 1,
    last_checked TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Videos detected from channels
CREATE TABLE videos (
    id INTEGER PRIMARY KEY,
    channel_id INTEGER REFERENCES channels(id),
    video_url TEXT UNIQUE NOT NULL,
    video_title TEXT,
    video_id TEXT UNIQUE NOT NULL,  -- YouTube video ID
    duration_seconds INTEGER,
    published_at TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- pending/processing/done/skipped/failed
    is_new INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Generated shorts
CREATE TABLE shorts (
    id INTEGER PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    title TEXT,
    start_time REAL,
    end_time REAL,
    score INTEGER,  -- virality score 0-100
    hook_sentence TEXT,
    virality_reason TEXT,
    file_path TEXT,  -- local path or URL
    status TEXT DEFAULT 'pending',  -- pending/uploaded/failed/skipped
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Upload tracking
CREATE TABLE uploads (
    id INTEGER PRIMARY KEY,
    short_id INTEGER REFERENCES shorts(id),
    platform TEXT NOT NULL,  -- tiktok/youtube
    platform_video_id TEXT,  -- ID returned by platform
    status TEXT DEFAULT 'pending',  -- pending/uploading/done/failed
    uploaded_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily upload limits (anti-spam)
CREATE TABLE daily_limits (
    id INTEGER PRIMARY KEY,
    platform TEXT NOT NULL,
    max_uploads_per_day INTEGER DEFAULT 5,
    min_gap_minutes INTEGER DEFAULT 30,  -- gap between uploads
    current_count INTEGER DEFAULT 0,
    date DATE DEFAULT CURRENT_TIMESTAMP
);

-- Settings
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT
);
```

---

## 5. Detailed Workflow

### 5.1 Channel Monitoring (Daily Check)

```
1. Read all enabled channels from DB
2. For each channel:
   a. Use yt-dlp to fetch recent videos (last 24h)
   b. For each video found:
      - Check if video_id already in videos table
      - If new → insert with status='pending'
      - If exists → skip
3. Update channel.last_checked timestamp
```

**Schedule:** Default 20:00 (8 PM) local time, configurable via Web UI

### 5.2 Short Generation Pipeline

```
For each video with status='pending':
1. Set status='processing'
2. Call AI-Youtube-Shorts-Generator:
   a. Download video (via MuAPI)
   b. Transcribe (Whisper)
   c. LLM highlight detection
   d. Auto-crop vertical 9:16
   e. Return: list of shorts with scores, hooks, reasons
3. Anti-spam filter:
   - Keep only top 5 shorts per video (configurable)
   - Sort by viral score descending
   - Remove duplicates
4. Insert shorts into DB with status='pending'
5. Set video status='done'
```

### 5.3 Upload Pipeline (Anti-Spam Safe)

```
For each short with status='pending':
1. Check daily limit for platform:
   - If current_count >= max_uploads_per_day → skip (defer to tomorrow)
2. Check gap since last upload:
   - If < min_gap_minutes → wait
3. Upload to TikTok first:
   a. Browser automation (Playwright)
   b. Navigate to TikTok Creator Center
   c. Upload video file
   d. Add title, description, hashtags
   e. Publish
4. Record upload in DB, increment daily_count
5. Wait min_gap_minutes
6. Upload to YouTube Shorts:
   a. YouTube Data API v3
   b. Upload video file
   c. Add title, description, tags
   d. Publish
7. Record upload, increment daily_count
8. Set short status='uploaded'
```

### 5.4 Anti-Spam Safeguards

| Safeguard | Default Value | Description |
|-----------|---------------|-------------|
| Max shorts per video | 5 | Don't generate too many from one source |
| Max uploads per platform per day | 5 | Stay well below platform limits |
| Min gap between uploads | 30 minutes | Avoid burst uploads |
| New account warmup period | 7 days | Start with 2/day, ramp up |
| Duplicate detection | video_id + short_title | Never upload same content twice |

---

## 6. Web UI Design

### Pages

#### Dashboard (Home)
- Overview stats: channels monitored, videos processed, shorts generated, uploads today
- Recent activity feed
- Quick actions: "Run Check Now", "View Pending Uploads"
- System status: scheduler running, last check, next check

#### Channels
- List of monitored channels (name, URL, last checked, video count)
- Add new channel form
- Toggle channel on/off
- Delete channel

#### Videos
- List of detected videos (title, channel, date detected, status)
- Filter by status: pending/processing/done/failed
- View shorts generated per video

#### Shorts
- List of generated shorts (title, score, video source, status)
- Preview/download shorts
- Manual re-upload button

#### Uploads
- Upload history (platform, status, timestamp, error if failed)
- Daily usage per platform
- Progress indicator

#### Settings
- Schedule configuration (hour, minute, enabled)
- Anti-spam settings (max uploads, gaps, limits)
- API key management (MuAPI, TikTok, YouTube)
- Notification settings (email/webhook on failure)

### UI Style
- Clean, dark mode default
- Responsive (works on mobile)
- Card-based layout
- Status badges (color-coded: green=done, yellow=pending, red=failed)

---

## 7. Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Backend** | FastAPI | Fast, async, easy API + serve static files |
| **Frontend** | HTML + CSS + vanilla JS | No build step, lightweight, fast to load |
| **Database** | SQLite | Zero config, local, reliable |
| **Scheduler** | APScheduler | Python-native, cron-like, persistent |
| **YouTube Detection** | yt-dlp | Reliable, maintained, supports many sites |
| **Short Generation** | AI-Youtube-Shorts-Generator (forked) | Proven pipeline, already built |
| **TikTok Upload** | Playwright | Reliable browser automation |
| **YouTube Upload** | Google API Python Client | Official, stable |
| **Video Processing** | ffmpeg | Industry standard |

---

## 8. Integration Strategy

### Forked Dependencies

1. **AI-Youtube-Shorts-Generator** → Fork to our repo
   - Modify: expose `generate_shorts()` as importable function
   - Modify: add database integration (insert shorts into DB)
   - Keep: core pipeline logic unchanged

2. **social-auto-upload** → Fork to our repo (optional)
   - Could use as reference for upload logic
   - Or implement our own simpler uploader

### Project Structure

```
ai-shorts-automation/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── config.py              # Settings management
│   ├── database.py            # SQLite setup & models
│   ├── scheduler.py           # APScheduler jobs
│   ├── api/
│   │   ├── channels.py        # Channel CRUD endpoints
│   │   ├── videos.py          # Video endpoints
│   │   ├── shorts.py          # Shorts endpoints
│   │   ├── uploads.py         # Upload endpoints
│   │   └── settings.py        # Settings endpoints
│   └── services/
│       ├── monitor.py         # YouTube channel monitoring
│       ├── generator.py       # Short generation orchestration
│       ├── uploader.py        # Multi-platform upload
│       └── anti_spam.py       # Rate limiting & safety
├── frontend/
│   ├── index.html             # Dashboard
│   ├── channels.html
│   ├── videos.html
│   ├── shorts.html
│   ├── uploads.html
│   ├── settings.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── shorts_generator/          # Forked from AI-Youtube-Shorts-Generator
│   ├── __init__.py
│   ├── config.py
│   ├── downloader.py
│   ├── transcriber.py
│   ├── highlights.py
│   ├── clipper.py
│   └── pipeline.py
├── data/
│   └── shorts_automation.db   # SQLite database
├── docs/
│   └── superpowers/specs/
│       └── 2026-10-15-youtube-shorts-automation-design.md
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

---

## 9. Security Considerations

- **API Keys:** Stored in `.env` file, never committed to git (in `.gitignore`)
- **OAuth tokens:** YouTube OAuth tokens stored encrypted in DB
- **TikTok session:** Browser cookies stored locally, refreshed on expiry
- **Database:** SQLite with WAL mode for concurrent reads/writes
- **Web UI:** No authentication (local use only) — note: don't expose to public network

---

## 10. Deployment

### Local Development
```bash
# Clone
git clone https://github.com/<user>/ai-shorts-automation.git
cd ai-shorts-automation

# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python backend/app.py
# Open http://localhost:8000
```

### Production (Same Machine)
```bash
# Run as background service
nohup python backend/app.py > logs/app.log 2>&1 &

# Or use systemd (Linux) / Task Scheduler (Windows)
```

### Git Workflow
```bash
# Push to GitHub
git remote add origin https://github.com/<user>/ai-shorts-automation.git
git push -u origin main

# On another machine
git clone https://github.com/<user>/ai-shorts-automation.git
# Same setup steps
```

---

## 11. Open Questions for Builder

1. **TikTok upload reliability:** Browser automation can be fragile. Should we also support manual fallback (user uploads manually from Web UI)?

2. **YouTube API quota:** YouTube Data API has daily quota (10,000 units). Each upload costs ~1,600 units. With 5 uploads/day = 8,000 units. Need to monitor quota usage.

3. **Error recovery:** What happens if upload fails midway? Should we retry? How many times?

4. **Notification:** Should we send notifications (email, Telegram, Discord webhook) when uploads complete or fail?

5. **Multi-user:** Is single-user assumption correct, or might this be used for clients/agency?

---

## 12. Build Plan

### Phase 1: Core Infrastructure
- [ ] Project setup & structure
- [ ] Database models & migrations
- [ ] FastAPI skeleton with all endpoints
- [ ] Web UI skeleton (all pages)

### Phase 2: YouTube Monitoring
- [ ] Channel CRUD API
- [ ] yt-dlp integration for video detection
- [ ] New video detection logic
- [ ] Scheduler integration

### Phase 3: Short Generation
- [ ] Fork AI-Youtube-Shorts-Generator
- [ ] Integrate `generate_shorts()` function
- [ ] Database integration for shorts
- [ ] Anti-spam filtering (top N per video)

### Phase 4: Upload Pipeline
- [ ] YouTube Data API integration
- [ ] TikTok browser automation (Playwright)
- [ ] Upload queue with rate limiting
- [ ] Daily limits & gap enforcement
- [ ] Upload status tracking

### Phase 5: Polish
- [ ] Web UI refinement
- [ ] Error handling & recovery
- [ ] Logging
- [ ] Documentation
- [ ] Git push

---

**Status:** Ready for review. After approval, invoke writing-plans skill to create detailed implementation plan.
