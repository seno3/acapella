from __future__ import annotations

import re
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import ALLOWED_EXTENSIONS, STRENGTHS, cors_origins, default_data_dir, default_tracks_dir
from .db import Database
from .jobs import JobQueue
from .separation import AudioSeparatorBackend, detect_device, ffmpeg_available

MEDIA_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac", ".m4a": "audio/mp4"}


def create_app(data_dir: Path | None = None, separator_factory=None, tracks_dir: Path | None = None) -> FastAPI:
    data_dir = Path(data_dir or default_data_dir())
    tracks_dir = Path(tracks_dir or default_tracks_dir())
    for sub in ("uploads", "originals", "tmp", "models"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)
    tracks_dir.mkdir(parents=True, exist_ok=True)

    db = Database(data_dir / "acapella.db")
    factory = separator_factory or (lambda: AudioSeparatorBackend(data_dir / "models", data_dir / "tmp"))
    jobs = JobQueue(db, factory, data_dir, tracks_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        jobs.start()
        yield
        jobs.stop()

    app = FastAPI(title="Acapella", lifespan=lifespan)
    app.state.db, app.state.jobs = db, jobs
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["*"], allow_headers=["*"])

    def track_out(t: dict) -> dict:
        base = f"/api/tracks/{t['id']}/audio"
        return {
            "id": t["id"],
            "title": t["title"],
            "duration": t["duration"],
            "settings": t["settings"],
            "created_at": t["created_at"],
            "audio": {"original": f"{base}/original", "vocals_mp3": f"{base}/vocals_mp3"},
        }

    def job_out(j: dict) -> dict:
        return {k: j[k] for k in ("id", "title", "strength", "status", "progress", "message", "error",
                                  "track_id", "created_at")}

    @app.get("/api/health")
    def health():
        return {"ok": True, "device": detect_device(), "ffmpeg": ffmpeg_available()}

    @app.post("/api/upload", status_code=202)
    async def upload(file: UploadFile = File(...), strength: str = Form("medium"), title: str | None = Form(None)):
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type. Use one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        if strength not in STRENGTHS:
            raise HTTPException(400, f"strength must be one of {STRENGTHS}")
        dest = data_dir / "uploads" / f"{uuid.uuid4().hex}{ext}"
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out, length=1024 * 1024)
        if dest.stat().st_size == 0:
            dest.unlink()
            raise HTTPException(400, "Uploaded file is empty")
        name = (title or "").strip() or _title_from_filename(file.filename or "Untitled")
        job = db.create_job(name, strength, str(dest))
        jobs.submit(job["id"])
        return job_out(job)

    @app.get("/api/jobs")
    def list_jobs(active: bool = False):
        return [job_out(j) for j in db.list_jobs(active_only=active)]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        job = db.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return job_out(job)

    @app.get("/api/tracks")
    def list_tracks():
        return [track_out(t) for t in db.list_tracks()]

    @app.get("/api/tracks/{track_id}")
    def get_track(track_id: str):
        track = db.get_track(track_id)
        if not track:
            raise HTTPException(404, "Track not found")
        return track_out(track)

    @app.get("/api/tracks/{track_id}/audio/{kind}")
    def get_audio(track_id: str, kind: str, download: bool = False):
        track = db.get_track(track_id)
        column = {"original": "original_path", "vocals_mp3": "vocals_path"}
        if not track or kind not in column:
            raise HTTPException(404, "Not found")
        path = Path(track[column[kind]])
        if not path.exists():
            raise HTTPException(404, "File missing")
        # Vocals download under the same name they have in the tracks folder.
        filename = (f"{track['title']}{path.suffix}" if kind == "original" else path.name) if download else None
        return FileResponse(path, media_type=MEDIA_TYPES.get(path.suffix, "application/octet-stream"),
                            filename=filename)

    @app.delete("/api/tracks/{track_id}", status_code=204)
    def delete_track(track_id: str):
        track = db.get_track(track_id)
        if not track:
            raise HTTPException(404, "Track not found")
        db.delete_track(track_id)
        Path(track["original_path"]).unlink(missing_ok=True)
        Path(track["vocals_path"]).unlink(missing_ok=True)

    return app


def _title_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[_]+", " ", stem).strip() or "Untitled"

