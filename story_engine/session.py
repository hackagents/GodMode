from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras

from story_engine.config import settings
from story_engine.models import ChapterResponse, SessionState


def _serialize(state: SessionState) -> dict:
    return {
        "session_id": state.session_id,
        "source_story": state.source_story,
        "catalog_id": state.catalog_id,
        "chapter_count": state.chapter_count,
        "status": state.status,
        "history": json.dumps(state.history),
        "chapters": json.dumps([c.model_dump() for c in state.chapters]),
    }


def _deserialize(row: psycopg2.extras.RealDictRow) -> SessionState:
    return SessionState(
        session_id=row["session_id"],
        source_story=row["source_story"],
        catalog_id=row["catalog_id"],
        chapter_count=row["chapter_count"],
        status=row["status"],
        history=json.loads(row["history"]),
        chapters=[ChapterResponse(**c) for c in json.loads(row["chapters"])],
    )


class SessionStore:
    def __init__(self, database_url: str):
        self._database_url = database_url

    def _connect(self) -> psycopg2.extensions.connection:
        return psycopg2.connect(self._database_url)

    @contextmanager
    def _cursor(self):
        conn = self._connect()
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    yield cur
        finally:
            conn.close()

    def init_db(self) -> None:
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS sessions (
                            session_id    TEXT PRIMARY KEY,
                            source_story  TEXT NOT NULL,
                            catalog_id    INTEGER,
                            chapter_count INTEGER NOT NULL DEFAULT 0,
                            status        TEXT NOT NULL DEFAULT 'active',
                            history       TEXT NOT NULL DEFAULT '[]',
                            chapters      TEXT NOT NULL DEFAULT '[]',
                            created_at    TIMESTAMPTZ DEFAULT NOW(),
                            updated_at    TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
        finally:
            conn.close()

    def create(self, source_story: str, catalog_id: Optional[int] = None) -> SessionState:
        state = SessionState(
            session_id=str(uuid.uuid4()),
            source_story=source_story,
            catalog_id=catalog_id,
            chapter_count=0,
            status="active",
            history=[],
            chapters=[],
        )
        row = _serialize(state)
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO sessions
                   (session_id, source_story, catalog_id, chapter_count, status, history, chapters)
                   VALUES (%(session_id)s, %(source_story)s, %(catalog_id)s,
                           %(chapter_count)s, %(status)s, %(history)s, %(chapters)s)""",
                row,
            )
        return state

    def get(self, session_id: str) -> Optional[SessionState]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM sessions WHERE session_id = %s", (session_id,))
            row = cur.fetchone()
        return _deserialize(row) if row else None

    def update(self, session_id: str, state: SessionState) -> None:
        row = _serialize(state)
        with self._cursor() as cur:
            cur.execute(
                """UPDATE sessions
                   SET source_story  = %(source_story)s,
                       catalog_id    = %(catalog_id)s,
                       chapter_count = %(chapter_count)s,
                       status        = %(status)s,
                       history       = %(history)s,
                       chapters      = %(chapters)s,
                       updated_at    = NOW()
                   WHERE session_id = %(session_id)s""",
                row,
            )

    def delete(self, session_id: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))


session_store = SessionStore(database_url=settings.DATABASE_URL)
