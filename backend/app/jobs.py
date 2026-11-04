"""Single background worker that processes uploads one at a time (models are too heavy to run in parallel)."""
from __future__ import annotations

import logging
import queue
import shutil
import threading
import uuid
from pathlib import Path

from .audio import duration_seconds, save_mp3, save_wav
from .db import Database
from .pipeline import GATE_SETTINGS, extract_vocals
from .separation import MODELS, VocalSeparator

log = logging.getLogger(__name__)


class JobQueue:
    def __init__(self, db: Database, separator_factory, data_dir: Path):
        self.db = db
        self._separator_factory = separator_factory
        self._separator: VocalSeparator | None = None
        self.data_dir = data_dir
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
        track_dir = self.data_dir / "tracks" / track_id
        track_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = extract_vocals(input_path, job["strength"], separator, self.data_dir / "tmp", progress)

            progress(0.95, "Encoding WAV and MP3")
            original = track_dir / f"original{input_path.suffix.lower()}"
            shutil.move(str(input_path), original)
            wav, mp3 = track_dir / "vocals.wav", track_dir / "vocals.mp3"
            save_wav(wav, result.vocals, result.sample_rate)
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
                str(original), str(wav), str(mp3),
            )
        except Exception:
            shutil.rmtree(track_dir, ignore_errors=True)
            input_path.unlink(missing_ok=True)
            raise
        self.db.update_job(job_id, status="done", progress=1.0, message="Done", track_id=track["id"])
