from __future__ import annotations

import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.genai import types as genai_types
from story_engine.models import ChoiceRequest
from story_engine.session import session_store
from story_engine.catalog import catalog_store
from story_engine.agent.client import gemini_client
from story_engine.agent.prompts import SYSTEM_PROMPT, build_continuation_messages
from story_engine.agent.parser import parse_chapter
from story_engine.agent.image_generator import generate_chapter_image
from story_engine.prefetch import prefetch_cache, prefetch_choices
from story_engine.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stories/{session_id}/chapters")
async def next_chapter(session_id: str, request: ChoiceRequest):
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "ended":
        raise HTTPException(status_code=400, detail="Story has already ended")

    raw = request.input.strip()
    choice_key = raw.upper() if raw.upper() in ("A", "B", "C", "D") else None

    # ── Cache hit: serve instantly ────────────────────────────────────────────
    if choice_key:
        cached = prefetch_cache.pop(session_id, choice_key)
        if cached:
            prefetch_cache.invalidate(session_id)  # other choices are now stale

            async def cached_stream():
                new_number = session.chapter_count + 1
                session.history = cached.history
                session.chapter_count = new_number
                session.chapters.append(cached.chapter)
                if cached.chapter.is_ending or new_number >= settings.MAX_CHAPTERS:
                    session.status = "ended"
                session_store.update(session_id, session)

                if session.status != "ended" and cached.chapter.choices:
                    asyncio.create_task(prefetch_choices(session))

                yield f"data: [CHAPTER_JSON] {cached.chapter.model_dump_json()}\n\n"

            return StreamingResponse(cached_stream(), media_type="text/event-stream")

    # ── Cache miss: generate live ─────────────────────────────────────────────
    user_input = raw
    if choice_key and session.chapters:
        last_chapter = session.chapters[-1]
        if last_chapter.choices:
            for choice in last_chapter.choices:
                if choice.key == choice_key:
                    user_input = f"I choose {choice_key}: {choice.text}"
                    break

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

    async def event_stream():
        try:
            full_text = ""
            response = gemini_client.models.generate_content_stream(
                model=settings.MODEL_NAME,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.9,
                    max_output_tokens=4096,
                ),
            )
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    yield f"data: {chunk.text}\n\n"

            new_chapter_number = session.chapter_count + 1
            chapter = parse_chapter(full_text, chapter_number=new_chapter_number)

            image_style = None
            if session.catalog_id is not None:
                catalog_entry = catalog_store.get_story(session.catalog_id)
                if catalog_entry:
                    image_style = catalog_entry.image_generated_style

            image_result = generate_chapter_image(chapter.scene, chapter.reveal, session.source_story, style=image_style)
            if image_result:
                chapter.image_base64, chapter.image_mime_type = image_result

            session.history = messages + [{"role": "model", "content": full_text}]
            session.chapter_count = new_chapter_number
            session.chapters.append(chapter)

            if chapter.is_ending or session.chapter_count >= settings.MAX_CHAPTERS:
                session.status = "ended"

            session_store.update(session.session_id, session)

            if session.status != "ended" and chapter.choices:
                asyncio.create_task(prefetch_choices(session))

            yield f"data: [CHAPTER_JSON] {chapter.model_dump_json()}\n\n"
        except Exception as e:
            logger.exception("Error generating chapter")
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
