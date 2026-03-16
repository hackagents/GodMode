from fastapi import APIRouter, HTTPException, Response
from story_engine.models import SessionSummaryResponse
from story_engine.session import session_store

router = APIRouter()


@router.get("/stories/{session_id}", response_model=SessionSummaryResponse)
async def get_session(session_id: str):
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionSummaryResponse(
        session_id=session.session_id,
        source_story=session.source_story,
        chapter_count=session.chapter_count,
        status=session.status,
        chapters=session.chapters,
    )


@router.delete("/stories/{session_id}", status_code=204)
async def delete_session(session_id: str):
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session_store.delete(session_id)
    return Response(status_code=204)
