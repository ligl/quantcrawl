from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any


class StorageRouterPipeline:
    """Default SQLite storage and optional PostgreSQL storage."""

    def __init__(self, storage_backend: str, sqlite_path: str, postgres_dsn: str) -> None:
        self.storage_backend = storage_backend
        self.sqlite_path = sqlite_path
        self.postgres_dsn = postgres_dsn
        self.sqlite_conn: sqlite3.Connection | None = None
        self.pg_conn: Any = None

    @classmethod
    def from_crawler(cls, crawler: Any) -> StorageRouterPipeline:
        settings = crawler.settings
        return cls(
            storage_backend=settings.get("STORAGE_BACKEND", "sqlite"),
            sqlite_path=settings.get("SQLITE_PATH", "data/quantcrawl.db"),
            postgres_dsn=settings.get("POSTGRES_DSN", ""),
        )

    def open_spider(self, spider: Any) -> None:
        _ = spider
        if self.storage_backend == "sqlite":
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            self._ensure_sqlite_table()
            return

        if self.storage_backend == "postgres":
            try:
                import psycopg
            except Exception as exc:  # pragma: no cover
                raise RuntimeError("psycopg is required for postgres backend") from exc

            self.pg_conn = psycopg.connect(self.postgres_dsn)
            self._ensure_postgres_table()
            return

        raise RuntimeError(f"Unsupported storage backend: {self.storage_backend}")

    def close_spider(self, spider: Any) -> None:
        _ = spider
        if self.sqlite_conn is not None:
            self.sqlite_conn.commit()
            self.sqlite_conn.close()
        if self.pg_conn is not None:
            self.pg_conn.commit()
            self.pg_conn.close()

    def process_item(self, item: Any, spider: Any) -> Any:
        _ = spider
        now = datetime.now(UTC).isoformat()
        payload = dict(item)
        source = str(payload.get("source", ""))
        dataset = str(payload.get("dataset", ""))
        record_hash = str(payload.get("raw_payload_hash", ""))

        if self.storage_backend == "sqlite":
            assert self.sqlite_conn is not None
            self.sqlite_conn.execute(
                """
                INSERT OR IGNORE INTO records
                (
                    source,
                    dataset,
                    raw_payload_hash,
                    event_time,
                    collected_at,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    dataset,
                    record_hash,
                    str(payload.get("event_time", "")),
                    str(payload.get("collected_at", "")),
                    json.dumps(payload, ensure_ascii=False),
                    now,
                ),
            )
            self.sqlite_conn.commit()
            return item

        if self.storage_backend == "postgres":
            assert self.pg_conn is not None
            with self.pg_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO records
                    (
                        source,
                        dataset,
                        raw_payload_hash,
                        event_time,
                        collected_at,
                        payload_json,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (source, dataset, raw_payload_hash) DO NOTHING
                    """,
                    (
                        source,
                        dataset,
                        record_hash,
                        str(payload.get("event_time", "")),
                        str(payload.get("collected_at", "")),
                        json.dumps(payload, ensure_ascii=False),
                        now,
                    ),
                )
            self.pg_conn.commit()
            return item

        return item

    def _ensure_sqlite_table(self) -> None:
        assert self.sqlite_conn is not None
        self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                dataset TEXT NOT NULL,
                raw_payload_hash TEXT NOT NULL,
                event_time TEXT,
                collected_at TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (source, dataset, raw_payload_hash)
            )
            """
        )
        self.sqlite_conn.commit()

    def _ensure_postgres_table(self) -> None:
        assert self.pg_conn is not None
        with self.pg_conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id BIGSERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    dataset TEXT NOT NULL,
                    raw_payload_hash TEXT NOT NULL,
                    event_time TEXT,
                    collected_at TEXT,
                    payload_json JSONB NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (source, dataset, raw_payload_hash)
                )
                """
            )
        self.pg_conn.commit()
