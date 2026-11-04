import numpy as np

from app.audio import duration_seconds, load_audio, min_magnitude_ensemble, noise_gate, save_mp3, save_wav
from tests.conftest import BASS_HZ, DURATION, GAP, HAT_HZ, PHRASES, SR, VOCAL_HZ, band_energy, make_bass, make_hat, make_vocal


def test_wav_roundtrip(tmp_path):
    audio = make_vocal()
    path = tmp_path / "a.wav"
    save_wav(path, audio, SR)
    loaded, sr = load_audio(path)
    assert sr == SR
    assert loaded.shape == audio.shape
    assert np.max(np.abs(loaded - audio)) < 1e-3
    assert abs(duration_seconds(path) - DURATION) < 1e-3


def test_mp3_encode(tmp_path):
    path = tmp_path / "a.mp3"
    save_mp3(path, make_vocal(), SR)
    data = path.read_bytes()
    assert len(data) > 10_000
    # Starts with an MPEG frame sync or an ID3 tag.
    assert data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0)
    loaded, sr = load_audio(path)  # libsndfile >= 1.1 decodes MP3
    assert sr == SR
    assert abs(loaded.shape[1] / sr - DURATION) < 0.1


def test_min_ensemble_removes_leakage_from_each_model():
    vocal = make_vocal()
    a = vocal + 0.3 * make_bass()
    b = vocal + 0.3 * make_hat()
    out = min_magnitude_ensemble([a, b])

    assert out.shape == vocal.shape
    # Each model's leak is suppressed by at least 20 dB...
    assert band_energy(out, BASS_HZ) < band_energy(a, BASS_HZ) / 100
    assert band_energy(out, HAT_HZ) < band_energy(b, HAT_HZ) / 100
    # ...while the vocal they agree on is kept (within 1 dB).
    assert band_energy(out, VOCAL_HZ) > band_energy(vocal, VOCAL_HZ) * 0.8


def test_min_ensemble_handles_length_and_channel_mismatch():
    vocal = make_vocal()
    mono_short = vocal[:1, :-500]
    out = min_magnitude_ensemble([vocal, mono_short])
    assert out.shape == (2, vocal.shape[1] - 500)


def test_noise_gate_silences_gaps_and_keeps_phrases():
    rng = np.random.default_rng(0)
    noisy = make_vocal() + 0.002 * rng.standard_normal(make_vocal().shape).astype(np.float32)
    gated = noise_gate(noisy, SR)

    gap = slice(int(GAP[0] * SR), int(GAP[1] * SR))
    assert np.all(gated[:, gap] == 0.0)
    assert np.all(gated[:, : int(0.2 * SR)] == 0.0)  # leading silence
    for start, end in PHRASES:
        middle = slice(int((start + 0.1) * SR), int((end - 0.1) * SR))
        np.testing.assert_allclose(gated[:, middle], noisy[:, middle])


def test_noise_gate_holds_through_short_dips():
    audio = make_vocal()
    dip = slice(int(0.7 * SR), int(0.75 * SR))  # 50 ms dip inside a phrase
    audio[:, dip] = 0.0
    audio[:, dip.stop : dip.stop + 10] = 0.3  # sharp re-entry
    gated = noise_gate(audio, SR)
    after = slice(dip.stop + 100, dip.stop + 2000)
    np.testing.assert_allclose(gated[:, after], audio[:, after])


def test_noise_gate_on_silence_returns_zeros():
    assert not noise_gate(np.zeros((2, SR), np.float32), SR).any()
