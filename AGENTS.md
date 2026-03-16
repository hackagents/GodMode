# AGENTS.md

This file provides guidance to AI agents working in this repository.

---

## Project Overview

Story Engine is a FastAPI application that transforms classic source stories into branching, choice-driven interactive narratives. It uses Google Gemini to stream vivid prose chapter by chapter, offering the reader four choices that shape where the story goes next. Stories are seeded from a SQLite catalog; sessions are held in memory.

---

## Architecture

```
story_engine/
├── main.py               # FastAPI app entry point; lifespan initialises the catalog DB
├── config.py             # pydantic-settings config (GEMINI_API_KEY, MODEL_NAME, etc.)
├── models.py             # All Pydantic request/response models
├── session.py            # In-memory SessionStore (dict-backed, per-process)
├── catalog.py            # SQLite-backed CatalogStore; seeds 12 classic stories on first run
├── agent/
│   ├── client.py         # Gemini client singleton
│   ├── prompts.py        # SYSTEM_PROMPT constant + message-builder helpers
│   └── parser.py         # Parses raw Gemini text into ChapterResponse
└── routers/
    ├── catalog.py        # GET  /catalog
    ├── stories.py        # POST /stories  (start a new session, streams SSE)
    ├── chapters.py       # POST /stories/{session_id}/chapters  (continue, streams SSE)
    └── sessions.py       # GET  /stories/{session_id}  |  DELETE /stories/{session_id}
```

### Request flow

```
Client
  │
  ├── GET  /catalog
  │     └── catalog.py router → CatalogStore.list_stories() → SQLite
  │
  ├── POST /stories  { catalog_id | source_story }
  │     └── stories.py router
  │           ├── (optional) CatalogStore.get_story(catalog_id) → resolves source_story
  │           ├── SessionStore.create(source_story) → new UUID session
  │           ├── build_opening_messages(source_story)
  │           ├── gemini_client.models.generate_content_stream(...)  ← SSE chunks
  │           ├── parse_chapter(full_text) → ChapterResponse
  │           └── SessionStore.update(session)
  │
  └── POST /stories/{session_id}/chapters  { input }
        └── chapters.py router
              ├── SessionStore.get(session_id)
              ├── Resolves choice key (A/B/C/D) → full choice text
              ├── build_continuation_messages(history, user_input)
              ├── gemini_client.models.generate_content_stream(...)  ← SSE chunks
              ├── parse_chapter(full_text) → ChapterResponse
              └── SessionStore.update(session)
```

---

## Code Style

- **Python 3.11+**. Use `from __future__ import annotations` at the top of every module.
- **Pydantic v2** for all models and config. No raw dicts for structured data passed between components.
- **Type annotations are mandatory** on all public functions and class methods.
- **No bare `except:`** — always catch specific exceptions. Routers catch `Exception` only to emit `[ERROR]` SSE events; keep this pattern consistent.
- **Async-first**: all FastAPI route handlers must be `async def`. Blocking I/O (e.g. SQLite in `catalog.py`) is acceptable only for lightweight catalog reads; if it becomes a bottleneck, move it to `asyncio.run_in_executor`.
- Follow consistent formatting — keep imports grouped (stdlib, third-party, local) and sorted within each group.

---

## Testing

**Write tests for every new feature before considering it done.**

- Place tests in `tests/` mirroring the source structure:
  ```
  tests/
  ├── unit/
  │   ├── test_parser.py
  │   ├── test_catalog.py
  │   └── test_session.py
  └── integration/
      └── test_routes.py
  ```
- **Unit tests** create unit test for mostly anything that you create.
- **Integration tests** do integration test b/w interaction of system or modules.
- When adding a new router or modifying an existing one, add or update the corresponding integration test.
- When modifying `parser.py`, add a unit test that covers the new or changed parsing behaviour with a raw string fixture.
- Run tests with:
  ```bash
  pytest tests/
  pytest --cov=story_engine tests/   # with coverage
  ```
- Aim for **≥ 85% coverage**.

