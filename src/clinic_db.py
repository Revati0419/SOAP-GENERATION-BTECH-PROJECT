from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ClinicRepository:
    """Simple SQLite repository for patients and generated SOAP sessions."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    age INTEGER,
                    gender TEXT DEFAULT 'unknown',
                    phone TEXT,
                    notes TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    source_type TEXT NOT NULL,
                    transcript TEXT,
                    target_lang TEXT,
                    input_lang TEXT,
                    phq8_score INTEGER DEFAULT 0,
                    severity TEXT DEFAULT 'unknown',
                    gender TEXT DEFAULT 'unknown',
                    soap_english_json TEXT,
                    soap_target_json TEXT,
                    full_result_json TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(patient_id) REFERENCES patients(id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(full_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_patient ON sessions(patient_id)")
            conn.commit()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return dict(row) if row is not None else {}

    def create_patient(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO patients (full_name, age, gender, phone, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["full_name"].strip(),
                    payload.get("age"),
                    payload.get("gender", "unknown"),
                    payload.get("phone"),
                    payload.get("notes"),
                    now,
                ),
            )
            patient_id = cur.lastrowid
            conn.commit()
        return self.get_patient(patient_id)

    def list_patients(self, query: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 200))
        with self._connect() as conn:
            if query:
                pattern = f"%{query.strip()}%"
                rows = conn.execute(
                    """
                    SELECT p.*,
                           (SELECT COUNT(*) FROM sessions s WHERE s.patient_id = p.id) AS session_count
                    FROM patients p
                    WHERE lower(p.full_name) LIKE lower(?)
                    ORDER BY p.created_at DESC
                    LIMIT ?
                    """,
                    (pattern, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT p.*,
                           (SELECT COUNT(*) FROM sessions s WHERE s.patient_id = p.id) AS session_count
                    FROM patients p
                    ORDER BY p.created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_patient(self, patient_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT p.*, (SELECT COUNT(*) FROM sessions s WHERE s.patient_id = p.id) AS session_count
                FROM patients p
                WHERE p.id = ?
                """,
                (patient_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def create_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._connect() as conn:
            exists = conn.execute("SELECT id FROM patients WHERE id = ?", (payload["patient_id"],)).fetchone()
            if not exists:
                raise ValueError(f"Patient {payload['patient_id']} does not exist")

            cur = conn.execute(
                """
                INSERT INTO sessions (
                    patient_id, source_type, transcript, target_lang, input_lang,
                    phq8_score, severity, gender,
                    soap_english_json, soap_target_json, full_result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["patient_id"],
                    payload.get("source_type", "transcript"),
                    payload.get("transcript"),
                    payload.get("target_lang", "marathi"),
                    payload.get("input_lang"),
                    payload.get("phq8_score", 0),
                    payload.get("severity", "unknown"),
                    payload.get("gender", "unknown"),
                    json.dumps(payload.get("soap_english", {}), ensure_ascii=False),
                    json.dumps(payload.get("soap_target", {}), ensure_ascii=False),
                    json.dumps(payload.get("full_result", {}), ensure_ascii=False),
                    now,
                ),
            )
            session_id = cur.lastrowid
            conn.commit()
        return self.get_session(session_id)

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT s.*, p.full_name AS patient_name
                FROM sessions s
                JOIN patients p ON p.id = s.patient_id
                WHERE s.id = ?
                """,
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return self._decode_session_row(row)

    def list_sessions_for_patient(self, patient_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.*, p.full_name AS patient_name
                FROM sessions s
                JOIN patients p ON p.id = s.patient_id
                WHERE s.patient_id = ?
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (patient_id, limit),
            ).fetchall()
        return [self._decode_session_row(r) for r in rows]

    def list_recent_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.*, p.full_name AS patient_name
                FROM sessions s
                JOIN patients p ON p.id = s.patient_id
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._decode_session_row(r) for r in rows]

    def get_stats(self) -> Dict[str, int]:
        with self._connect() as conn:
            total_patients = conn.execute("SELECT COUNT(*) AS c FROM patients").fetchone()["c"]
            total_sessions = conn.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
            active_sessions = conn.execute(
                "SELECT COUNT(*) AS c FROM sessions WHERE created_at >= ?",
                (time.time() - 7 * 24 * 3600,),
            ).fetchone()["c"]
        return {
            "total_patients": int(total_patients),
            "total_sessions": int(total_sessions),
            "active_sessions_last_7_days": int(active_sessions),
        }

    @staticmethod
    def _safe_json_loads(text: Optional[str]) -> Dict[str, Any]:
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    def _decode_session_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = self._row_to_dict(row)
        data["soap_english"] = self._safe_json_loads(data.pop("soap_english_json", None))
        data["soap_target"] = self._safe_json_loads(data.pop("soap_target_json", None))
        data["full_result"] = self._safe_json_loads(data.pop("full_result_json", None))
        return data
