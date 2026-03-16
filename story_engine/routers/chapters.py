import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.genai import types as genai_types
from story_engine.models import ChoiceRequest
from story_engine.session import session_store
from story_engine.agent.client import gemini_client
from story_engine.agent.prompts import SYSTEM_PROMPT, build_continuation_messages
from story_engine.agent.parser import parse_chapter
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

    # Resolve choice key to text
    user_input = request.input
    if user_input.strip().upper() in ("A", "B", "C", "D") and session.chapters:
        key = user_input.strip().upper()
        last_chapter = session.chapters[-1]
        if last_chapter.choices:
            for choice in last_chapter.choices:
                if choice.key == key:
                    user_input = f"I choose {key}: {choice.text}"
                    break

    # Check if approaching max chapters
    if session.chapter_count >= settings.MAX_CHAPTERS - 1:
        user_input += "\n\n[Story note: This is the final chapter. Please bring the story to a satisfying conclusion with an EPITAPH instead of CHOICES.]"

    messages = build_continuation_messages(session.history, user_input)
    contents = [genai_types.Content(role=m["role"], parts=[genai_types.Part(text=m["content"])]) for m in messages]

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

            session.history = messages + [{"role": "model", "content": full_text}]
            session.chapter_count = new_chapter_number
            session.chapters.append(chapter)

            if chapter.is_ending or session.chapter_count >= settings.MAX_CHAPTERS:
                session.status = "ended"

            session_store.update(session.session_id, session)

            yield f"data: [CHAPTER_JSON] {chapter.model_dump_json()}\n\n"
        except Exception as e:
            logger.exception("Error generating chapter")
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
