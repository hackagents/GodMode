from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

import psycopg2
import psycopg2.extras

from story_engine.config import settings

_SEED_STORIES = [
    ("Hamlet", "tragedy", "A Danish prince seeks revenge for his father's murder while grappling with doubt, madness, and mortality.", "Hamlet by Shakespeare"),
    ("The Odyssey", "epic", "A cunning hero battles gods, monsters, and temptation on a decade-long voyage home from war.", "The Odyssey by Homer"),
    ("Romeo and Juliet", "romance", "Two star-crossed lovers from rival families risk everything for love in Renaissance Verona.", "Romeo and Juliet by Shakespeare"),
    ("Frankenstein", "gothic horror", "An ambitious scientist creates life from death and must face the consequences of playing god.", "Frankenstein by Mary Shelley"),
    ("Pride and Prejudice", "romance", "A sharp-witted woman navigates love, class, and family pressures in Regency-era England.", "Pride and Prejudice by Jane Austen"),
    ("Moby Dick", "adventure", "An obsessed captain drags his crew into a doomed hunt for a legendary white whale.", "Moby Dick by Herman Melville"),
    ("The Count of Monte Cristo", "adventure", "A wrongfully imprisoned man escapes and meticulously dismantles the lives of those who betrayed him.", "The Count of Monte Cristo by Alexandre Dumas"),
    ("Crime and Punishment", "psychological thriller", "A destitute student commits a murder to test his theory of superior men — and unravels.", "Crime and Punishment by Fyodor Dostoevsky"),
    ("Don Quixote", "satire", "A delusional nobleman sets out on knightly adventures, tilting at windmills and testing the nature of reality.", "Don Quixote by Miguel de Cervantes"),
    ("1984", "dystopia", "A man working for a totalitarian regime begins to question the truth — and falls in love.", "1984 by George Orwell"),
    ("Macbeth", "tragedy", "A brave general murders his king after a prophecy kindles his ambition — and slowly loses everything.", "Macbeth by Shakespeare"),
    ("Jane Eyre", "gothic romance", "An orphaned governess finds love at a brooding manor while hiding its dark secret.", "Jane Eyre by Charlotte Brontë"),
]

_SELECT_COLS = (
    "id, title, genre, description, source_story, "
    "image_base64, image_mime_type, image_generated_style, "
    "initial_plot, environment, text_style"
)


@dataclass
class CatalogStory:
    id: int
    title: str
    genre: str
    description: str
    source_story: str
    image_base64: Optional[str] = field(default=None)
    image_mime_type: Optional[str] = field(default=None)
    image_generated_style: Optional[str] = field(default=None)
    initial_plot: Optional[str] = field(default=None)
    environment: Optional[str] = field(default=None)
    text_style: Optional[str] = field(default=None)


class CatalogStore:
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
                        CREATE TABLE IF NOT EXISTS catalog (
                            id                    SERIAL PRIMARY KEY,
                            title                 TEXT NOT NULL,
                            genre                 TEXT NOT NULL,
                            description           TEXT NOT NULL,
                            source_story          TEXT NOT NULL,
                            image_base64          TEXT,
                            image_mime_type       TEXT,
                            image_generated_style TEXT,
                            initial_plot          TEXT,
                            environment           TEXT,
                            text_style            TEXT
                        )
                    """)
                    # Migrate: add columns that may be missing in older schemas
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'catalog' AND table_schema = current_schema()
                    """)
                    existing = {row[0] for row in cur.fetchall()}
                    for col in ("image_base64", "image_mime_type", "image_generated_style",
                                "initial_plot", "environment", "text_style"):
                        if col not in existing:
                            cur.execute(f"ALTER TABLE catalog ADD COLUMN {col} TEXT")

                    cur.execute("SELECT COUNT(*) FROM catalog")
                    if cur.fetchone()[0] == 0:
                        cur.executemany(
                            "INSERT INTO catalog (title, genre, description, source_story) VALUES (%s, %s, %s, %s)",
                            _SEED_STORIES,
                        )
        finally:
            conn.close()

    # ── reads ─────────────────────────────────────────────────────────────────

    def list_stories(self) -> list[CatalogStory]:
        with self._cursor() as cur:
            cur.execute(f"SELECT {_SELECT_COLS} FROM catalog ORDER BY id")
            rows = cur.fetchall()
        return [CatalogStory(**dict(r)) for r in rows]

    def get_story(self, story_id: int) -> Optional[CatalogStory]:
        with self._cursor() as cur:
            cur.execute(f"SELECT {_SELECT_COLS} FROM catalog WHERE id = %s", (story_id,))
            row = cur.fetchone()
        return CatalogStory(**dict(row)) if row else None

    # ── writes ────────────────────────────────────────────────────────────────

    def create_story(
        self,
        title: str,
        genre: str,
        description: str,
        source_story: str,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
        image_generated_style: Optional[str] = None,
        initial_plot: Optional[str] = None,
        environment: Optional[str] = None,
        text_style: Optional[str] = None,
    ) -> CatalogStory:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO catalog
                   (title, genre, description, source_story,
                    image_base64, image_mime_type, image_generated_style,
                    initial_plot, environment, text_style)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (title, genre, description, source_story,
                 image_base64, image_mime_type, image_generated_style,
                 initial_plot, environment, text_style),
            )
            new_id = cur.fetchone()["id"]
        return self.get_story(new_id)  # type: ignore[return-value]

    def update_story(
        self,
        story_id: int,
        title: str,
        genre: str,
        description: str,
        source_story: str,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
        image_generated_style: Optional[str] = None,
        initial_plot: Optional[str] = None,
        environment: Optional[str] = None,
        text_style: Optional[str] = None,
    ) -> Optional[CatalogStory]:
        with self._cursor() as cur:
            cur.execute(
                """UPDATE catalog
                   SET title = %s, genre = %s, description = %s, source_story = %s,
                       image_base64 = %s, image_mime_type = %s, image_generated_style = %s,
                       initial_plot = %s, environment = %s, text_style = %s
                   WHERE id = %s""",
                (title, genre, description, source_story,
                 image_base64, image_mime_type, image_generated_style,
                 initial_plot, environment, text_style, story_id),
            )
            rows_affected = cur.rowcount
        return self.get_story(story_id) if rows_affected else None

    def delete_story(self, story_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute("DELETE FROM catalog WHERE id = %s", (story_id,))
            return cur.rowcount > 0


catalog_store = CatalogStore(database_url=settings.DATABASE_URL)
