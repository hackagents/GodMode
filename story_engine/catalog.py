import sqlite3
from dataclasses import dataclass
from typing import Optional
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


@dataclass
class CatalogStory:
    id: int
    title: str
    genre: str
    description: str
    source_story: str


class CatalogStore:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    genre TEXT NOT NULL,
                    description TEXT NOT NULL,
                    source_story TEXT NOT NULL
                )
            """)
            if conn.execute("SELECT COUNT(*) FROM catalog").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO catalog (title, genre, description, source_story) VALUES (?, ?, ?, ?)",
                    _SEED_STORIES,
                )

    def list_stories(self) -> list[CatalogStory]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, genre, description, source_story FROM catalog ORDER BY id"
            ).fetchall()
        return [CatalogStory(**dict(r)) for r in rows]

    def get_story(self, story_id: int) -> Optional[CatalogStory]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, genre, description, source_story FROM catalog WHERE id = ?",
                (story_id,),
            ).fetchone()
        return CatalogStory(**dict(row)) if row else None


catalog_store = CatalogStore(db_path=settings.CATALOG_DB_PATH)
