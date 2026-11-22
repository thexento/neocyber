"""SQLite-backed session, message, and findings storage for NeoCyber."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

from neocyber.models.message import Message, Role, ToolCall
from neocyber.models.session import Session


class Database:
    """Manages SQLite database for NeoCyber."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            data_dir = os.path.expanduser("~/.local/share/neocyber")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "neocyber.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    model_profile TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    tool_calls_json TEXT NOT NULL DEFAULT '[]',
                    is_error INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    description TEXT NOT NULL,
                    evidence_file TEXT,
                    remediation TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    # ── Sessions ─────────────────────────────────────────────────────────────

    def save_session(self, session: Session) -> None:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, title, agent, model_profile, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    agent = excluded.agent,
                    model_profile = excluded.model_profile,
                    updated_at = excluded.updated_at
                """,
                (
                    session.id,
                    session.title,
                    session.agent,
                    session.model_profile,
                    session.created_at.isoformat(),
                    now,
                ),
            )

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None

            msg_rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()

            messages: List[Message] = []
            for m in msg_rows:
                tc_data = json.loads(m["tool_calls_json"])
                tool_calls = [ToolCall(**tc) for tc in tc_data]
                messages.append(
                    Message(
                        role=Role(m["role"]),
                        content=m["content"],
                        timestamp=datetime.fromisoformat(m["created_at"]),
                        tool_calls=tool_calls,
                        is_error=bool(m["is_error"]),
                        agent=m["agent"],
                    )
                )

            return Session(
                id=row["id"],
                title=row["title"],
                agent=row["agent"],
                model_profile=row["model_profile"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                messages=messages,
            )

    def list_sessions(self) -> List[Session]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, agent, model_profile, created_at, updated_at "
                "FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
            return [
                Session(
                    id=r["id"],
                    title=r["title"],
                    agent=r["agent"],
                    model_profile=r["model_profile"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    updated_at=datetime.fromisoformat(r["updated_at"]),
                    messages=[],
                )
                for r in rows
            ]

    def delete_session(self, session_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def save_message(self, session_id: str, message: Message) -> None:
        tool_calls_dicts = [
            {
                "id": tc.id,
                "name": tc.name,
                "arguments": tc.arguments,
                "status": tc.status,
                "output": tc.output,
                "duration": tc.duration,
                "exit_code": tc.exit_code,
            }
            for tc in message.tool_calls
        ]
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    session_id, role, content, agent, tool_calls_json, is_error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    message.role.value,
                    message.content,
                    message.agent,
                    json.dumps(tool_calls_dicts),
                    1 if message.is_error else 0,
                    message.timestamp.isoformat(),
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), session_id),
            )

    # ── Findings ─────────────────────────────────────────────────────────────

    def save_finding(
        self,
        finding_id: str,
        title: str,
        severity: str,
        asset: str,
        description: str,
        evidence_file: Optional[str] = None,
        remediation: Optional[str] = None,
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO findings (
                    id, title, severity, asset, description, evidence_file, remediation, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    severity = excluded.severity,
                    asset = excluded.asset,
                    description = excluded.description,
                    evidence_file = excluded.evidence_file,
                    remediation = excluded.remediation
                """,
                (
                    finding_id,
                    title,
                    severity.upper(),
                    asset,
                    description,
                    evidence_file,
                    remediation,
                    datetime.now().isoformat(),
                ),
            )

    def list_findings(self) -> List[dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM findings ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
