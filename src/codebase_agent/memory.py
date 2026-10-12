from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class MemoryItem:
    kind: str
    content: str
    created_at: str


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        kind TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)"
                )

    def add(self, kind: str, content: str) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO memories(kind, content, created_at) VALUES (?, ?, ?)",
                    (kind, content, created_at),
                )

    def search(self, query: str, limit: int = 5) -> list[MemoryItem]:
        like_query = f"%{query}%"
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT kind, content, created_at
                FROM memories
                WHERE content LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (like_query, limit),
            ).fetchall()

        return [MemoryItem(kind=row[0], content=row[1], created_at=row[2]) for row in rows]
