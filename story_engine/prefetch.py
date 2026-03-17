from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from google.genai import types as genai_types

from story_engine.agent.image_generator import generate_chapter_image
from story_engine.agent.parser import parse_chapter
from story_engine.agent.story_agent import build_story_runner, create_seeded_session
from story_engine.agent.tts_agent import run_tts
from story_engine.catalog import catalog_store
from story_engine.config import settings
from story_engine.models import ChapterResponse, SessionState

logger = logging.getLogger(__name__)

_TTS_PREFETCH_VOICE = "Kore"


# ── TTS prefetch cache ────────────────────────────────────────────────────────

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


# ── Chapter prefetch cache ────────────────────────────────────────────────────

@dataclass
class PrefetchResult:
    chapter: ChapterResponse
    history: list[dict]  # full updated history including the model turn


class PrefetchCache:
    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], PrefetchResult] = {}

    def store(self, session_id: str, choice_key: str, result: PrefetchResult) -> None:
        self._cache[(session_id, choice_key)] = result

    def pop(self, session_id: str, choice_key: str) -> Optional[PrefetchResult]:
        return self._cache.pop((session_id, choice_key), None)

    def invalidate(self, session_id: str) -> None:
        stale = [k for k in self._cache if k[0] == session_id]
        for k in stale:
            del self._cache[k]


prefetch_cache = PrefetchCache()


# ── TTS prefetch ──────────────────────────────────────────────────────────────

async def _prefetch_tts(session_id: str, choice_key: str, text: str) -> None:
    """Generate TTS for the first paragraph via the TTS ADK agent and cache it."""
    try:
        pcm = await run_tts(text, _TTS_PREFETCH_VOICE)
        tts_prefetch_cache.store(
            session_id, choice_key, TtsCacheEntry(voice=_TTS_PREFETCH_VOICE, pcm=pcm)
        )
        logger.debug("TTS prefetch stored for choice %s session %s", choice_key, session_id)
    except Exception:
        logger.warning(
            "TTS prefetch failed for choice %s session %s", choice_key, session_id, exc_info=True
        )


# ── Chapter prefetch ──────────────────────────────────────────────────────────

async def prefetch_choices(session: SessionState) -> None:
    """Generate all choice chapters in parallel via the story ADK agent and cache them."""
    last_chapter = session.chapters[-1]
    if not last_chapter.choices:
        return

    text_style: Optional[str] = None
    image_style: Optional[str] = None
    if session.catalog_id is not None:
        entry = catalog_store.get_story(session.catalog_id)
        if entry:
            text_style = entry.text_style
            image_style = entry.image_generated_style

    async def _generate(choice_key: str, choice_text: str) -> None:
        user_input = f"I choose {choice_key}: {choice_text}"
        if session.chapter_count >= settings.MAX_CHAPTERS - 1:
            user_input += (
                "\n\n[Story note: This is the final chapter. "
                "Please bring the story to a satisfying conclusion with an EPITAPH instead of CHOICES.]"
            )

        try:
            runner, session_service = build_story_runner(text_style)
            adk_session = await create_seeded_session(
                session_service, session.session_id, session.history
            )
            user_message = genai_types.Content(
                role="user", parts=[genai_types.Part(text=user_input)]
            )

            full_text = ""
            async for event in runner.run_async(
                user_id=session.session_id,
                session_id=adk_session.id,
                new_message=user_message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            full_text += part.text

            chapter = parse_chapter(full_text, chapter_number=session.chapter_count + 1)

            image_result = await asyncio.to_thread(
                generate_chapter_image,
                chapter.scene,
                chapter.reveal,
                session.source_story,
                image_style,
            )
            if image_result:
                chapter.image_base64, chapter.image_mime_type = image_result

            updated_history = session.history + [
                {"role": "user", "content": user_input},
                {"role": "model", "content": full_text},
            ]
            prefetch_cache.store(
                session.session_id,
                choice_key,
                PrefetchResult(chapter=chapter, history=updated_history),
            )
            logger.debug("Prefetched choice %s for session %s", choice_key, session.session_id)

            # TTS prefetch for first paragraph (background — don't block image gen)
            first_para = (chapter.scene or "").split("\n\n")[0].strip()
            if first_para:
                asyncio.create_task(_prefetch_tts(session.session_id, choice_key, first_para))

        except Exception:
            logger.warning("Prefetch failed for choice %s", choice_key, exc_info=True)

    await asyncio.gather(*[_generate(c.key, c.text) for c in last_chapter.choices])
