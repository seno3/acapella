"""Isolation-strength logic. Biased toward removing instrumental bleed, even at some cost to vocal quality."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from .audio import min_magnitude_ensemble, noise_gate, save_wav
from .separation import VocalSeparator

PRIMARY = "mel_roformer"
SECONDARY = "bs_roformer"

GATE_SETTINGS = {"threshold_db": -40.0, "hold_ms": 120.0, "lookahead_ms": 20.0, "min_open_ms": 60.0}

ProgressFn = Callable[[float, str], None]


@dataclass
class PipelineResult:
    vocals: np.ndarray
    sample_rate: int
    steps: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)


def extract_vocals(
    input_path: Path,
    strength: str,
    separator: VocalSeparator,
    work_dir: Path,
    progress: ProgressFn = lambda p, m: None,
) -> PipelineResult:
    if strength not in ("low", "medium", "high"):
        raise ValueError(f"Unknown strength: {strength}")

    passes = {"low": 1, "medium": 2, "high": 3}[strength]
    done = 0

    def run(path: Path, key: str, label: str) -> tuple[np.ndarray, int]:
        nonlocal done
        progress(0.05 + 0.85 * done / passes, label)
        audio, sr, used = separator.separate(path, key)
        result.models.append(used)
        done += 1
        return audio, sr

    result = PipelineResult(vocals=np.zeros((1, 0), np.float32), sample_rate=44100)

    vocals, sr = run(input_path, PRIMARY, "Separating vocals")
    result.steps.append(f"separate:{result.models[-1]}")

    if strength in ("medium", "high"):
        second, sr2 = run(input_path, SECONDARY, "Running second model")
        if sr2 != sr:
            raise RuntimeError(f"Sample rate mismatch between models ({sr} vs {sr2})")
        vocals = min_magnitude_ensemble([vocals, second])
        result.steps.append(f"ensemble_min:{result.models[-1]}")

    if strength == "high":
        with tempfile.TemporaryDirectory(dir=work_dir) as tmp:
            stem_path = Path(tmp) / "vocals_pass1.wav"
            save_wav(stem_path, vocals, sr)
            vocals, _ = run(stem_path, PRIMARY, "Re-separating vocal stem")
        result.steps.append(f"second_pass:{result.models[-1]}")
        progress(0.92, "Gating silence between phrases")
        vocals = noise_gate(vocals, sr, **GATE_SETTINGS)
        result.steps.append("noise_gate")

    result.vocals = vocals.astype(np.float32)
    result.sample_rate = sr
    return result
