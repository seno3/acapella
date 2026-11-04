from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    duration REAL NOT NULL,
    settings TEXT NOT NULL,
    original_path TEXT NOT NULL,
    vocals_path TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    strength TEXT NOT NULL,
    input_path TEXT NOT NULL,
    status TEXT NOT NULL,          -- queued | processing | done | failed
    progress REAL NOT NULL DEFAULT 0,
    message TEXT,
    error TEXT,
    track_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            # A job left "processing" by a crash will never finish; mark it failed on startup.
            self._conn.execute(
                "UPDATE jobs SET status='failed', error='Interrupted by server restart' "
                "WHERE status IN ('queued','processing')"
            )
            self._conn.commit()

    def _exec(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur.fetchall()

    # Jobs
    def create_job(self, title: str, strength: str, input_path: str) -> dict:
        now = time.time()
        job_id = uuid.uuid4().hex
        self._exec(
            "INSERT INTO jobs (id,title,strength,input_path,status,progress,message,created_at,updated_at) "
            "VALUES (?,?,?,?,'queued',0,'Waiting in queue',?,?)",
            (job_id, title, strength, input_path, now, now),
        )
        return self.get_job(job_id)

    def update_job(self, job_id: str, **fields) -> None:
        fields["updated_at"] = time.time()
        cols = ",".join(f"{k}=?" for k in fields)
        self._exec(f"UPDATE jobs SET {cols} WHERE id=?", (*fields.values(), job_id))

    def get_job(self, job_id: str) -> dict | None:
        rows = self._exec("SELECT * FROM jobs WHERE id=?", (job_id,))
        return dict(rows[0]) if rows else None

    def list_jobs(self, active_only: bool = False) -> list[dict]:
        where = "WHERE status IN ('queued','processing')" if active_only else ""
        return [dict(r) for r in self._exec(f"SELECT * FROM jobs {where} ORDER BY created_at DESC")]

    # Tracks
    def create_track(self, track_id: str, title: str, duration: float, settings: dict,
                     original_path: str, vocals_path: str) -> dict:
        self._exec(
            "INSERT INTO tracks VALUES (?,?,?,?,?,?,?)",
            (track_id, title, duration, json.dumps(settings), original_path, vocals_path, time.time()),
        )
        return self.get_track(track_id)

    def get_track(self, track_id: str) -> dict | None:
        rows = self._exec("SELECT * FROM tracks WHERE id=?", (track_id,))
        return _track(rows[0]) if rows else None

    def list_tracks(self) -> list[dict]:
        return [_track(r) for r in self._exec("SELECT * FROM tracks ORDER BY created_at DESC")]

    def delete_track(self, track_id: str) -> None:
        self._exec("DELETE FROM tracks WHERE id=?", (track_id,))


def _track(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["settings"] = json.loads(d["settings"])
    return d
