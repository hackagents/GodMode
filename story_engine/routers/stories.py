from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.genai import types as genai_types

from story_engine.agent.image_generator import generate_chapter_image
from story_engine.agent.parser import parse_chapter
from story_engine.agent.prompts import build_opening_messages
from story_engine.agent.story_agent import build_story_runner, create_seeded_session
from story_engine.catalog import catalog_store
from story_engine.models import StartStoryRequest
from story_engine.prefetch import prefetch_choices
from story_engine.session import session_store

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stories")
async def start_story(request: StartStoryRequest):
    if request.catalog_id is not None:
        catalog_entry = catalog_store.get_story(request.catalog_id)
        if catalog_entry is None:
            raise HTTPException(status_code=404, detail="Catalog story not found")
        source_story = catalog_entry.source_story
    else:
        source_story = request.source_story

    async def event_stream():
        session = session_store.create(source_story, catalog_id=request.catalog_id)
        yield f"data: [SESSION_ID] {session.session_id}\n\n"

        initial_plot = catalog_entry.initial_plot if request.catalog_id is not None else None
        environment = catalog_entry.environment if request.catalog_id is not None else None
        text_style = catalog_entry.text_style if request.catalog_id is not None else None
        image_style = catalog_entry.image_generated_style if request.catalog_id is not None else None

        # Build the opening message (saved verbatim to history for continuations)
        opening_messages = build_opening_messages(
            source_story, initial_plot=initial_plot, environment=environment
        )
        opening_text = opening_messages[0]["content"]

        runner, session_service = build_story_runner(text_style)
        adk_session = await create_seeded_session(session_service, session.session_id, [])
        user_message = genai_types.Content(
            role="user", parts=[genai_types.Part(text=opening_text)]
        )

        try:
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
                            yield f"data: {part.text}\n\n"

            chapter = parse_chapter(full_text, chapter_number=1)

            image_result = await asyncio.to_thread(
                generate_chapter_image,
                chapter.scene,
                chapter.reveal,
                source_story,
                image_style,
            )
            if image_result:
                chapter.image_base64, chapter.image_mime_type = image_result

            session.history = [
                {"role": "user", "content": opening_text},
                {"role": "model", "content": full_text},
            ]
            session.chapter_count = 1
            session.chapters.append(chapter)
            if chapter.is_ending:
                session.status = "ended"
            session_store.update(session.session_id, session)

            if session.status != "ended" and chapter.choices:
                asyncio.create_task(prefetch_choices(session))

            yield f"data: [CHAPTER_JSON] {chapter.model_dump_json()}\n\n"
        except Exception as e:
            logger.exception("Error generating story")
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
