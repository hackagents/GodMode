from __future__ import annotations

import pytest
from story_engine.prefetch import PrefetchCache, PrefetchResult
from story_engine.models import ChapterResponse


def _result(chapter_number: int = 1) -> PrefetchResult:
    return PrefetchResult(
        chapter=ChapterResponse(chapter_number=chapter_number, is_ending=False),
        history=[{"role": "user", "content": "begin"}],
    )


def test_store_and_pop():
    cache = PrefetchCache()
    r = _result()
    cache.store("sess-1", "A", r)
    assert cache.pop("sess-1", "A") is r


def test_pop_returns_none_on_miss():
    cache = PrefetchCache()
    assert cache.pop("sess-1", "A") is None


def test_pop_removes_entry():
    cache = PrefetchCache()
    cache.store("sess-1", "A", _result())
    cache.pop("sess-1", "A")
    assert cache.pop("sess-1", "A") is None


def test_invalidate_removes_all_session_entries():
    cache = PrefetchCache()
    cache.store("sess-1", "A", _result())
    cache.store("sess-1", "B", _result())
    cache.store("sess-1", "C", _result())
    cache.store("sess-2", "A", _result())

    cache.invalidate("sess-1")

    assert cache.pop("sess-1", "A") is None
    assert cache.pop("sess-1", "B") is None
    assert cache.pop("sess-1", "C") is None
    # other session unaffected
    assert cache.pop("sess-2", "A") is not None


def test_invalidate_empty_cache_does_not_raise():
    cache = PrefetchCache()
    cache.invalidate("nonexistent")  # should not raise


def test_multiple_sessions_isolated():
    cache = PrefetchCache()
    r1, r2 = _result(1), _result(2)
    cache.store("sess-1", "A", r1)
    cache.store("sess-2", "A", r2)
    assert cache.pop("sess-1", "A") is r1
    assert cache.pop("sess-2", "A") is r2
