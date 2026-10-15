"""Upload endpoints."""

from fastapi import APIRouter
from backend.database import get_db

router = APIRouter()


@router.get("/uploads")
async def list_uploads():
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT u.*, s.title as short_title, s.score
            FROM uploads u
            JOIN shorts s ON u.short_id = s.id
            ORDER BY u.created_at DESC
        """)
        rows = await cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "short_id": row["short_id"],
            "short_title": row["short_title"],
            "platform": row["platform"],
            "platform_video_id": row["platform_video_id"],
            "status": row["status"],
            "uploaded_at": row["uploaded_at"],
            "error_message": row["error_message"],
            "created_at": row["created_at"],
        })
    return result


@router.get("/uploads/daily-usage")
async def daily_usage():
    from datetime import date
    today = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT platform, current_count, max_uploads_per_day FROM daily_limits WHERE date=?",
            (today,)
        )
        rows = await cursor.fetchall()
    result = {}
    for row in rows:
        result[row["platform"]] = {
            "used": row["current_count"],
            "limit": row["max_uploads_per_day"],
            "remaining": max(0, row["max_uploads_per_day"] - row["current_count"]),
        }
    return result
