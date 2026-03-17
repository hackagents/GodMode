from __future__ import annotations

import asyncio
import base64
import io
import logging
import struct

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from google.genai import types as genai_types

from story_engine.agent.client import gemini_client
from story_engine.agent.tts_agent import run_tts
from story_engine.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

_STT_MODEL = settings.MODEL_NAME

VOICES = ["Kore", "Charon", "Fenrir", "Aoede", "Puck", "Zephyr", "Leda", "Orus"]

_CHUNK_BYTES = 4096  # ~85 ms of 16-bit mono PCM at 24 kHz


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 24000,
    num_channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    """Wrap raw PCM bytes in a RIFF/WAV container so browsers can play them."""
    data_size = len(pcm_data)
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))
    buf.write(struct.pack("<H", 1))   # PCM format
    buf.write(struct.pack("<H", num_channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * num_channels * bits_per_sample // 8))
    buf.write(struct.pack("<H", num_channels * bits_per_sample // 8))
    buf.write(struct.pack("<H", bits_per_sample))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm_data)
    return buf.getvalue()


@router.post("/narrate/tts")
async def text_to_speech(
    text: str = Form(...),
    voice: str = Form("Kore"),
):
    """Convert story text to speech using the TTS ADK agent, returning a WAV file."""
    if voice not in VOICES:
        voice = "Kore"
    try:
        raw = await run_tts(text, voice)
        audio_bytes = _pcm_to_wav(raw)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception:
        logger.exception("TTS generation failed")
        raise HTTPException(status_code=500, detail="TTS generation failed")


@router.post("/narrate/tts/stream")
async def tts_stream(
    text: str = Form(...),
    voice: str = Form("Kore"),
    session_id: str = Form(None),
    choice_key: str = Form(None),
):
    """Stream TTS audio as SSE events containing base64-encoded PCM chunks.

    Each event: data: <base64_pcm>
    Final event: data: [DONE]

    PCM format: 16-bit signed little-endian, mono, 24 kHz.
    """
    if voice not in VOICES:
        voice = "Kore"

    # ── Serve from prefetch cache if available ────────────────────────────────
    if session_id and choice_key:
        from story_engine.prefetch import tts_prefetch_cache
        entry = tts_prefetch_cache.pop(session_id, choice_key)
        if entry and entry.voice == voice:
            logger.debug("TTS cache hit for choice %s session %s", choice_key, session_id)

            async def cached_stream():
                raw = entry.pcm
                for i in range(0, len(raw), _CHUNK_BYTES):
                    b64 = base64.b64encode(raw[i : i + _CHUNK_BYTES]).decode()
                    yield f"data: {b64}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(cached_stream(), media_type="text/event-stream")

    # ── Generate via TTS ADK agent, then chunk the PCM ───────────────────────
    async def event_stream():
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        async def _run() -> None:
            try:
                raw = await run_tts(text, voice)
                for i in range(0, len(raw), _CHUNK_BYTES):
                    b64 = base64.b64encode(raw[i : i + _CHUNK_BYTES]).decode()
                    loop.call_soon_threadsafe(queue.put_nowait, b64)
            except Exception:
                logger.exception("TTS stream generation failed")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.create_task(_run())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {item}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/narrate/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("en-US"),
):
    """Transcribe recorded audio using Gemini multimodal, returning the raw transcript."""
    audio_bytes = await audio.read()
    mime_type = audio.content_type or "audio/webm"

    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=_STT_MODEL,
            contents=[
                genai_types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                (
                    f"Transcribe this audio exactly as spoken. "
                    f"Language hint: {language}. "
                    "The speaker is choosing between story options A, B, C, or D. "
                    "Output only the transcript, nothing else."
                ),
            ],
        )
        return {"transcript": response.text or ""}

    except Exception:
        logger.exception("STT transcription failed")
        raise HTTPException(status_code=500, detail="STT transcription failed")
