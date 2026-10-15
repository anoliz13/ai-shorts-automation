"""Short generation pipeline (API mode via MuAPI)."""

import asyncio
import os
import subprocess
import tempfile
import requests
from backend.config import settings
from backend.services.logger import get_logger

logger = get_logger(__name__)


def _download_video(url: str, output_path: str) -> bool:
    """Download video using yt-dlp."""
    try:
        import yt_dlp
        ydl_opts = {
            "outtmpl": output_path,
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


def _transcribe_video(video_path: str) -> dict:
    """Transcribe video using faster-whisper (local mode) or MuAPI (API mode)."""
    if settings.shorts_mode == "local":
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel(
                settings.local_whisper_model,
                device=settings.local_whisper_device
            )
            segments, info = model.transcribe(video_path)
            transcript = {
                "duration": info.duration,
                "segments": [
                    {"start": s.start, "end": s.end, "text": s.text}
                    for s in segments
                ],
            }
            return transcript
        except ImportError:
            logger.warning("faster-whisper not installed, using mock transcript")
            return {"duration": 0, "segments": []}
    return {"duration": 0, "segments": []}


def _detect_highlights(transcript: dict) -> list[dict]:
    """Use LLM to detect viral highlight moments."""
    if not transcript.get("segments"):
        return []

    segments_text = " ".join([s["text"] for s in transcript["segments"]])

    try:
        if settings.llm_provider == "openai" and settings.openai_api_key:
            return _detect_highlights_openai(segments_text, transcript)
        elif settings.llm_provider == "gemini" and settings.gemini_api_key:
            return _detect_highlights_gemini(segments_text, transcript)
    except Exception as e:
        logger.error(f"LLM highlight detection failed: {e}")

    return []


def _detect_highlights_openai(text: str, transcript: dict) -> list[dict]:
    """Use OpenAI to detect highlights."""
    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": HIGHLIGHT_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.3,
    )
    content = response.choices[0].message.content
    # Parse JSON response
    import json
    try:
        highlights = json.loads(content)
        return highlights if isinstance(highlights, list) else highlights.get("highlights", [])
    except json.JSONDecodeError:
        return []


def _detect_highlights_gemini(text: str, transcript: dict) -> list[dict]:
    """Use Gemini to detect highlights."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content([
            HIGHLIGHT_SYSTEM_PROMPT,
            text,
        ])
        import json
        highlights = json.loads(response.text)
        return highlights if isinstance(highlights, list) else highlights.get("highlights", [])
    except Exception:
        return []


HIGHLIGHT_SYSTEM_PROMPT = """You are a viral content detection AI. Analyze the transcript and find the most viral-worthy moments for short-form vertical videos (Shorts, TikTok, Reels).

Criteria for virality (ranked by importance):
1. HOOK MOMENTS - Attention-grabbing statements in the first 3 seconds
2. EMOTIONAL PEAKS - Moments of high emotion (excitement, surprise, anger)
3. OPINION BOMBS - Controversial or bold statements
4. REVELATION MOMENTS - "I learned that..." / "The secret is..."
5. CONFLICT - Arguments, disagreements, tension
6. QUOTABLE LINES - Statements people would screenshot or share
7. STORY PEAKS - Climaxes in narratives
8. PRACTICAL VALUE - Actionable tips or insights

For each highlight, provide:
- title: Short descriptive title (max 50 chars)
- start_time: Start timestamp in seconds (float)
- end_time: End timestamp in seconds (float)
- score: Virality score 0-100 (integer)
- hook_sentence: The opening hook line (max 100 chars)
- virality_reason: One sentence explaining why this works

IMPORTANT: Only return highlights with score >= 70. Maximum 10 highlights.
Return ONLY valid JSON array, no other text."""


def _crop_vertical(video_path: str, start: float, end: float, output_path: str) -> bool:
    """Crop video segment to vertical 9:16 using ffmpeg."""
    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", str(start),
        "-t", str(duration),
        "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"ffmpeg crop failed: {e}")
        return False


def generate_shorts(url: str, num_clips: int = 5, mode: str = "api",
                     aspect_ratio: str = "9:16") -> dict:
    """Generate shorts from a YouTube video URL.

    Returns dict with 'shorts' list containing title, start_time, end_time,
    score, hook_sentence, virality_reason, clip_url.
    """
    output_dir = settings.local_output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Extract video ID for temp filename
    video_id = url.split("v=")[-1].split("&")[0] if "v=" in url else "unknown"
    temp_video = os.path.join(output_dir, f"source_{video_id}.mp4")

    # Download
    logger.info(f"Downloading video: {url}")
    if not os.path.exists(temp_video):
        if not _download_video(url, temp_video):
            return {"shorts": [], "error": "Download failed"}

    # Transcribe
    logger.info("Transcribing video...")
    transcript = _transcribe_video(temp_video)

    # Detect highlights
    logger.info("Detecting viral highlights...")
    highlights = _detect_highlights(transcript)

    if not highlights:
        return {"shorts": [], "error": "No highlights detected"}

    # Sort by score, take top N
    highlights.sort(key=lambda h: h.get("score", 0), reverse=True)
    highlights = highlights[:num_clips]

    # Crop each highlight
    shorts = []
    for i, h in enumerate(highlights):
        output_path = os.path.join(output_dir, f"short_{video_id}_{i+1}.mp4")
        logger.info(f"Cropping short {i+1}: {h['title']}")
        if _crop_vertical(temp_video, h["start_time"], h["end_time"], output_path):
            shorts.append({
                "title": h.get("title", ""),
                "start_time": h.get("start_time", 0),
                "end_time": h.get("end_time", 0),
                "score": h.get("score", 0),
                "hook_sentence": h.get("hook_sentence", ""),
                "virality_reason": h.get("virality_reason", ""),
                "clip_url": output_path,
            })

    logger.info(f"Generated {len(shorts)} shorts from {url}")
    return {"shorts": shorts}
