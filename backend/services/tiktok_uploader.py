"""TikTok uploader via Playwright browser automation."""

import asyncio
import os
from backend.services.logger import get_logger

logger = get_logger(__name__)


class TikTokAuthError(Exception):
    pass


async def upload_to_tiktok(file_path: str, title: str) -> dict:
    """Upload video to TikTok Creator Center using Playwright.

    First run: browser opens visibly so user can log in.
    Subsequent runs: headless with saved session.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"platform_video_id": None, "error": "playwright not installed"}

    session_file = "data/tiktok_session.json"
    has_session = os.path.exists(session_file)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=has_session)
        context = await browser.new_context(
            storage_state=session_file if has_session else None
        )
        page = await context.new_page()

        try:
            await page.goto("https://www.tiktok.com/creator-center/upload")
            await page.wait_for_load_state("networkidle")

            # Check if redirected to login
            if "login" in page.url:
                if not has_session:
                    logger.info("TikTok login required. Please log in when browser opens.")
                    # Wait for user to log in (up to 5 min)
                    await page.wait_for_url("**/creator-center/**", timeout=300000)
                    await context.storage_state(path=session_file)
                else:
                    raise TikTokAuthError("Session expired. Delete data/tiktok_session.json and retry.")

            # Upload file
            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                return {"platform_video_id": None, "error": "File input not found"}
            await file_input.set_input_files(file_path)

            # Wait for upload to complete
            await page.wait_for_selector('div[contenteditable="true"]', timeout=60000)

            # Set title
            title_input = await page.query_selector('div[contenteditable="true"]')
            if title_input:
                await title_input.click()
                await title_input.fill(title[:150])

            # Publish
            await page.wait_for_timeout(2000)
            publish_btn = await page.query_selector('button:has-text("Post")')
            if publish_btn:
                await publish_btn.click()
                await page.wait_for_timeout(10000)

            return {"platform_video_id": "uploaded", "error": None}

        except Exception as e:
            return {"platform_video_id": None, "error": str(e)}
        finally:
            await browser.close()
