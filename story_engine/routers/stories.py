from __future__ import annotations

import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.genai import types as genai_types
from story_engine.models import StartStoryRequest
from story_engine.session import session_store
from story_engine.catalog import catalog_store
from story_engine.agent.client import gemini_client
from story_engine.agent.prompts import SYSTEM_PROMPT, build_opening_messages
from story_engine.agent.parser import parse_chapter
from story_engine.agent.image_generator import generate_chapter_image
from story_engine.prefetch import prefetch_choices
from story_engine.config import settings

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

        messages = build_opening_messages(source_story)
        # Convert to genai Content format
        contents = [genai_types.Content(role=m["role"], parts=[genai_types.Part(text=m["content"])]) for m in messages]

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

            chapter = parse_chapter(full_text, chapter_number=1)

            image_style = catalog_entry.image_generated_style if request.catalog_id is not None else None
            image_result = generate_chapter_image(chapter.scene, chapter.reveal, source_story, style=image_style)
            if image_result:
                chapter.image_base64, chapter.image_mime_type = image_result

            session.history = messages + [{"role": "model", "content": full_text}]
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
