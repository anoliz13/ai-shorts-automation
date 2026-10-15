"""APScheduler for daily channel checks."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.config import settings
from backend.services.logger import get_logger

logger = get_logger(__name__)

scheduler = None


def start_scheduler():
    """Start the APScheduler with daily jobs."""
    global scheduler
    scheduler = AsyncIOScheduler()

    from backend.services.monitor import scan_all_channels
    from backend.services.generator import process_pending_videos
    from backend.services.uploader import process_pending_uploads

    # Daily channel check
    scheduler.add_job(
        scan_all_channels,
        trigger="cron",
        hour=settings.check_hour,
        minute=settings.check_minute,
        id="daily_check",
        replace_existing=True,
    )

    # Generate shorts 30 min after check
    scheduler.add_job(
        process_pending_videos,
        trigger="cron",
        hour=settings.check_hour,
        minute=(settings.check_minute + 30) % 60,
        id="generate_shorts",
        replace_existing=True,
    )

    # Upload 30 min after generation
    scheduler.add_job(
        process_pending_uploads,
        trigger="cron",
        hour=settings.check_hour,
        minute=(settings.check_minute + 60) % 60,
        id="upload_shorts",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started. Daily check at {settings.check_hour:02d}:{settings.check_minute:02d}")
    return scheduler
