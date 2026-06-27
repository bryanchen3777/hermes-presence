"""
inner_life/storage.py — SQLite 持久化

每個 profile 一個獨立的 db（或共享 db）。
提供 schema 初始化 + 基本 CRUD。
"""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


# ===== Schema =====

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS activity_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name    TEXT NOT NULL,
    ts              REAL NOT NULL,
    activity_type   TEXT NOT NULL,    -- 'wake' | 'meal' | 'work' | 'leisure' | 'social' | 'rest' | 'sleep' | 'thought'
    title           TEXT NOT NULL,    -- '起床' | '整理花園' | '幫 Ram 泡茶'
    description     TEXT,            -- 細節（可選）
    energy_delta    REAL DEFAULT 0,  -- 對能量的影響 -0.2 ~ +0.3
    emotion_delta   REAL DEFAULT 0,  -- 對情緒的影響（valence）-1 ~ 1
    related_profile TEXT,            -- 若有，'ram' / 'rem' / 'bryan'
    source          TEXT DEFAULT 'rule'  -- 'rule' | 'llm' | 'manual'
);
CREATE INDEX IF NOT EXISTS idx_activity_profile_ts
ON activity_log(profile_name, ts DESC);
CREATE INDEX IF NOT EXISTS idx_activity_type
ON activity_log(profile_name, activity_type);

CREATE TABLE IF NOT EXISTS body_state (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name    TEXT NOT NULL,
    ts              REAL NOT NULL,
    energy          REAL NOT NULL,    -- 0-1
    hunger          REAL NOT NULL,    -- 0-1
    fatigue         REAL NOT NULL,    -- 0-1
    comfort         REAL NOT NULL,    -- 0-1
    last_meal_ts    REAL,
    last_sleep_ts   REAL,
    last_awake_hours REAL
);
CREATE INDEX IF NOT EXISTS idx_body_profile_ts
ON body_state(profile_name, ts DESC);

CREATE TABLE IF NOT EXISTS inner_monologue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name    TEXT NOT NULL,
    ts              REAL NOT NULL,
    thought         TEXT NOT NULL,    -- '今天有點累，但晚上還算悠閒'
    trigger_event   TEXT,            -- 'idle_3hr' | 'after_meal' | 'saw_post' | 'manual'
    valence         REAL,            -- -1 ~ 1
    arousal         REAL             -- 0-1
);
CREATE INDEX IF NOT EXISTS idx_monologue_profile_ts
ON inner_monologue(profile_name, ts DESC);
"""


class Storage:
    """SQLite 持久化層"""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ===== activity_log =====

    def add_activity(
        self,
        profile_name: str,
        activity_type: str,
        title: str,
        description: Optional[str] = None,
        energy_delta: float = 0.0,
        emotion_delta: float = 0.0,
        related_profile: Optional[str] = None,
        source: str = "rule",
        ts: Optional[float] = None,
    ) -> int:
        ts = ts if ts is not None else time.time()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO activity_log
                (profile_name, ts, activity_type, title, description,
                 energy_delta, emotion_delta, related_profile, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (profile_name, ts, activity_type, title, description,
                 energy_delta, emotion_delta, related_profile, source),
            )
            conn.commit()
            return cur.lastrowid

    def get_activities(
        self,
        profile_name: str,
        since_ts: Optional[float] = None,
        limit: int = 50,
    ) -> list[dict]:
        with self._conn() as conn:
            if since_ts is not None:
                rows = conn.execute(
                    """SELECT * FROM activity_log
                    WHERE profile_name = ? AND ts >= ?
                    ORDER BY ts DESC LIMIT ?""",
                    (profile_name, since_ts, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM activity_log
                    WHERE profile_name = ?
                    ORDER BY ts DESC LIMIT ?""",
                    (profile_name, limit),
                ).fetchall()
        return [dict(r) for r in rows]

    # ===== body_state =====

    def add_body_state(
        self,
        profile_name: str,
        energy: float,
        hunger: float,
        fatigue: float,
        comfort: float = 0.8,
        last_meal_ts: Optional[float] = None,
        last_sleep_ts: Optional[float] = None,
        last_awake_hours: float = 0.0,
        ts: Optional[float] = None,
    ) -> int:
        ts = ts if ts is not None else time.time()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO body_state
                (profile_name, ts, energy, hunger, fatigue, comfort,
                 last_meal_ts, last_sleep_ts, last_awake_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (profile_name, ts, energy, hunger, fatigue, comfort,
                 last_meal_ts, last_sleep_ts, last_awake_hours),
            )
            conn.commit()
            return cur.lastrowid

    def get_latest_body_state(self, profile_name: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT * FROM body_state
                WHERE profile_name = ?
                ORDER BY ts DESC LIMIT 1""",
                (profile_name,),
            ).fetchone()
        return dict(row) if row else None

    # ===== inner_monologue =====

    def add_monologue(
        self,
        profile_name: str,
        thought: str,
        trigger_event: Optional[str] = None,
        valence: Optional[float] = None,
        arousal: Optional[float] = None,
        ts: Optional[float] = None,
    ) -> int:
        ts = ts if ts is not None else time.time()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO inner_monologue
                (profile_name, ts, thought, trigger_event, valence, arousal)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (profile_name, ts, thought, trigger_event, valence, arousal),
            )
            conn.commit()
            return cur.lastrowid

    def get_monologues(
        self,
        profile_name: str,
        since_ts: Optional[float] = None,
        limit: int = 20,
    ) -> list[dict]:
        with self._conn() as conn:
            if since_ts is not None:
                rows = conn.execute(
                    """SELECT * FROM inner_monologue
                    WHERE profile_name = ? AND ts >= ?
                    ORDER BY ts DESC LIMIT ?""",
                    (profile_name, since_ts, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM inner_monologue
                    WHERE profile_name = ?
                    ORDER BY ts DESC LIMIT ?""",
                    (profile_name, limit),
                ).fetchall()
        return [dict(r) for r in rows]
