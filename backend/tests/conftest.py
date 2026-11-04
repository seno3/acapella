"""Shared fixtures: a short synthetic "song" and a fake separator, so tests never download models."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.audio import load_audio, save_wav

SR = 44100
DURATION = 3.0
# Vocal phrases (seconds). The gap between them must end up silent at "high" strength.
PHRASES = [(0.3, 1.2), (1.8, 2.7)]
GAP = (1.35, 1.65)

VOCAL_HZ = 440.0
BASS_HZ = 110.0
HAT_HZ = 3000.0


def _t() -> np.ndarray:
    return np.arange(int(SR * DURATION)) / SR


def make_vocal() -> np.ndarray:
    t = _t()
    tone = 0.3 * np.sin(2 * np.pi * VOCAL_HZ * t) + 0.1 * np.sin(2 * np.pi * 2 * VOCAL_HZ * t)
    env = np.zeros_like(t)
    for start, end in PHRASES:
        env[(t >= start) & (t < end)] = 1.0
    return np.stack([tone * env] * 2).astype(np.float32)


def make_bass() -> np.ndarray:
    return np.stack([0.3 * np.sin(2 * np.pi * BASS_HZ * _t())] * 2).astype(np.float32)


def make_hat() -> np.ndarray:
    return np.stack([0.2 * np.sin(2 * np.pi * HAT_HZ * _t())] * 2).astype(np.float32)


def band_energy(audio: np.ndarray, hz: float, sr: int = SR, width: float = 20.0) -> float:
    spectrum = np.abs(np.fft.rfft(audio.mean(axis=0)))
    freqs = np.fft.rfftfreq(audio.shape[1], 1 / sr)
    return float(np.sum(spectrum[(freqs > hz - width) & (freqs < hz + width)] ** 2))


class FakeSeparator:
    """Each "model" leaks a different instrument into its vocal stem, like real models do.

    mel_roformer leaks bass, bs_roformer leaks hi-hat. Separating anything other than the original
    mix (the high-strength second pass) halves whatever isn't the vocal.
    """

    device = "cpu"

    def __init__(self, mix_path: Path | None = None, fail: set[str] | None = None):
        self.mix_path = mix_path
        self.calls: list[tuple[Path, str]] = []
        self.fail = fail or set()

    def separate(self, input_path: Path, model_key: str):
        self.calls.append((Path(input_path), model_key))
        if model_key in self.fail:
            raise RuntimeError("boom")
        audio, sr = load_audio(input_path)
        vocal = make_vocal()
        if self.mix_path is None or Path(input_path) != self.mix_path:
            # Second pass on an existing vocal stem: keep the vocal, reduce the rest.
            residual = audio[:, : vocal.shape[1]] - vocal[:, : audio.shape[1]]
            return vocal[:, : audio.shape[1]] + 0.5 * residual, sr, model_key
        leak = make_bass() if model_key == "mel_roformer" else make_hat()
        return vocal + 0.3 * leak, sr, model_key


@pytest.fixture
def mix_file(tmp_path: Path) -> Path:
    path = tmp_path / "mix.wav"
    save_wav(path, make_vocal() + make_bass() + make_hat(), SR)
    return path


@pytest.fixture
def fake_separator(mix_file: Path) -> FakeSeparator:
    return FakeSeparator(mix_file)
