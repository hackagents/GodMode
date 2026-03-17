from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass
from typing import Optional

from google.genai import types as genai_types
from google.genai.types import Modality

from story_engine.agent.client import gemini_client
from story_engine.agent.image_generator import generate_chapter_image
from story_engine.agent.parser import parse_chapter
from story_engine.agent.prompts import SYSTEM_PROMPT, build_continuation_messages
from story_engine.catalog import catalog_store
from story_engine.config import settings
from story_engine.models import ChapterResponse, SessionState

logger = logging.getLogger(__name__)

_TTS_MODEL = "gemini-2.5-flash-preview-tts"
_TTS_PREFETCH_VOICE = "Kore"


@dataclass
class TtsCacheEntry:
    voice: str
    pcm: bytes  # raw 16-bit PCM, 24 kHz mono


class TtsPrefetchCache:
    """Stores first-paragraph TTS audio pre-generated for each prefetched choice."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], TtsCacheEntry] = {}

    def store(self, session_id: str, choice_key: str, entry: TtsCacheEntry) -> None:
        self._cache[(session_id, choice_key)] = entry

    def pop(self, session_id: str, choice_key: str) -> Optional[TtsCacheEntry]:
        return self._cache.pop((session_id, choice_key), None)

    def invalidate(self, session_id: str) -> None:
        stale = [k for k in self._cache if k[0] == session_id]
        for k in stale:
            del self._cache[k]


tts_prefetch_cache = TtsPrefetchCache()


async def _prefetch_tts(session_id: str, choice_key: str, text: str) -> None:
    """Generate TTS for the first paragraph and store it in the cache."""
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=_TTS_MODEL,
            contents=text,
            config=genai_types.GenerateContentConfig(
                response_modalities=[Modality.AUDIO],
                speech_config=genai_types.SpeechConfig(
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                            voice_name=_TTS_PREFETCH_VOICE,
                        )
                    )
                ),
            ),
        )
        part = response.candidates[0].content.parts[0]
        data = part.inline_data.data
        raw: bytes = data if isinstance(data, bytes) else base64.b64decode(data)
        tts_prefetch_cache.store(session_id, choice_key, TtsCacheEntry(voice=_TTS_PREFETCH_VOICE, pcm=raw))
        logger.debug("TTS prefetch stored for choice %s session %s", choice_key, session_id)
    except Exception:
        logger.warning("TTS prefetch failed for choice %s session %s", choice_key, session_id, exc_info=True)


@dataclass
class PrefetchResult:
    chapter: ChapterResponse
    history: list[dict]  # full updated history including the model turn


class PrefetchCache:
    def __init__(self) -> None:
        # keyed by (session_id, choice_key)
        self._cache: dict[tuple[str, str], PrefetchResult] = {}

    def store(self, session_id: str, choice_key: str, result: PrefetchResult) -> None:
        self._cache[(session_id, choice_key)] = result

    def pop(self, session_id: str, choice_key: str) -> Optional[PrefetchResult]:
        """Retrieve and remove a cached result, or return None on miss."""
        return self._cache.pop((session_id, choice_key), None)

    def invalidate(self, session_id: str) -> None:
        """Discard all prefetch entries for a session (other choices are now stale)."""
        stale = [k for k in self._cache if k[0] == session_id]
        for k in stale:
            del self._cache[k]


prefetch_cache = PrefetchCache()


async def prefetch_choices(session: SessionState) -> None:
    """Generate all choices for the current chapter in parallel and cache them."""
    last_chapter = session.chapters[-1]
    if not last_chapter.choices:
        return

    image_style: Optional[str] = None
    if session.catalog_id is not None:
        entry = catalog_store.get_story(session.catalog_id)
        if entry:
            image_style = entry.image_generated_style

    async def _generate(choice_key: str, choice_text: str) -> None:
        user_input = f"I choose {choice_key}: {choice_text}"
        if session.chapter_count >= settings.MAX_CHAPTERS - 1:
            user_input += (
                "\n\n[Story note: This is the final chapter. "
                "Please bring the story to a satisfying conclusion with an EPITAPH instead of CHOICES.]"
            )

        messages = build_continuation_messages(session.history, user_input)
        contents = [
            genai_types.Content(role=m["role"], parts=[genai_types.Part(text=m["content"])])
            for m in messages
        ]

        try:
            response = await asyncio.to_thread(
                gemini_client.models.generate_content,
                model=settings.MODEL_NAME,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.9,
                    max_output_tokens=4096,
                ),
            )
            full_text = response.text or ""
            chapter = parse_chapter(full_text, chapter_number=session.chapter_count + 1)

            # Fire TTS prefetch for first paragraph as a background task (parallel with image)
            first_para = (chapter.scene or "").split("\n\n")[0].strip()
            if first_para:
                asyncio.create_task(_prefetch_tts(session.session_id, choice_key, first_para))

            image_result = await asyncio.to_thread(
                generate_chapter_image,
                chapter.scene,
                chapter.reveal,
                session.source_story,
                image_style,
            )
            if image_result:
                chapter.image_base64, chapter.image_mime_type = image_result

            prefetch_cache.store(
                session.session_id,
                choice_key,
                PrefetchResult(
                    chapter=chapter,
                    history=messages + [{"role": "model", "content": full_text}],
                ),
            )
            logger.debug("Prefetched choice %s for session %s", choice_key, session.session_id)
        except Exception:
            logger.warning("Prefetch failed for choice %s", choice_key, exc_info=True)

    await asyncio.gather(*[_generate(c.key, c.text) for c in last_chapter.choices])
