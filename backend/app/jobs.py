"""Single background worker that processes uploads one at a time (models are too heavy to run in parallel)."""
from __future__ import annotations

import logging
import queue
import re
import shutil
import threading
import uuid
from pathlib import Path

from .audio import duration_seconds, save_mp3
from .db import Database
from .pipeline import GATE_SETTINGS, extract_vocals
from .separation import MODELS, VocalSeparator

log = logging.getLogger(__name__)


class JobQueue:
    def __init__(self, db: Database, separator_factory, data_dir: Path, tracks_dir: Path):
        self.db = db
        self._separator_factory = separator_factory
        self._separator: VocalSeparator | None = None
        self.data_dir = data_dir
        self.tracks_dir = tracks_dir
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    @property
    def separator(self) -> VocalSeparator:
        # Created lazily so the API starts instantly even though torch is slow to import.
        if self._separator is None:
            self._separator = self._separator_factory()
        return self._separator

    def start(self) -> None:
        self._thread = threading.Thread(target=self._worker, name="acapella-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._thread:
            self._thread.join(timeout=5)

    def submit(self, job_id: str) -> None:
        self._queue.put(job_id)

    def _worker(self) -> None:
        while (job_id := self._queue.get()) is not None:
            try:
                self.process(job_id)
            except Exception as exc:
                log.exception("Job %s failed", job_id)
                self.db.update_job(job_id, status="failed", error=str(exc), message="Failed")

    def process(self, job_id: str) -> None:
        job = self.db.get_job(job_id)
        input_path = Path(job["input_path"])
        self.db.update_job(job_id, status="processing", progress=0.02, message="Loading models")

        def progress(p: float, msg: str) -> None:
            self.db.update_job(job_id, progress=round(p, 3), message=msg)

        separator = self.separator
        track_id = uuid.uuid4().hex
        original = self.data_dir / "originals" / f"{track_id}{input_path.suffix.lower()}"
        mp3: Path | None = None
        try:
            result = extract_vocals(input_path, job["strength"], separator, self.data_dir / "tmp", progress)

            progress(0.95, "Encoding MP3")
            shutil.move(str(input_path), original)
            mp3 = unique_path(self.tracks_dir, safe_filename(job["title"]), ".mp3")
            save_mp3(mp3, result.vocals, result.sample_rate)

            settings = {
                "strength": job["strength"],
                "device": separator.device,
                "steps": result.steps,
                "models": [MODELS.get(m, m) for m in result.models],
                "sample_rate": result.sample_rate,
            }
            if job["strength"] == "high":
                settings["noise_gate"] = GATE_SETTINGS
            track = self.db.create_track(
                track_id, job["title"], duration_seconds(original), settings,
                str(original), str(mp3),
            )
        except Exception:
            for path in (input_path, original, mp3):
                if path:
                    path.unlink(missing_ok=True)
            raise
        self.db.update_job(job_id, status="done", progress=1.0, message="Done", track_id=track["id"])


def safe_filename(title: str) -> str:
    """Turn a track title into a name that is valid on macOS, Windows and Linux."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", title).strip(" .")
    return name[:150] or "Untitled"


def unique_path(folder: Path, stem: str, suffix: str) -> Path:
    """folder/stem.mp3, or folder/stem (2).mp3 etc. if that name is taken."""
    path, n = folder / f"{stem}{suffix}", 2
    while path.exists():
        path, n = folder / f"{stem} ({n}){suffix}", n + 1
    return path
