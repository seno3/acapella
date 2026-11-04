import time

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import DURATION, FakeSeparator


@pytest.fixture
def client(tmp_path):
    separator = FakeSeparator()  # no mix path: every input is treated as already-separated
    app = create_app(tmp_path / "data", separator_factory=lambda: separator, tracks_dir=tmp_path / "tracks")
    with TestClient(app) as c:
        yield c


def wait_for(client, job_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise TimeoutError(job)


@pytest.mark.parametrize("strength", ["low", "medium", "high"])
def test_upload_process_and_library(client, mix_file, strength, tmp_path):
    with mix_file.open("rb") as f:
        r = client.post("/api/upload", files={"file": ("My_Song.wav", f, "audio/wav")}, data={"strength": strength})
    assert r.status_code == 202, r.text
    job = wait_for(client, r.json()["id"])
    assert job["status"] == "done", job
    assert job["progress"] == 1.0

    tracks = client.get("/api/tracks").json()
    assert len(tracks) == 1
    track = tracks[0]
    assert track["id"] == job["track_id"]
    assert track["title"] == "My Song"
    assert abs(track["duration"] - DURATION) < 0.01
    assert track["settings"]["strength"] == strength

    # Only the vocal MP3 lands in the flat tracks folder, named after the song.
    assert [p.name for p in (tmp_path / "tracks").iterdir()] == ["My Song.mp3"]
    download = client.get(track["audio"]["vocals_mp3"], params={"download": "true"})
    assert download.headers["content-disposition"].endswith("My%20Song.mp3")

    for kind in ("original", "vocals_mp3"):
        audio = client.get(track["audio"][kind])
        assert audio.status_code == 200
        assert len(audio.content) > 1000
    assert client.get(track["audio"]["vocals_mp3"]).headers["content-type"] == "audio/mpeg"

    # Range requests are needed for seeking in the browser.
    partial = client.get(track["audio"]["vocals_mp3"], headers={"Range": "bytes=0-99"})
    assert partial.status_code == 206 and len(partial.content) == 100

    assert client.delete(f"/api/tracks/{track['id']}").status_code == 204
    assert client.get("/api/tracks").json() == []
    assert list((tmp_path / "tracks").iterdir()) == []
    assert list((tmp_path / "data" / "originals").iterdir()) == []


def test_rejects_unsupported_file(client):
    r = client.post("/api/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_rejects_bad_strength(client, mix_file):
    r = client.post("/api/upload", files={"file": ("a.wav", mix_file.read_bytes(), "audio/wav")},
                    data={"strength": "max"})
    assert r.status_code == 400


def test_failed_job_reports_error(tmp_path, mix_file):
    separator = FakeSeparator(fail={"mel_roformer"})
    app = create_app(tmp_path / "data", separator_factory=lambda: separator, tracks_dir=tmp_path / "tracks")
    with TestClient(app) as c:
        r = c.post("/api/upload", files={"file": ("a.wav", mix_file.read_bytes(), "audio/wav")})
        job = wait_for(c, r.json()["id"])
    assert job["status"] == "failed"
    assert "boom" in job["error"]


def test_unknown_job_404(client):
    assert client.get("/api/jobs/nope").status_code == 404


def test_same_title_gets_numbered_name(client, mix_file, tmp_path):
    for _ in range(2):
        r = client.post("/api/upload", files={"file": ("My_Song.wav", mix_file.read_bytes(), "audio/wav")})
        assert wait_for(client, r.json()["id"])["status"] == "done"
    assert sorted(p.name for p in (tmp_path / "tracks").iterdir()) == ["My Song (2).mp3", "My Song.mp3"]


def test_safe_filename():
    from app.jobs import safe_filename
    assert safe_filename('AC/DC: "Back"?') == "ACDC Back"
    assert safe_filename(" ... ") == "Untitled"
