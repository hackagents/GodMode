from __future__ import annotations

import base64

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from google.genai.types import Modality

_TTS_MODEL = "gemini-2.5-flash-preview-tts"
_TTS_INSTRUCTION = (
    "Convert the provided text to speech exactly as given. "
    "Do not add any commentary or additional words."
)


def build_tts_runner(voice: str) -> tuple[Runner, InMemorySessionService]:
    """Return a Runner + session service for a single TTS request."""
    agent = LlmAgent(
        name="tts_agent",
        model=_TTS_MODEL,
        instruction=_TTS_INSTRUCTION,
        generate_content_config=genai_types.GenerateContentConfig(
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
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="story_tts", session_service=session_service)
    return runner, session_service


async def run_tts(text: str, voice: str) -> bytes:
    """Generate speech for the given text, returning raw PCM bytes."""
    runner, session_service = build_tts_runner(voice)
    adk_session = await session_service.create_session(
        app_name="story_tts",
        user_id="tts_user",
    )
    message = genai_types.Content(role="user", parts=[genai_types.Part(text=text)])

    async for event in runner.run_async(
        user_id="tts_user",
        session_id=adk_session.id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.inline_data and part.inline_data.data:
                    data = part.inline_data.data
                    return data if isinstance(data, bytes) else base64.b64decode(data)

    raise RuntimeError("TTS agent returned no audio")
