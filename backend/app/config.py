import os
from pathlib import Path

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}
STRENGTHS = ("low", "medium", "high")


def default_data_dir() -> Path:
    return Path(os.environ.get("ACAPELLA_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))


def cors_origins() -> list[str]:
    raw = os.environ.get("ACAPELLA_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]
