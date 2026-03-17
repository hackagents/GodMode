from __future__ import annotations

import pytest
import psycopg2

from story_engine.catalog import CatalogStore


@pytest.fixture
def store(pg_url, pg_conn):
    pg_conn.cursor().execute("DROP TABLE IF EXISTS catalog")
    s = CatalogStore(database_url=pg_url)
    s.init_db()
    yield s
    pg_conn.cursor().execute("DROP TABLE IF EXISTS catalog")


# ── init & seed ───────────────────────────────────────────────────────────────

def test_init_seeds_stories(store):
    stories = store.list_stories()
    assert len(stories) == 12


def test_init_is_idempotent(pg_url, pg_conn):
    """Calling init_db twice does not duplicate seed data."""
    pg_conn.cursor().execute("DROP TABLE IF EXISTS catalog")
    s = CatalogStore(database_url=pg_url)
    s.init_db()
    s.init_db()
    assert len(s.list_stories()) == 12
    pg_conn.cursor().execute("DROP TABLE IF EXISTS catalog")


def test_migration_adds_missing_columns(pg_url, pg_conn):
    """A table created without newer columns should be migrated by init_db."""
    pg_conn.cursor().execute("DROP TABLE IF EXISTS catalog")
    pg_conn.cursor().execute("""
        CREATE TABLE catalog (
            id          SERIAL PRIMARY KEY,
            title       TEXT NOT NULL,
            genre       TEXT NOT NULL,
            description TEXT NOT NULL,
            source_story TEXT NOT NULL
        )
    """)
    s = CatalogStore(database_url=pg_url)
    s.init_db()  # should add all missing columns without error
    story = s.create_story("Test", "drama", "desc", "Test source")
    assert story.image_base64 is None
    assert story.image_generated_style is None
    assert story.text_style is None
    pg_conn.cursor().execute("DROP TABLE IF EXISTS catalog")


# ── read ──────────────────────────────────────────────────────────────────────

def test_get_story_returns_correct_story(store):
    stories = store.list_stories()
    first = stories[0]
    fetched = store.get_story(first.id)
    assert fetched is not None
    assert fetched.title == first.title


def test_get_story_returns_none_for_missing_id(store):
    assert store.get_story(9999999) is None


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
    result = store.update_story(9999999, "T", "g", "d", "s")
    assert result is None


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_story(store):
    story = store.create_story("Delete Me", "drama", "desc", "source")
    assert store.delete_story(story.id) is True
    assert store.get_story(story.id) is None


def test_delete_nonexistent_story_returns_false(store):
    assert store.delete_story(9999999) is False


# ── initial_plot & environment ────────────────────────────────────────────────

def test_create_story_with_initial_plot_and_environment(store):
    story = store.create_story(
        title="Dune",
        genre="sci-fi",
        description="A desert planet saga.",
        source_story="Dune by Frank Herbert",
        initial_plot="Paul arrives on Arrakis and learns the ways of the Fremen.",
        environment="Desert planet Arrakis, brutal heat, scarce water, political intrigue",
    )
    assert story.initial_plot == "Paul arrives on Arrakis and learns the ways of the Fremen."
    assert story.environment == "Desert planet Arrakis, brutal heat, scarce water, political intrigue"
    fetched = store.get_story(story.id)
    assert fetched.initial_plot == story.initial_plot
    assert fetched.environment == story.environment


def test_create_story_without_plot_and_environment_defaults_to_none(store):
    story = store.create_story("Title", "drama", "desc", "source")
    assert story.initial_plot is None
    assert story.environment is None


def test_update_story_sets_initial_plot_and_environment(store):
    story = store.create_story("Title", "drama", "desc", "source")
    updated = store.update_story(
        story_id=story.id,
        title="Title",
        genre="drama",
        description="desc",
        source_story="source",
        initial_plot="A hero rises.",
        environment="Ancient Rome",
    )
    assert updated.initial_plot == "A hero rises."
    assert updated.environment == "Ancient Rome"


def test_update_story_clears_initial_plot_and_environment(store):
    story = store.create_story(
        "Title", "drama", "desc", "source",
        initial_plot="Some plot",
        environment="Some place",
    )
    updated = store.update_story(
        story_id=story.id,
        title="Title",
        genre="drama",
        description="desc",
        source_story="source",
        initial_plot=None,
        environment=None,
    )
    assert updated.initial_plot is None
    assert updated.environment is None


# ── text_style ────────────────────────────────────────────────────────────────

def test_create_story_with_text_style(store):
    story = store.create_story(
        title="Dune",
        genre="sci-fi",
        description="A desert planet saga.",
        source_story="Dune by Frank Herbert",
        text_style="Terse Hemingway prose, short punchy sentences",
    )
    assert story.text_style == "Terse Hemingway prose, short punchy sentences"
    fetched = store.get_story(story.id)
    assert fetched.text_style == "Terse Hemingway prose, short punchy sentences"


def test_create_story_without_text_style_defaults_to_none(store):
    story = store.create_story("Title", "drama", "desc", "source")
    assert story.text_style is None


def test_update_story_sets_text_style(store):
    story = store.create_story("Title", "drama", "desc", "source")
    updated = store.update_story(
        story_id=story.id,
        title="Title",
        genre="drama",
        description="desc",
        source_story="source",
        text_style="Florid Victorian gothic prose",
    )
    assert updated.text_style == "Florid Victorian gothic prose"


def test_update_story_clears_text_style(store):
    story = store.create_story("Title", "drama", "desc", "source", text_style="some style")
    updated = store.update_story(
        story_id=story.id,
        title="Title",
        genre="drama",
        description="desc",
        source_story="source",
        text_style=None,
    )
    assert updated.text_style is None
