from __future__ import annotations

import pytest
from story_engine.catalog import CatalogStore


@pytest.fixture
def store(tmp_path):
    s = CatalogStore(db_path=str(tmp_path / "test.db"))
    s.init_db()
    return s


# ── init & seed ───────────────────────────────────────────────────────────────

def test_init_seeds_stories(store):
    stories = store.list_stories()
    assert len(stories) == 12


def test_init_is_idempotent(tmp_path):
    """Calling init_db twice does not duplicate seed data."""
    s = CatalogStore(db_path=str(tmp_path / "test.db"))
    s.init_db()
    s.init_db()
    assert len(s.list_stories()) == 12


def test_migration_adds_image_columns(tmp_path):
    """A DB created without image columns should be migrated on init_db."""
    import sqlite3
    db = str(tmp_path / "old.db")
    with sqlite3.connect(db) as conn:
        conn.execute("""
            CREATE TABLE catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, genre TEXT NOT NULL,
                description TEXT NOT NULL, source_story TEXT NOT NULL
            )
        """)
    s = CatalogStore(db_path=db)
    s.init_db()  # should add all three new columns without error
    story = s.create_story("Test", "drama", "desc", "Test source")
    assert story.image_base64 is None
    assert story.image_generated_style is None


# ── read ──────────────────────────────────────────────────────────────────────

def test_get_story_returns_correct_story(store):
    stories = store.list_stories()
    first = stories[0]
    fetched = store.get_story(first.id)
    assert fetched is not None
    assert fetched.title == first.title


def test_get_story_returns_none_for_missing_id(store):
    assert store.get_story(9999) is None


# ── create ────────────────────────────────────────────────────────────────────

def test_create_story(store):
    story = store.create_story(
        title="Dune",
        genre="sci-fi",
        description="A desert planet saga.",
        source_story="Dune by Frank Herbert",
    )
    assert story.id is not None
    assert story.title == "Dune"
    assert story.image_base64 is None
    assert story.image_generated_style is None
    assert len(store.list_stories()) == 13


def test_create_story_with_style(store):
    story = store.create_story(
        title="Dune",
        genre="sci-fi",
        description="A desert planet saga.",
        source_story="Dune by Frank Herbert",
        image_generated_style="watercolor, warm tones, impressionist",
    )
    assert story.image_generated_style == "watercolor, warm tones, impressionist"
    fetched = store.get_story(story.id)
    assert fetched.image_generated_style == "watercolor, warm tones, impressionist"


def test_create_story_with_image(store):
    story = store.create_story(
        title="Dune",
        genre="sci-fi",
        description="A desert planet saga.",
        source_story="Dune by Frank Herbert",
        image_base64="abc123",
        image_mime_type="image/png",
    )
    assert story.image_base64 == "abc123"
    assert story.image_mime_type == "image/png"

    fetched = store.get_story(story.id)
    assert fetched.image_base64 == "abc123"


# ── update ────────────────────────────────────────────────────────────────────

def test_update_story(store):
    story = store.create_story("Old Title", "drama", "Old desc", "Old source")
    updated = store.update_story(
        story_id=story.id,
        title="New Title",
        genre="comedy",
        description="New desc",
        source_story="New source",
    )
    assert updated is not None
    assert updated.title == "New Title"
    assert updated.genre == "comedy"
    assert updated.image_base64 is None
    assert updated.image_generated_style is None


def test_update_story_sets_style(store):
    story = store.create_story("Title", "drama", "desc", "source")
    updated = store.update_story(
        story_id=story.id,
        title="Title",
        genre="drama",
        description="desc",
        source_story="source",
        image_generated_style="pixel art, 8-bit, retro",
    )
    assert updated.image_generated_style == "pixel art, 8-bit, retro"


def test_update_story_sets_image(store):
    story = store.create_story("Title", "drama", "desc", "source")
    updated = store.update_story(
        story_id=story.id,
        title="Title",
        genre="drama",
        description="desc",
        source_story="source",
        image_base64="xyz",
        image_mime_type="image/jpeg",
    )
    assert updated.image_base64 == "xyz"


def test_update_story_clears_image(store):
    story = store.create_story("Title", "drama", "desc", "source", image_base64="old", image_mime_type="image/png")
    updated = store.update_story(
        story_id=story.id,
        title="Title",
        genre="drama",
        description="desc",
        source_story="source",
        image_base64=None,
    )
    assert updated.image_base64 is None


def test_update_nonexistent_story_returns_none(store):
    result = store.update_story(9999, "T", "g", "d", "s")
    assert result is None


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_story(store):
    story = store.create_story("Delete Me", "drama", "desc", "source")
    assert store.delete_story(story.id) is True
    assert store.get_story(story.id) is None


def test_delete_nonexistent_story_returns_false(store):
    assert store.delete_story(9999) is False
