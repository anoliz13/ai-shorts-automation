"""Main FastAPI application."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.api.channels import router as channels_router
from backend.api.videos import router as videos_router
from backend.api.shorts import router as shorts_router
from backend.api.uploads import router as uploads_router
from backend.api.settings_api import router as settings_router
from backend.api.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    # Start scheduler
    try:
        from backend.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"Scheduler start failed: {e}")
    yield
    # Shutdown
    try:
        from backend.scheduler import scheduler
        if scheduler:
            scheduler.shutdown()
    except Exception:
        pass


app = FastAPI(
    title="AI Shorts Automation",
    description="Automated YouTube Shorts pipeline: monitor, generate, upload",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(channels_router, prefix="/api", tags=["channels"])
app.include_router(videos_router, prefix="/api", tags=["videos"])
app.include_router(shorts_router, prefix="/api", tags=["shorts"])
app.include_router(uploads_router, prefix="/api", tags=["uploads"])
app.include_router(settings_router, prefix="/api", tags=["settings"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])


@app.post("/api/pipeline/run-now")
async def run_pipeline_now():
    """Manually trigger the full pipeline."""
    from backend.services.monitor import scan_all_channels
    from backend.services.generator import process_pending_videos
    from backend.services.uploader import process_pending_uploads

    monitor_result = await scan_all_channels()
    generator_result = await process_pending_videos()
    uploader_result = await process_pending_uploads()

    return {
        "monitor": monitor_result,
        "generator": generator_result,
        "uploader": uploader_result,
    }


# Mount frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
