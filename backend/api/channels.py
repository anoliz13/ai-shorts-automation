"""Channel CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from backend.database import get_db

router = APIRouter()


class ChannelIn(BaseModel):
    channel_url: str
    channel_name: Optional[str] = None


class ChannelOut(BaseModel):
    id: int
    channel_url: str
    channel_name: Optional[str] = None
    check_enabled: bool
    last_checked: Optional[str] = None
    created_at: str


@router.get("/channels", response_model=list[ChannelOut])
async def list_channels():
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM channels ORDER BY created_at DESC")
        rows = await cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "channel_url": row["channel_url"],
            "channel_name": row["channel_name"],
            "check_enabled": bool(row["check_enabled"]),
            "last_checked": row["last_checked"],
            "created_at": row["created_at"],
        })
    return result


@router.post("/channels", response_model=ChannelOut, status_code=201)
async def add_channel(channel: ChannelIn):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO channels (channel_url, channel_name) VALUES (?, ?)",
            (channel.channel_url, channel.channel_name)
        )
        await db.commit()
        channel_id = cursor.lastrowid

        cursor = await db.execute("SELECT * FROM channels WHERE id=?", (channel_id,))
        row = await cursor.fetchone()

    return {
        "id": row["id"],
        "channel_url": row["channel_url"],
        "channel_name": row["channel_name"],
        "check_enabled": bool(row["check_enabled"]),
        "last_checked": row["last_checked"],
        "created_at": row["created_at"],
    }


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int):
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM channels WHERE id=?", (channel_id,))
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Channel not found")
    return {"ok": True}


@router.patch("/channels/{channel_id}", response_model=ChannelOut)
async def update_channel(channel_id: int, body: dict):
    check_enabled = body.get("check_enabled")
    if check_enabled is None:
        raise HTTPException(status_code=400, detail="check_enabled is required")

    async with get_db() as db:
        cursor = await db.execute(
            "UPDATE channels SET check_enabled=? WHERE id=?",
            (int(check_enabled), channel_id)
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Channel not found")

        cursor = await db.execute("SELECT * FROM channels WHERE id=?", (channel_id,))
        row = await cursor.fetchone()

    return {
        "id": row["id"],
        "channel_url": row["channel_url"],
        "channel_name": row["channel_name"],
        "check_enabled": bool(row["check_enabled"]),
        "last_checked": row["last_checked"],
        "created_at": row["created_at"],
    }


@router.post("/channels/check-now")
async def check_now():
    """Manually trigger channel scan."""
    from backend.services.monitor import scan_all_channels
    result = await scan_all_channels()
    return result
