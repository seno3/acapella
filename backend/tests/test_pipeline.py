import numpy as np
import pytest

from app.pipeline import extract_vocals
from app.separation import AudioSeparatorBackend
from tests.conftest import BASS_HZ, GAP, HAT_HZ, PHRASES, SR, VOCAL_HZ, band_energy, make_hat, make_vocal


def test_low_uses_single_model(mix_file, fake_separator, tmp_path):
    result = extract_vocals(mix_file, "low", fake_separator, tmp_path)
    assert [k for _, k in fake_separator.calls] == ["mel_roformer"]
    assert result.sample_rate == SR
    # Single model output still has that model's bass bleed.
    assert band_energy(result.vocals, BASS_HZ) > band_energy(make_vocal(), BASS_HZ) * 100


def test_medium_ensembles_two_models(mix_file, fake_separator, tmp_path):
    low = extract_vocals(mix_file, "low", fake_separator, tmp_path).vocals
    fake_separator.calls.clear()
    medium = extract_vocals(mix_file, "medium", fake_separator, tmp_path)

    assert [k for _, k in fake_separator.calls] == ["mel_roformer", "bs_roformer"]
    assert band_energy(medium.vocals, BASS_HZ) < band_energy(low, BASS_HZ) / 100
    assert band_energy(medium.vocals, HAT_HZ) < band_energy(make_vocal() + 0.3 * make_hat(), HAT_HZ) / 100
    assert band_energy(medium.vocals, VOCAL_HZ) > band_energy(make_vocal(), VOCAL_HZ) * 0.8


def test_high_adds_second_pass_and_gate(mix_file, fake_separator, tmp_path):
    progress = []
    result = extract_vocals(mix_file, "high", fake_separator, tmp_path, lambda p, m: progress.append(p))

    keys = [k for _, k in fake_separator.calls]
    assert keys == ["mel_roformer", "bs_roformer", "mel_roformer"]
    second_pass_input = fake_separator.calls[2][0]
    assert second_pass_input != mix_file
    assert not second_pass_input.exists()  # temp file cleaned up
    assert result.steps[-1] == "noise_gate"

    vocals = result.vocals
    gap = slice(int(GAP[0] * SR), int(GAP[1] * SR))
    assert np.all(vocals[:, gap] == 0.0), "gaps between phrases must be fully silent"
    for start, end in PHRASES:
        mid = slice(int((start + 0.1) * SR), int((end - 0.1) * SR))
        assert np.sqrt(np.mean(vocals[:, mid] ** 2)) > 0.1
    assert progress == sorted(progress)


def test_unknown_strength_rejected(mix_file, fake_separator, tmp_path):
    with pytest.raises(ValueError):
        extract_vocals(mix_file, "extreme", fake_separator, tmp_path)


def test_backend_falls_back_to_htdemucs(tmp_path, monkeypatch):
    monkeypatch.setattr("app.separation.ffmpeg_available", lambda: True)
    backend = AudioSeparatorBackend(tmp_path / "models", tmp_path / "work")
    backend.device = "cpu"
    tried = []

    def fake_run(path, key, force_cpu):
        tried.append((key, force_cpu))
        if key != "htdemucs":
            raise RuntimeError("model download failed")
        return make_vocal(), SR

    monkeypatch.setattr(backend, "_run", fake_run)
    _, _, used = backend.separate(tmp_path / "x.wav", "mel_roformer")
    assert used == "htdemucs"
    assert tried == [("mel_roformer", True), ("htdemucs", True)]


def test_backend_retries_on_cpu_when_gpu_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("app.separation.ffmpeg_available", lambda: True)
    backend = AudioSeparatorBackend(tmp_path / "models", tmp_path / "work")
    backend.device = "cuda"
    tried = []

    def fake_run(path, key, force_cpu):
        tried.append((key, force_cpu))
        if not force_cpu:
            raise RuntimeError("CUDA out of memory")
        return make_vocal(), SR

    monkeypatch.setattr(backend, "_run", fake_run)
    _, _, used = backend.separate(tmp_path / "x.wav", "mel_roformer")
    assert used == "mel_roformer"
    assert tried == [("mel_roformer", False), ("mel_roformer", True)]


def test_backend_reports_missing_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr("app.separation.ffmpeg_available", lambda: False)
    backend = AudioSeparatorBackend(tmp_path / "models", tmp_path / "work")
    with pytest.raises(RuntimeError, match="ffmpeg"):
        backend.separate(tmp_path / "x.wav", "mel_roformer")
