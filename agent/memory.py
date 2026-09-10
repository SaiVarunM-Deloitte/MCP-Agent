from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


class TestMemory:

    def __init__(self, db_path: str | Path):

        self.db_path = str(db_path)

        Path(self.db_path).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.conn = sqlite3.connect(
            self.db_path
        )

        self.conn.row_factory = sqlite3.Row

        self._create_tables()

    # =====================================================
    # DATABASE
    # =====================================================

    def _create_tables(self):

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                total_tests INTEGER DEFAULT 0,
                passed INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0
            )
            """
        )

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                run_id INTEGER NOT NULL,

                test_id TEXT NOT NULL,

                test_name TEXT,

                attempt INTEGER NOT NULL,

                status TEXT NOT NULL,

                reason TEXT,

                error TEXT,

                evidence TEXT,

                duration REAL DEFAULT 0,

                created_at TEXT NOT NULL,

                FOREIGN KEY(run_id)
                    REFERENCES test_runs(run_id)
            )
            """
        )

        self.conn.commit()

    # =====================================================
    # RUN
    # =====================================================

    def create_run(self) -> int:

        cursor = self.conn.execute(
            """
            INSERT INTO test_runs(started_at)
            VALUES (?)
            """,
            (datetime.utcnow().isoformat(),)
        )

        self.conn.commit()

        return cursor.lastrowid

    # =====================================================
    # SAVE ATTEMPT
    # =====================================================

    def save_result(
        self,
        run_id: int,
        test_id: str,
        test_name: str,
        attempt: int,
        status: str,
        reason: str | None = None,
        error: str | None = None,
        evidence: list | None = None,
        duration: float = 0,
    ):

        self.conn.execute(
            """
            INSERT INTO test_attempts
            (
                run_id,
                test_id,
                test_name,
                attempt,
                status,
                reason,
                error,
                evidence,
                duration,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                test_id,
                test_name,
                attempt,
                status,
                reason,
                error,
                json.dumps(
                    evidence or [],
                    ensure_ascii=False
                ),
                duration,
                datetime.utcnow().isoformat()
            )
        )

        self.conn.commit()

    # =====================================================
    # HISTORY
    # =====================================================

    def get_test_history(
        self,
        test_id: str,
        limit: int = 10
    ):

        cursor = self.conn.execute(
            """
            SELECT *
            FROM test_attempts
            WHERE test_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (test_id, limit)
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    # =====================================================
    # CURRENT RUN FAILED TESTS
    # =====================================================

    def get_failed_tests(
        self,
        run_id: int
    ):

        cursor = self.conn.execute(
            """
            SELECT *
            FROM test_attempts
            WHERE run_id = ?
            AND attempt = (
                SELECT MAX(t2.attempt)
                FROM test_attempts t2
                WHERE t2.run_id = test_attempts.run_id
                  AND t2.test_id = test_attempts.test_id
            )
            AND status = 'FAILED'
            """,
            (run_id,)
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    # =====================================================
    # FINAL RESULTS
    # =====================================================

    def get_final_results(self, run_id: int):

        cursor = self.conn.execute(
            """
            SELECT *
            FROM test_attempts
            WHERE run_id = ?
            AND attempt = (
                SELECT MAX(t2.attempt)
                FROM test_attempts t2
                WHERE t2.run_id = test_attempts.run_id
                  AND t2.test_id = test_attempts.test_id
            )
            ORDER BY test_id
            """,
            (run_id,)
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    # =====================================================
    # FINISH RUN
    # =====================================================

    def finish_run(
        self,
        run_id: int,
        total_tests: int,
        passed: int,
        failed: int
    ):

        self.conn.execute(
            """
            UPDATE test_runs
            SET
                finished_at = ?,
                total_tests = ?,
                passed = ?,
                failed = ?
            WHERE run_id = ?
            """,
            (
                datetime.utcnow().isoformat(),
                total_tests,
                passed,
                failed,
                run_id
            )
        )

        self.conn.commit()

    def close(self):
        self.conn.close()