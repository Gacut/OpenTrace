from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 4

MIGRATIONS = {
    1: """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE items (
            id TEXT PRIMARY KEY, type TEXT NOT NULL, x REAL NOT NULL, y REAL NOT NULL,
            width REAL NOT NULL, height REAL NOT NULL, rotation REAL NOT NULL DEFAULT 0,
            z REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL, modified_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Nowe', tags_json TEXT NOT NULL DEFAULT '[]',
            locked INTEGER NOT NULL DEFAULT 0, payload_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX idx_items_type ON items(type);
        CREATE INDEX idx_items_status ON items(status);
        CREATE INDEX idx_items_modified ON items(modified_at);
        CREATE TABLE connections (
            id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL,
            color TEXT NOT NULL, width REAL NOT NULL, style TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '', direction TEXT NOT NULL DEFAULT 'forward',
            created_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY(target_id) REFERENCES items(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_connections_source ON connections(source_id);
        CREATE INDEX idx_connections_target ON connections(target_id);
    """,
    2: """
        ALTER TABLE connections ADD COLUMN relation_type TEXT NOT NULL DEFAULT 'jest powiązany z';
        ALTER TABLE connections ADD COLUMN confidence TEXT NOT NULL DEFAULT 'nieznany';
    """,
    3: """
        CREATE TABLE analysis_records (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '',
            tags_json TEXT NOT NULL DEFAULT '[]',
            item_ids_json TEXT NOT NULL DEFAULT '[]',
            data_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL
        );
        CREATE INDEX idx_records_kind ON analysis_records(kind);
        CREATE INDEX idx_records_status ON analysis_records(status);
        CREATE INDEX idx_records_modified ON analysis_records(modified_at);
    """,
    4: """
        ALTER TABLE connections ADD COLUMN branch_from_id TEXT NOT NULL DEFAULT '';
        CREATE INDEX idx_connections_branch ON connections(branch_from_id);
    """,
}


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.migrate()

    def migrate(self) -> None:
        current = int(self.connection.execute("PRAGMA user_version").fetchone()[0])
        if current > SCHEMA_VERSION:
            raise RuntimeError("Projekt utworzono w nowszej wersji aplikacji.")
        for version in range(current + 1, SCHEMA_VERSION + 1):
            with self.connection:
                self.connection.executescript(MIGRATIONS[version])
                self.connection.execute(f"PRAGMA user_version = {version}")

    def close(self) -> None:
        self.connection.close()
