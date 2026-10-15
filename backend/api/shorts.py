"""Shorts endpoints."""

from fastapi import APIRouter, HTTPException
from backend.database import get_db

router = APIRouter()


@router.get("/shorts")
async def list_shorts():
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT s.*, v.video_title as source_video_title
            FROM shorts s
            JOIN videos v ON s.video_id = v.id
            ORDER BY s.created_at DESC
        """)
        rows = await cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "video_id": row["video_id"],
            "video_title": row["source_video_title"],
            "title": row["title"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "score": row["score"],
            "hook_sentence": row["hook_sentence"],
            "virality_reason": row["virality_reason"],
            "file_path": row["file_path"],
            "status": row["status"],
            "created_at": row["created_at"],
        })
    return result


@router.post("/shorts/{short_id}/upload")
async def upload_short(short_id: int):
    """Manually trigger upload for a specific short."""
    from backend.services.uploader import upload_single_short
    result = await upload_single_short(short_id)
    return result
