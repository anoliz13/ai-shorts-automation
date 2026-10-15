# AI Shorts Automation - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated pipeline that monitors YouTube channels, generates viral shorts with AI, and uploads them to TikTok & YouTube Shorts — controlled through a Web UI.

**Architecture:** FastAPI backend serves both REST API and static frontend. APScheduler runs daily channel checks. SQLite tracks all state (channels, videos, shorts, uploads). Three service modules handle monitoring (yt-dlp), generation (AI highlight detection + auto-crop), and uploading (Playwright for TikTok, Google API for YouTube).

**Tech Stack:** Python 3.10+, FastAPI, SQLite (aiosqlite), APScheduler, yt-dlp, Playwright, google-api-python-client, ffmpeg

**Spec:** `docs/superpowers/specs/2026-10-15-youtube-shorts-automation-design.md`

---

## Global Constraints

- Python 3.10+ required
- ffmpeg must be on PATH
- SQLite WAL mode enabled on all connections
- All API keys loaded from `.env` file only — never hardcoded
- `.env` and `data/` directory are in `.gitignore`
- Max 5 uploads per platform per day (default, configurable)
- Min 30 minutes gap between uploads (default, configurable)
- Daily check defaults to 20:00 local time (configurable)
- TikTok upload via Playwright browser automation
- YouTube upload via YouTube Data API v3
- No authentication on Web UI (local use only)

## Review Focus

- **Channel with no new videos:** monitor job runs, finds nothing new → no shorts generated, no uploads, no errors, last_checked updates correctly
- **Upload daily limit reached:** shorts remain status='pending', deferred to next day, no error thrown
- **yt-dlp fails on private/deleted video:** video marked status='failed' with error message, pipeline continues with next video
- **Playwright TikTok session expired:** uploader catches auth error, sets upload status='failed', logs actionable message for user
- **Duplicate video detected:** second run of same channel does not re-insert video, does not re-generate shorts, does not re-upload

---

## Task 1: Project Scaffold & Database

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `backend/database.py`
- Create: `backend/config.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Produces:
  - `get_db() -> aiosqlite.Connection` — async context manager, WAL mode enabled
  - `init_db() -> None` — creates all tables if not exist
  - `settings: Settings` — pydantic-settings object with all env vars

- [x] **Step 1: Create project root and requirements.txt** ✅
- [x] **Step 2: Create .gitignore** ✅
- [x] **Step 3: Create .env.example** ✅
- [x] **Step 4: Implement `backend/config.py`** ✅
- [x] **Step 5: Implement `backend/database.py`** ✅

---

## Task 2: FastAPI Backend Skeleton + Web UI Shell

**Files:**
- Create: `backend/app.py`
- Create: `backend/api/__init__.py`
- Create: `backend/api/channels.py`
- Create: `backend/api/videos.py`
- Create: `backend/api/shorts.py`
- Create: `backend/api/uploads.py`
- Create: `backend/api/settings_api.py`
- Create: `frontend/index.html`
- Create: `frontend/channels.html`
- Create: `frontend/videos.html`
- Create: `frontend/shorts.html`
- Create: `frontend/uploads.html`
- Create: `frontend/settings.html`
- Create: `frontend/css/style.css`
- Create: `frontend/js/app.js`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `get_db()`, `init_db()`, `settings` from Task 1
- Produces:
  - `GET /api/channels` → `list[ChannelOut]`
  - `POST /api/channels` body `ChannelIn` → `ChannelOut`
  - `DELETE /api/channels/{id}` → `{"ok": true}`
  - `PATCH /api/channels/{id}` body `{"check_enabled": bool}` → `ChannelOut`
  - `GET /api/videos` → `list[VideoOut]`
  - `GET /api/shorts` → `list[ShortOut]`
- [x] **Step 1: Implement all API routers** ✅
- [x] **Step 2: Implement `backend/app.py`** ✅
- [x] **Step 3: Build Web UI HTML pages** ✅

---

## Task 3: YouTube Channel Monitor + Scheduler

**Files:**
- Create: `backend/services/monitor.py`
- Create: `backend/scheduler.py`
- Test: `tests/test_monitor.py`

**Interfaces:**
- Consumes: `get_db()`, `settings` from Task 1
- Produces:
  - `scan_channel(channel_id: int, channel_url: str) -> dict`
  - `scan_all_channels() -> dict`
  - `start_scheduler() -> None`
  - `POST /api/channels/check-now` → result dict

- [x] **Step 1: Implement `backend/services/monitor.py`** ✅
- [x] **Step 2: Implement `backend/scheduler.py`** ✅

---

## Task 4: Short Generator Service

**Files:**
- Create: `shorts_generator/__init__.py`
- Create: `backend/services/generator.py`
- Test: `tests/test_generator.py`

**Interfaces:**
- Consumes: `get_db()`, `settings` from Task 1
- Produces:
  - `generate_shorts(url, num_clips, mode, aspect_ratio) -> dict`
  - `process_pending_videos() -> dict`

- [x] **Step 1: Implement `shorts_generator/__init__.py`** ✅
- [x] **Step 2: Implement `backend/services/generator.py`** ✅

---

## Task 5: Upload Pipeline (TikTok + YouTube Shorts)

**Files:**
- Create: `backend/services/uploader.py`
- Create: `backend/services/anti_spam.py`
- Create: `backend/services/tiktok_uploader.py`
- Create: `backend/services/youtube_uploader.py`
- Test: `tests/test_uploader.py`
- Test: `tests/test_anti_spam.py`

**Interfaces:**
- Consumes: `get_db()`, `settings` from Task 1
- Produces:
  - `upload_to_tiktok(short_id, file_path, title) -> dict`
  - `upload_to_youtube(short_id, file_path, title, description) -> dict`
  - `process_pending_uploads() -> dict`
  - `check_daily_limit(platform) -> bool`
  - `record_upload_attempt(platform) -> None`

- [x] **Step 1: Implement `backend/services/anti_spam.py`** ✅
- [x] **Step 2: Implement `backend/services/tiktok_uploader.py`** ✅
- [x] **Step 3: Implement `backend/services/youtube_uploader.py`** ✅
- [x] **Step 4: Implement `backend/services/uploader.py`** ✅

---

## Task 6: Wire Full Pipeline + Polish Web UI

**Files:**
- Modify: `backend/scheduler.py`
- Modify: `backend/app.py` — add `POST /api/pipeline/run-now`
- Modify: all frontend pages
- Create: `backend/services/logger.py`
- Test: `tests/test_pipeline.py`

- [x] **Step 1: Implement structured logging** ✅
- [x] **Step 2: Add pipeline run-now endpoint** ✅
- [x] **Step 3: Polish Web UI pages** ✅

---

## Task 7: README, .env setup, GitHub Push

**Files:**
- Create: `README.md`
- Create: `setup.sh` / `setup.bat`
- Create: `docs/superpowers/plans/plan.md`

- [x] **Step 1: Write README.md** ✅
- [x] **Step 2: Write setup scripts** ✅
- [x] **Step 3: Git init + push to GitHub** ✅

---

## Clone on Another Machine

After push, on any other machine:

```bash
git clone https://github.com/<your-username>/ai-shorts-automation.git
cd ai-shorts-automation
chmod +x setup.sh && ./setup.sh   # Linux/Mac
# or: setup.bat                   # Windows

# Fill in your API keys:
nano .env

# Run:
python backend/app.py
# Open http://localhost:8000
```
