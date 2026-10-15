"""YouTube channel monitoring via yt-dlp."""

import yt_dlp
from datetime import datetime
from backend.database import get_db
from backend.services.logger import get_logger

logger = get_logger(__name__)


def fetch_recent_videos(channel_url: str) -> list[dict]:
    """Fetch recent videos from a YouTube channel (last 24 hours)."""
    ydl_opts = {
        "extract_flat": True,
        "playlistend": 20,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            if not result or "entries" not in result:
                return []
            videos = []
            for entry in result["entries"]:
                if entry:
                    videos.append({
                        "id": entry.get("id", ""),
                        "title": entry.get("title", ""),
                        "url": entry.get("url", ""),
                        "duration": entry.get("duration", 0),
                        "upload_date": entry.get("upload_date", ""),
                    })
            return videos
    except Exception as e:
        logger.warning(f"yt-dlp failed for {channel_url}: {e}")
        return []


async def scan_channel(channel_id: int, channel_url: str) -> dict:
    """Scan a single channel for new videos. Returns counts."""
    logger.info(f"Scanning channel {channel_id}: {channel_url}")
    videos = fetch_recent_videos(channel_url)

    new_count = 0
    skipped = 0

    async with get_db() as db:
        for video in videos:
            vid = video["id"]
            if not vid:
                continue

            cursor = await db.execute(
                "SELECT id FROM videos WHERE video_id=?", (vid,)
            )
            existing = await cursor.fetchone()

            if existing:
                skipped += 1
                continue

            await db.execute(
                """INSERT INTO videos (channel_id, video_url, video_id, video_title,
                   duration_seconds, published_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                (channel_id, video["url"], vid, video["title"],
                 video.get("duration"), video.get("upload_date"))
            )
            new_count += 1
            logger.info(f"New video detected: {video['title']} ({vid})")

        await db.execute(
            "UPDATE channels SET last_checked=? WHERE id=?",
            (datetime.utcnow().isoformat(), channel_id)
        )
        await db.commit()

    logger.info(f"Channel {channel_id}: {new_count} new, {skipped} skipped")
    return {"new_videos": new_count, "skipped": skipped}


async def scan_all_channels() -> dict:
    """Scan all enabled channels. Returns aggregate counts."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, channel_url FROM channels WHERE check_enabled=1"
        )
        channels = await cursor.fetchall()

    total_new = 0
    for ch in channels:
        result = await scan_channel(ch["id"], ch["channel_url"])
        total_new += result["new_videos"]

    logger.info(f"Scan complete: {len(channels)} channels, {total_new} new videos")
    return {"channels_checked": len(channels), "new_videos": total_new}
