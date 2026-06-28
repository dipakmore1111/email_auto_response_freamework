from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from .models import MessageOutcome, RunResult


class RunStore:
    def __init__(self, db_file: Path) -> None:
        self.db_file = db_file
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    mode TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    scanned INTEGER NOT NULL DEFAULT 0,
                    replied INTEGER NOT NULL DEFAULT 0,
                    skipped INTEGER NOT NULL DEFAULT 0,
                    failed INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'running',
                    error_text TEXT
                );

                CREATE TABLE IF NOT EXISTS message_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    from_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    action TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    generator TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(id)
                );
                """
            )
            conn.commit()

    def start_run(self, mode: str, query_text: str) -> int:
        now = datetime.now(UTC).isoformat()
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO runs (started_at, mode, query_text) VALUES (?, ?, ?)",
                (now, mode, query_text),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def add_event(self, run_id: int, event: MessageOutcome) -> None:
        now = datetime.now(UTC).isoformat()
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO message_events
                (run_id, created_at, message_id, from_email, subject, action, rule_name, generator, preview)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    now,
                    event.message_id,
                    event.from_email,
                    event.subject,
                    event.action,
                    event.rule_name,
                    event.generator,
                    event.preview,
                ),
            )
            conn.commit()

    def finish_run(self, run_id: int, result: RunResult, status: str = "completed", error_text: str = "") -> None:
        finished_at = datetime.now(UTC).isoformat()
        with closing(self._connect()) as conn:
            conn.execute(
                """
                UPDATE runs
                SET finished_at = ?, scanned = ?, replied = ?, skipped = ?, failed = ?, status = ?, error_text = ?
                WHERE id = ?
                """,
                (
                    finished_at,
                    result.scanned,
                    result.replied,
                    result.skipped,
                    result.failed,
                    status,
                    error_text,
                    run_id,
                ),
            )
            conn.commit()

    def recent_runs(self, limit: int = 10) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def recent_events(self, limit: int = 25) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT * FROM message_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def summary(self) -> dict[str, int]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_runs,
                    COALESCE(SUM(replied), 0) AS total_replied,
                    COALESCE(SUM(skipped), 0) AS total_skipped,
                    COALESCE(SUM(failed), 0) AS total_failed
                FROM runs
                """
            ).fetchone()
            return {
                "total_runs": int(row["total_runs"]),
                "total_replied": int(row["total_replied"]),
                "total_skipped": int(row["total_skipped"]),
                "total_failed": int(row["total_failed"]),
            }
