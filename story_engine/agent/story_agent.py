from __future__ import annotations

import time

from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from story_engine.agent.prompts import SYSTEM_PROMPT
from story_engine.config import settings

_AGENT_NAME = "story_agent"


def build_story_agent(text_style: str | None = None) -> LlmAgent:
    instruction = SYSTEM_PROMPT
    if text_style:
        instruction += f"\n\n- Write all prose in the following style: {text_style}"

    return LlmAgent(
        name=_AGENT_NAME,
        model=settings.MODEL_NAME,
        instruction=instruction,
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=0.9,
            max_output_tokens=4096,
        ),
    )


def build_story_runner(text_style: str | None = None) -> tuple[Runner, InMemorySessionService]:
    """Return a Runner + session service scoped to one request."""
    agent = build_story_agent(text_style)
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="story_engine", session_service=session_service)
    return runner, session_service


async def create_seeded_session(
    session_service: InMemorySessionService,
    user_id: str,
    history: list[dict],
) -> object:
    """Create an ADK session and replay prior conversation history into it."""
    adk_session = await session_service.create_session(
        app_name="story_engine",
        user_id=user_id,
    )
    now = time.time()
    for i, msg in enumerate(history):
        author = "user" if msg["role"] == "user" else _AGENT_NAME
        event = Event(
            invocation_id=f"history_{i}",
            author=author,
            content=genai_types.Content(
                role=msg["role"],
                parts=[genai_types.Part(text=msg["content"])],
            ),
            timestamp=now + i,
        )
        await session_service.append_event(session=adk_session, event=event)
    return adk_session
