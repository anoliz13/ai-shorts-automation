"""Dashboard endpoint."""

from fastapi import APIRouter
from backend.database import get_db

router = APIRouter()


@router.get("/dashboard")
async def dashboard_stats():
    async with get_db() as db:
        # Count channels
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM channels")
        total_channels = (await cursor.fetchone())["cnt"]

        # Count videos
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM videos")
        total_videos = (await cursor.fetchone())["cnt"]

        # Count shorts
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM shorts")
        total_shorts = (await cursor.fetchone())["cnt"]

        # Count uploads today
        from datetime import date
        today = date.today().isoformat()
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM uploads WHERE date(created_at)=?",
            (today,)
        )
        uploads_today = (await cursor.fetchone())["cnt"]

        # Last check
        cursor = await db.execute(
            "SELECT MAX(last_checked) as last FROM channels WHERE last_checked IS NOT NULL"
        )
        row = await cursor.fetchone()
        last_check = row["last"] if row else None

    return {
        "total_channels": total_channels,
        "total_videos": total_videos,
        "total_shorts": total_shorts,
        "uploads_today": uploads_today,
        "last_check": last_check,
    }
