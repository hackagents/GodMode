from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Optional

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


def _deserialize(row: sqlite3.Row) -> SessionState:
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
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id    TEXT PRIMARY KEY,
                    source_story  TEXT NOT NULL,
                    catalog_id    INTEGER,
                    chapter_count INTEGER NOT NULL DEFAULT 0,
                    status        TEXT NOT NULL DEFAULT 'active',
                    history       TEXT NOT NULL DEFAULT '[]',
                    chapters      TEXT NOT NULL DEFAULT '[]',
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

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
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO sessions
                   (session_id, source_story, catalog_id, chapter_count, status, history, chapters)
                   VALUES (:session_id, :source_story, :catalog_id, :chapter_count, :status, :history, :chapters)""",
                row,
            )
        return state

    def get(self, session_id: str) -> Optional[SessionState]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return _deserialize(row) if row else None

    def update(self, session_id: str, state: SessionState) -> None:
        row = _serialize(state)
        with self._connect() as conn:
            conn.execute(
                """UPDATE sessions
                   SET source_story  = :source_story,
                       catalog_id    = :catalog_id,
                       chapter_count = :chapter_count,
                       status        = :status,
                       history       = :history,
                       chapters      = :chapters,
                       updated_at    = CURRENT_TIMESTAMP
                   WHERE session_id = :session_id""",
                row,
            )

    def delete(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


session_store = SessionStore(db_path=settings.CATALOG_DB_PATH)
