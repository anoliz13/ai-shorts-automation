"""Upload pipeline: TikTok + YouTube Shorts with anti-spam."""

import asyncio
from datetime import datetime
from backend.database import get_db
from backend.config import settings
from backend.services.logger import get_logger
from backend.services.anti_spam import check_daily_limit, record_upload_attempt, get_last_upload_time

logger = get_logger(__name__)


async def upload_to_tiktok(short_id: int, file_path: str, title: str) -> dict:
    """Upload a short to TikTok via Playwright browser automation."""
    try:
        from backend.services.tiktok_uploader import upload_to_tiktok as _upload
        return await _upload(file_path, title)
    except ImportError:
        logger.warning("TikTok uploader not available")
        return {"platform_video_id": None, "error": "Uploader not available"}


async def upload_to_youtube(short_id: int, file_path: str, title: str, description: str = "") -> dict:
    """Upload a short to YouTube via YouTube Data API v3."""
    try:
        from backend.services.youtube_uploader import upload_to_youtube as _upload
        return await _upload(file_path, title, description)
    except ImportError:
        logger.warning("YouTube uploader not available")
        return {"platform_video_id": None, "error": "Uploader not available"}


async def process_pending_uploads() -> dict:
    """Upload all pending shorts to TikTok and YouTube."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM shorts WHERE status='pending' ORDER BY score DESC"
        )
        shorts = await cursor.fetchall()

    uploaded = 0
    skipped = 0
    failed = 0

    for short in shorts:
        short_id = short["id"]

        for platform in ["tiktok", "youtube"]:
            # Check daily limit
            if not await check_daily_limit(platform):
                logger.info(f"Daily limit reached for {platform}, skipping short {short_id}")
                skipped += 1
                continue

            # Check gap since last upload
            last_upload = await get_last_upload_time(platform)
            if last_upload:
                elapsed = (datetime.utcnow() - last_upload).total_seconds() / 60
                if elapsed < settings.min_gap_minutes:
                    wait = (settings.min_gap_minutes - elapsed) * 60
                    logger.info(f"Waiting {wait:.0f}s before next {platform} upload")
                    await asyncio.sleep(wait)

            # Perform upload
            try:
                if platform == "tiktok":
                    result = await upload_to_tiktok(short_id, short["file_path"], short["title"])
                else:
                    result = await upload_to_youtube(short_id, short["file_path"], short["title"])

                platform_video_id = result.get("platform_video_id")
                error = result.get("error", "")

                async with get_db() as db:
                    if platform_video_id:
                        await db.execute(
                            """INSERT INTO uploads (short_id, platform, platform_video_id,
                               status, uploaded_at)
                               VALUES (?, ?, ?, 'done', ?)""",
                            (short_id, platform, platform_video_id, datetime.utcnow().isoformat())
                        )
                        await record_upload_attempt(platform)
                        uploaded += 1
                        logger.info(f"Uploaded short {short_id} to {platform}: {platform_video_id}")
                    else:
                        await db.execute(
                            """INSERT INTO uploads (short_id, platform, status, error_message)
                               VALUES (?, ?, 'failed', ?)""",
                            (short_id, platform, error or "Unknown error")
                        )
                        failed += 1
                        logger.error(f"Failed upload short {short_id} to {platform}: {error}")
                    await db.commit()

            except Exception as e:
                logger.error(f"Upload exception short {short_id} to {platform}: {e}")
                async with get_db() as db:
                    await db.execute(
                        """INSERT INTO uploads (short_id, platform, status, error_message)
                           VALUES (?, ?, 'failed', ?)""",
                        (short_id, platform, str(e))
                    )
                    await db.commit()
                failed += 1

        # Update short status
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT status FROM uploads WHERE short_id=? AND status='done'",
                (short_id,)
            )
            uploads = await cursor.fetchall()
            if uploads:
                await db.execute(
                    "UPDATE shorts SET status='uploaded' WHERE id=?", (short_id,)
                )
            await db.commit()

        # Gap between shorts
        await asyncio.sleep(settings.min_gap_minutes * 60)

    logger.info(f"Upload complete: {uploaded} uploaded, {skipped} skipped, {failed} failed")
    return {"uploaded": uploaded, "skipped": skipped, "failed": failed}


async def upload_single_short(short_id: int) -> dict:
    """Upload a single short to all platforms."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM shorts WHERE id=?", (short_id,))
        short = await cursor.fetchone()
        if not short:
            return {"error": "Short not found"}

    results = {}
    for platform in ["tiktok", "youtube"]:
        try:
            if platform == "tiktok":
                result = await upload_to_tiktok(short_id, short["file_path"], short["title"])
            else:
                result = await upload_to_youtube(short_id, short["file_path"], short["title"])
            results[platform] = result
        except Exception as e:
            results[platform] = {"error": str(e)}

    return results
