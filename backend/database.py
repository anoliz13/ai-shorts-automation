"""SQLite database setup and models."""

import os
import aiosqlite
from contextlib import asynccontextmanager
from backend.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_url TEXT UNIQUE NOT NULL,
    channel_name TEXT,
    check_enabled INTEGER DEFAULT 1,
    last_checked TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER REFERENCES channels(id),
    video_url TEXT UNIQUE NOT NULL,
    video_title TEXT,
    video_id TEXT UNIQUE NOT NULL,
    duration_seconds INTEGER,
    published_at TIMESTAMP,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shorts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER REFERENCES videos(id),
    title TEXT,
    start_time REAL,
    end_time REAL,
    score INTEGER,
    hook_sentence TEXT,
    virality_reason TEXT,
    file_path TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short_id INTEGER REFERENCES shorts(id),
    platform TEXT NOT NULL,
    platform_video_id TEXT,
    status TEXT DEFAULT 'pending',
    uploaded_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    max_uploads_per_day INTEGER DEFAULT 5,
    min_gap_minutes INTEGER DEFAULT 30,
    current_count INTEGER DEFAULT 0,
    date DATE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, date)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT
);
"""


async def init_db():
    """Initialize the database with all required tables."""
    db_dir = os.path.dirname(settings.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        await db.commit()


@asynccontextmanager
async def get_db():
    """Async context manager for database connections."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        yield db
