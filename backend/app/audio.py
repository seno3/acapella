"""Audio I/O and DSP helpers used by the vocal pipeline.

All audio arrays are float32 with shape (channels, samples).
"""
from __future__ import annotations

from pathlib import Path

import lameenc
import numpy as np
import soundfile as sf
from scipy.signal import istft, stft


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Load any supported file. Falls back to librosa (ffmpeg) for formats libsndfile can't read, e.g. M4A."""
    path = str(path)
    try:
        data, sr = sf.read(path, dtype="float32", always_2d=True)
        return np.ascontiguousarray(data.T), sr
    except Exception:
        import librosa  # installed with audio-separator; needs ffmpeg for M4A

        data, sr = librosa.load(path, sr=None, mono=False)
        if data.ndim == 1:
            data = data[np.newaxis, :]
        return data.astype(np.float32), int(sr)


def duration_seconds(path: str | Path) -> float:
    try:
        return float(sf.info(str(path)).duration)
    except Exception:
        audio, sr = load_audio(path)
        return audio.shape[1] / sr


def save_wav(path: str | Path, audio: np.ndarray, sr: int) -> None:
    sf.write(str(path), np.clip(audio, -1.0, 1.0).T, sr, subtype="PCM_16")


def save_mp3(path: str | Path, audio: np.ndarray, sr: int, bitrate: int = 320) -> None:
    channels = min(audio.shape[0], 2)
    pcm = (np.clip(audio[:channels], -1.0, 1.0) * 32767).astype(np.int16)
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate)
    encoder.set_in_sample_rate(sr)
    encoder.set_channels(channels)
    encoder.set_quality(2)
    data = encoder.encode(pcm.T.tobytes()) + encoder.flush()
    Path(path).write_bytes(bytes(data))


def match_channels(audio: np.ndarray, channels: int) -> np.ndarray:
    if audio.shape[0] == channels:
        return audio
    if audio.shape[0] == 1:
        return np.repeat(audio, channels, axis=0)
    return np.repeat(audio.mean(axis=0, keepdims=True), channels, axis=0)


def min_magnitude_ensemble(stems: list[np.ndarray], n_fft: int = 4096, hop: int = 1024) -> np.ndarray:
    """Combine vocal stems by keeping, for every time-frequency bin, the one with the smallest magnitude.

    A bin only survives at full level if every model agrees it is vocal, so instrumental bleed that any
    single model rejected gets suppressed. The phase comes from the same model as the kept magnitude.
    """
    if len(stems) == 1:
        return stems[0]
    channels = max(s.shape[0] for s in stems)
    length = min(s.shape[1] for s in stems)
    stems = [match_channels(s, channels)[:, :length] for s in stems]

    out = np.zeros((channels, length), dtype=np.float32)
    for ch in range(channels):
        specs = np.stack([stft(s[ch], nperseg=n_fft, noverlap=n_fft - hop)[2] for s in stems])
        idx = np.argmin(np.abs(specs), axis=0)
        combined = np.take_along_axis(specs, idx[np.newaxis], axis=0)[0]
        _, signal = istft(combined, nperseg=n_fft, noverlap=n_fft - hop)
        n = min(length, signal.shape[0])
        out[ch, :n] = signal[:n]
    return out


def noise_gate(
    audio: np.ndarray,
    sr: int,
    threshold_db: float = -40.0,
    window_ms: float = 20.0,
    hold_ms: float = 120.0,
    lookahead_ms: float = 20.0,
    min_open_ms: float = 60.0,
    attack_ms: float = 5.0,
    release_ms: float = 40.0,
) -> np.ndarray:
    """Silence everything between vocal phrases.

    The threshold is relative to the loudest window of the stem. Closed regions are set to exactly zero;
    short fades are applied only inside open regions so phrase edges don't click.
    """
    n = audio.shape[1]
    if n == 0:
        return audio
    mono = audio.mean(axis=0)
    win = max(1, int(sr * window_ms / 1000))
    hop = max(1, win // 2)
    n_frames = 1 + max(0, (n - win)) // hop
    frames = np.lib.stride_tricks.sliding_window_view(np.pad(mono, (0, win)), win)[::hop][:n_frames]
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1) + 1e-20)
    peak = rms.max()
    if peak <= 1e-9:
        return np.zeros_like(audio)
    open_frames = 20 * np.log10(rms / peak) > threshold_db

    # Keep the gate open for `hold_ms` after the signal drops (bridges dips mid-word) but only open
    # `lookahead_ms` early, so little instrumental sneaks in ahead of each phrase.
    hold = int(round(hold_ms / 1000 * sr / hop))
    lookahead = int(round(lookahead_ms / 1000 * sr / hop))
    open_frames = _dilate(open_frames, before=lookahead, after=hold)

    mask = np.zeros(n, dtype=bool)
    for start, end in _runs(open_frames):
        s, e = start * hop, min(n, (end - 1) * hop + win)
        if (e - s) / sr * 1000 >= min_open_ms:
            mask[s:e] = True

    gain = np.zeros(n, dtype=np.float32)
    attack = int(sr * attack_ms / 1000)
    release = int(sr * release_ms / 1000)
    for s, e in _runs(mask):
        gain[s:e] = 1.0
        length = e - s
        a = min(attack, length // 2)
        r = min(release, length - a)
        if a:
            gain[s : s + a] = np.linspace(0.0, 1.0, a, endpoint=False)
        if r:
            gain[e - r : e] = np.linspace(1.0, 0.0, r, endpoint=False) * gain[e - r : e]
    return audio * gain


def _dilate(mask: np.ndarray, before: int, after: int) -> np.ndarray:
    """Extend each True value `before` frames earlier and `after` frames later."""
    csum = np.concatenate([[0], np.cumsum(mask.astype(np.int64))])
    idx = np.arange(len(mask))
    lo = np.clip(idx - after, 0, len(mask))       # frame i is open if any True in [i-after, i+before]
    hi = np.clip(idx + before + 1, 0, len(mask))
    return (csum[hi] - csum[lo]) > 0


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) index pairs of consecutive True values."""
    padded = np.concatenate([[False], mask.astype(bool), [False]])
    edges = np.flatnonzero(np.diff(padded.astype(np.int8)))
    return list(zip(edges[::2], edges[1::2]))
