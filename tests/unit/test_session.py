from __future__ import annotations

import pytest
from story_engine.session import SessionStore


@pytest.fixture
def store(tmp_path):
    s = SessionStore(db_path=str(tmp_path / "test.db"))
    s.init_db()
    return s


def test_create_and_get(store):
    session = store.create("Hamlet by Shakespeare", catalog_id=1)

    assert session.session_id
    assert session.source_story == "Hamlet by Shakespeare"
    assert session.catalog_id == 1
    assert session.chapter_count == 0
    assert session.status == "active"

    fetched = store.get(session.session_id)
    assert fetched is not None
    assert fetched.session_id == session.session_id
    assert fetched.source_story == session.source_story
    assert fetched.catalog_id == 1


def test_create_without_catalog_id(store):
    session = store.create("A custom story")
    assert session.catalog_id is None
    fetched = store.get(session.session_id)
    assert fetched.catalog_id is None


def test_get_missing_session_returns_none(store):
    assert store.get("nonexistent-id") is None


def test_update_persists_changes(store):
    session = store.create("Hamlet by Shakespeare")
    session.chapter_count = 3
    session.status = "ended"
    store.update(session.session_id, session)

    fetched = store.get(session.session_id)
    assert fetched.chapter_count == 3
    assert fetched.status == "ended"


def test_update_persists_history(store):
    session = store.create("Hamlet by Shakespeare")
    session.history = [{"role": "user", "content": "Begin."}, {"role": "model", "content": "Once upon a time..."}]
    store.update(session.session_id, session)

    fetched = store.get(session.session_id)
    assert len(fetched.history) == 2
    assert fetched.history[0]["role"] == "user"


def test_delete(store):
    session = store.create("Hamlet by Shakespeare")
    store.delete(session.session_id)
    assert store.get(session.session_id) is None


def test_delete_nonexistent_does_not_raise(store):
    store.delete("nonexistent-id")  # should not raise


def test_sessions_survive_store_reinit(tmp_path):
    """Sessions written by one store instance are readable by a new instance on the same DB."""
    db = str(tmp_path / "test.db")

    store1 = SessionStore(db_path=db)
    store1.init_db()
    session = store1.create("Hamlet by Shakespeare", catalog_id=2)
    session.chapter_count = 2
    store1.update(session.session_id, session)

    store2 = SessionStore(db_path=db)
    store2.init_db()
    fetched = store2.get(session.session_id)
    assert fetched is not None
    assert fetched.chapter_count == 2
    assert fetched.catalog_id == 2
