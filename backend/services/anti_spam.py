"""Anti-spam rate limiting for uploads."""

from datetime import date, datetime
from backend.database import get_db
from backend.config import settings


async def check_daily_limit(platform: str) -> bool:
    """Return True if under the daily upload limit for this platform."""
    today = date.today().isoformat()
    max_key = f"max_uploads_per_day_{platform}"
    max_limit = getattr(settings, max_key, 5)

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT current_count FROM daily_limits WHERE platform=? AND date=?",
            (platform, today)
        )
        row = await cursor.fetchone()
        current = row["current_count"] if row else 0

    return current < max_limit


async def record_upload_attempt(platform: str) -> None:
    """Increment today's upload counter for this platform."""
    today = date.today().isoformat()
    max_key = f"max_uploads_per_day_{platform}"
    max_limit = getattr(settings, max_key, 5)

    async with get_db() as db:
        await db.execute(
            """INSERT INTO daily_limits (platform, max_uploads_per_day, current_count, date)
               VALUES (?, ?, 1, ?)
               ON CONFLICT(platform, date) DO UPDATE SET current_count = current_count + 1""",
            (platform, max_limit, today)
        )
        await db.commit()


async def get_last_upload_time(platform: str):
    """Return datetime of the most recent successful upload, or None."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT uploaded_at FROM uploads
               WHERE platform=? AND status='done'
               ORDER BY uploaded_at DESC LIMIT 1""",
            (platform,)
        )
        row = await cursor.fetchone()
        if row and row["uploaded_at"]:
            return datetime.fromisoformat(row["uploaded_at"])
    return None
