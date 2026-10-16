"""Provider management endpoints."""

import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db

router = APIRouter()


class ProviderIn(BaseModel):
    name: str
    provider_type: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class ProviderOut(BaseModel):
    id: int
    name: str
    provider_type: str
    model: Optional[str] = None
    is_active: bool
    is_builtin: bool
    test_status: str
    test_message: Optional[str] = None
    last_tested: Optional[str] = None


@router.get("/providers")
async def list_providers():
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM providers ORDER BY is_builtin DESC, name")
        rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


@router.post("/providers", status_code=201)
async def add_provider(provider: ProviderIn):
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO providers (name, provider_type, api_key, base_url, model)
               VALUES (?, ?, ?, ?, ?)""",
            (provider.name, provider.provider_type, provider.api_key,
             provider.base_url, provider.model)
        )
        await db.commit()
        pid = cursor.lastrowid
        cursor = await db.execute("SELECT * FROM providers WHERE id=?", (pid,))
        row = await cursor.fetchone()
    return _row_to_dict(row)


@router.patch("/providers/{provider_id}")
async def update_provider(provider_id: int, body: dict):
    async with get_db() as db:
        # Build dynamic update
        fields = []
        values = []
        for key in ["name", "provider_type", "api_key", "base_url", "model", "is_active"]:
            if key in body:
                fields.append(f"{key}=?")
                values.append(body[key])
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        values.append(provider_id)
        await db.execute(
            f"UPDATE providers SET {', '.join(fields)} WHERE id=?", values
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM providers WHERE id=?", (provider_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Provider not found")
    return _row_to_dict(row)


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT is_builtin FROM providers WHERE id=?", (provider_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Provider not found")
        if row["is_builtin"]:
            raise HTTPException(status_code=400, detail="Cannot delete built-in provider")
        await db.execute("DELETE FROM providers WHERE id=?", (provider_id,))
        await db.commit()
    return {"ok": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: int):
    """Test connectivity of a provider."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM providers WHERE id=?", (provider_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Provider not found")

        # Mark as testing
        await db.execute(
            "UPDATE providers SET test_status='testing' WHERE id=?", (provider_id,)
        )
        await db.commit()

    provider = _row_to_dict(row)
    status, message = await _test_connection(provider)

    async with get_db() as db:
        await db.execute(
            "UPDATE providers SET test_status=?, test_message=?, last_tested=? WHERE id=?",
            (status, message, datetime.utcnow().isoformat(), provider_id)
        )
        await db.commit()

    return {"status": status, "message": message}


async def _test_connection(provider: dict) -> tuple[str, str]:
    """Test a provider's connectivity. Returns (status, message)."""
    ptype = provider["provider_type"]

    if ptype == "llm":
        return await _test_llm(provider)
    elif ptype == "processing":
        return await _test_processing(provider)
    elif ptype == "transcription":
        return await _test_transcription(provider)
    else:
        return "untested", f"Unknown provider type: {ptype}"


async def _test_llm(provider: dict) -> tuple[str, str]:
    """Test LLM provider connectivity."""
    name = provider["name"].lower()
    api_key = provider.get("api_key")
    if not api_key:
        return "disconnected", "No API key configured"

    try:
        if "openai" in name:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=provider.get("model") or "gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5,
            )
            if response.choices:
                return "connected", "OpenAI connection successful"
        elif "gemini" in name or "google" in name:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(provider.get("model") or "gemini-2.5-flash")
            response = model.generate_content("Say 'ok'")
            if response.text:
                return "connected", "Gemini connection successful"
        else:
            # Generic OpenAI-compatible test
            import httpx
            base_url = provider.get("base_url") or "https://api.openai.com/v1"
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": provider.get("model") or "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "Say 'ok'"}],
                        "max_tokens": 5,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    return "connected", f"{provider['name']} connection successful"
                return "disconnected", f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return "disconnected", str(e)[:200]

    return "disconnected", "Could not verify connection"


async def _test_processing(provider: dict) -> tuple[str, str]:
    """Test processing provider (e.g. MuAPI)."""
    name = provider["name"].lower()
    api_key = provider.get("api_key")
    if not api_key:
        return "disconnected", "No API key configured"

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.muapi.ai/v1/me",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            if resp.status_code == 200:
                return "connected", "MuAPI connection successful"
            return "disconnected", f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return "disconnected", str(e)[:200]


async def _test_transcription(provider: dict) -> tuple[str, str]:
    """Test transcription provider (local Whisper)."""
    name = provider["name"].lower()
    if "whisper" in name or "local" in name:
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel(provider.get("model") or "base", device="cpu")
            return "connected", "faster-whisper model loaded successfully"
        except ImportError:
            return "disconnected", "faster-whisper not installed. Run: pip install faster-whisper"
        except Exception as e:
            return "disconnected", str(e)[:200]
    return "untested", "No test available for this provider"


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "provider_type": row["provider_type"],
        "api_key": row["api_key"],
        "base_url": row["base_url"],
        "model": row["model"],
        "is_active": bool(row["is_active"]),
        "is_builtin": bool(row["is_builtin"]),
        "test_status": row["test_status"],
        "test_message": row["test_message"],
        "last_tested": row["last_tested"],
    }
