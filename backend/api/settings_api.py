"""Settings endpoints."""

from fastapi import APIRouter
from backend.database import get_db

router = APIRouter()


@router.get("/settings")
async def get_settings():
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value, description FROM settings")
        rows = await cursor.fetchall()
    return {row["key"]: row["value"] for row in rows}


@router.put("/settings")
async def update_settings(body: dict):
    async with get_db() as db:
        for key, value in body.items():
            await db.execute(
                """INSERT INTO settings (key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (key, str(value))
            )
        await db.commit()
    return {"ok": True}
