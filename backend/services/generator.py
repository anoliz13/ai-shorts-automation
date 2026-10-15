"""Short generation service using AI-Youtube-Shorts-Generator."""

import asyncio
from datetime import datetime
from backend.database import get_db
from backend.config import settings
from backend.services.logger import get_logger

logger = get_logger(__name__)


async def generate_shorts(url: str, num_clips: int = 5, mode: str = "api",
                          aspect_ratio: str = "9:16") -> dict:
    """Generate shorts from a video URL. Returns dict with shorts list."""
    # Import from the shorts_generator module (will be implemented)
    try:
        from shorts_generator import generate_shorts as _generate
        return await asyncio.to_thread(_generate, url, num_clips, mode, aspect_ratio)
    except ImportError:
        logger.warning("shorts_generator not available, returning empty")
        return {"shorts": []}


async def process_pending_videos() -> dict:
    """Process all pending videos: generate shorts for each."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM videos WHERE status='pending'"
        )
        videos = await cursor.fetchall()

    processed = 0
    shorts_generated = 0
    failed = 0

    for video in videos:
        vid = video["id"]
        logger.info(f"Processing video {vid}: {video['video_title']}")

        async with get_db() as db:
            await db.execute(
                "UPDATE videos SET status='processing' WHERE id=?", (vid,)
            )
            await db.commit()

        try:
            result = await generate_shorts(
                video["video_url"],
                num_clips=settings.max_shorts_per_video,
                mode=settings.shorts_mode,
            )

            shorts = result.get("shorts", [])
            # Sort by score descending, take top N
            shorts.sort(key=lambda s: s.get("score", 0), reverse=True)
            shorts = shorts[:settings.max_shorts_per_video]

            async with get_db() as db:
                for s in shorts:
                    await db.execute(
                        """INSERT INTO shorts (video_id, title, start_time, end_time,
                           score, hook_sentence, virality_reason, file_path, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
                        (vid, s.get("title", ""), s.get("start_time", 0),
                         s.get("end_time", 0), s.get("score", 0),
                         s.get("hook_sentence", ""), s.get("virality_reason", ""),
                         s.get("clip_url", ""))
                    )
                    shorts_generated += 1

                await db.execute(
                    "UPDATE videos SET status='done', processed_at=? WHERE id=?",
                    (datetime.utcnow().isoformat(), vid)
                )
                await db.commit()

            processed += 1
            logger.info(f"Video {vid}: {len(shorts)} shorts generated")

        except Exception as e:
            logger.error(f"Failed to process video {vid}: {e}")
            async with get_db() as db:
                await db.execute(
                    "UPDATE videos SET status='failed', error_message=? WHERE id=?",
                    (str(e), vid)
                )
                await db.commit()
            failed += 1

    logger.info(f"Generation complete: {processed} processed, {shorts_generated} shorts, {failed} failed")
    return {"processed": processed, "shorts_generated": shorts_generated, "failed": failed}
