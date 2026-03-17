from __future__ import annotations

import asyncio
import base64
import io
import logging
import struct

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from google.genai import types as genai_types
from google.genai.types import Modality

from story_engine.agent.client import gemini_client
from story_engine.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

_TTS_MODEL = "gemini-2.5-flash-preview-tts"
_STT_MODEL = settings.MODEL_NAME  # reuse existing flash model for transcription

VOICES = ["Kore", "Charon", "Fenrir", "Aoede", "Puck", "Zephyr", "Leda", "Orus"]


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
    buf.write(struct.pack("<I", 16))                                           # subchunk size
    buf.write(struct.pack("<H", 1))                                            # PCM format
    buf.write(struct.pack("<H", num_channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * num_channels * bits_per_sample // 8))  # byte rate
    buf.write(struct.pack("<H", num_channels * bits_per_sample // 8))         # block align
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
    """Convert story text to speech using Gemini TTS."""
    if voice not in VOICES:
        voice = "Kore"

    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=_TTS_MODEL,
            contents=text,
            config=genai_types.GenerateContentConfig(
                # Must use the Modality enum — the string "AUDIO" does not map correctly
                response_modalities=[Modality.AUDIO],
                speech_config=genai_types.SpeechConfig(
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            ),
        )

        part = response.candidates[0].content.parts[0]
        # SDK may return bytes or a base64 string depending on version
        data = part.inline_data.data
        raw = data if isinstance(data, bytes) else base64.b64decode(data)
        mime = part.inline_data.mime_type or ""

        # Gemini TTS returns raw PCM (audio/L16); wrap it in WAV so browsers can play it
        audio_bytes = raw if "wav" in mime else _pcm_to_wav(raw)

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

    # Serve from prefetch cache if available
    if session_id and choice_key:
        from story_engine.prefetch import tts_prefetch_cache
        entry = tts_prefetch_cache.pop(session_id, choice_key)
        if entry and entry.voice == voice:
            _CHUNK_BYTES = 4096

            async def cached_stream():
                raw = entry.pcm
                for i in range(0, len(raw), _CHUNK_BYTES):
                    b64 = base64.b64encode(raw[i : i + _CHUNK_BYTES]).decode()
                    yield f"data: {b64}\n\n"
                yield "data: [DONE]\n\n"

            logger.debug("TTS cache hit for choice %s session %s", choice_key, session_id)
            return StreamingResponse(cached_stream(), media_type="text/event-stream")

    async def event_stream():
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        # Chunk size in bytes: 4096 bytes = 2048 samples = ~85 ms at 24 kHz 16-bit mono
        _CHUNK_BYTES = 4096

        def _run() -> None:
            try:
                # TTS models only support generate_content, not generate_content_stream.
                # We generate the full audio, then manually chunk the PCM so the
                # frontend can start playing the first ~85 ms before the rest arrives.
                response = gemini_client.models.generate_content(
                    model=_TTS_MODEL,
                    contents=text,
                    config=genai_types.GenerateContentConfig(
                        response_modalities=[Modality.AUDIO],
                        speech_config=genai_types.SpeechConfig(
                            voice_config=genai_types.VoiceConfig(
                                prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                                    voice_name=voice,
                                )
                            )
                        ),
                    ),
                )
                part = response.candidates[0].content.parts[0]
                data = part.inline_data.data
                raw: bytes = data if isinstance(data, bytes) else base64.b64decode(data)

                for i in range(0, len(raw), _CHUNK_BYTES):
                    b64 = base64.b64encode(raw[i : i + _CHUNK_BYTES]).decode()
                    loop.call_soon_threadsafe(queue.put_nowait, b64)
            except Exception:
                logger.exception("TTS stream generation failed")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.create_task(asyncio.to_thread(_run))

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
