import os
from pathlib import Path

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}
STRENGTHS = ("low", "medium", "high")


def default_data_dir() -> Path:
    return Path(os.environ.get("ACAPELLA_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))


def default_tracks_dir() -> Path:
    """Finished vocal MP3s, one flat folder at the repo root."""
    return Path(os.environ.get("ACAPELLA_TRACKS_DIR", Path(__file__).resolve().parents[2] / "tracks"))


def cors_origins() -> list[str]:
    raw = os.environ.get("ACAPELLA_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]
