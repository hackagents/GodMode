from __future__ import annotations

import base64

from google import genai
from google.genai import types as genai_types
from google.genai.types import Modality

from story_engine.config import settings

_TTS_MODEL = "gemini-2.5-flash-preview-tts"
_TTS_INSTRUCTION = (
    "Convert the provided text to speech exactly as given. "
    "Do not add any commentary or additional words."
)

# Dedicated Gemini API client for TTS — bypasses Vertex AI which does not
# support the TTS preview model on the global endpoint.
# vertexai=False forces Gemini API even when GOOGLE_GENAI_USE_VERTEXAI=TRUE is set globally
_tts_client = genai.Client(api_key=settings.GEMINI_API_KEY, vertexai=False)


async def run_tts(text: str, voice: str) -> bytes:
    """Generate speech for the given text, returning raw PCM bytes."""
    response = await _tts_client.aio.models.generate_content(
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

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            data = part.inline_data.data
            return data if isinstance(data, bytes) else base64.b64decode(data)

    raise RuntimeError("TTS agent returned no audio")
