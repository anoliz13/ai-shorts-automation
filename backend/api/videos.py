"""Video endpoints."""

from fastapi import APIRouter, Query
from typing import Optional
from backend.database import get_db

router = APIRouter()


@router.get("/videos")
async def list_videos(status: Optional[str] = Query(None)):
    async with get_db() as db:
        if status:
            cursor = await db.execute(
                "SELECT * FROM videos WHERE status=? ORDER BY created_at DESC",
                (status,)
            )
        else:
            cursor = await db.execute("SELECT * FROM videos ORDER BY created_at DESC")
        rows = await cursor.fetchall()

        # Get shorts count per video
        result = []
        for row in rows:
            shorts_cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM shorts WHERE video_id=?", (row["id"],)
            )
            shorts_row = await shorts_cursor.fetchone()

            result.append({
                "id": row["id"],
                "channel_id": row["channel_id"],
                "video_url": row["video_url"],
                "video_title": row["video_title"],
                "video_id": row["video_id"],
                "duration_seconds": row["duration_seconds"],
                "status": row["status"],
                "error_message": row["error_message"],
                "published_at": row["published_at"],
                "created_at": row["created_at"],
                "processed_at": row["processed_at"],
                "shorts_count": shorts_row["cnt"],
            })
    return result


@router.get("/videos/{video_id}")
async def get_video(video_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM videos WHERE id=?", (video_id,))
        row = await cursor.fetchone()
        if not row:
            return None

        shorts_cursor = await db.execute(
            "SELECT * FROM shorts WHERE video_id=? ORDER BY score DESC",
            (video_id,)
        )
        shorts = await shorts_cursor.fetchall()

    return {
        "id": row["id"],
        "channel_id": row["channel_id"],
        "video_url": row["video_url"],
        "video_title": row["video_title"],
        "status": row["status"],
        "shorts": [
            {
                "id": s["id"],
                "title": s["title"],
                "score": s["score"],
                "hook_sentence": s["hook_sentence"],
                "file_path": s["file_path"],
                "status": s["status"],
            }
            for s in shorts
        ],
    }
