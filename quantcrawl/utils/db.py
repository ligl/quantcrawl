from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager


class SQLitePool:
    """Lightweight sqlite connection helper for utility-layer use cases."""

    def __init__(self, path: str) -> None:
        self.path = path

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
