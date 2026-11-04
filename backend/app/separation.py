"""Wrapper around the `audio-separator` package.

The pipeline only depends on the small `VocalSeparator` protocol, so tests can swap in a fake.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Protocol

import numpy as np

from .audio import load_audio

log = logging.getLogger(__name__)

# Model keys used by the pipeline -> model filenames known to audio-separator. Override with env vars.
MODELS = {
    "mel_roformer": os.environ.get("ACAPELLA_PRIMARY_MODEL", "vocals_mel_band_roformer.ckpt"),
    "bs_roformer": os.environ.get("ACAPELLA_SECONDARY_MODEL", "model_bs_roformer_ep_317_sdr_12.9755.ckpt"),
    "htdemucs": os.environ.get("ACAPELLA_FALLBACK_MODEL", "htdemucs_ft.yaml"),
}
FALLBACK_KEY = "htdemucs"


class VocalSeparator(Protocol):
    device: str

    def separate(self, input_path: Path, model_key: str) -> tuple[np.ndarray, int, str]:
        """Return (vocals, sample_rate, model_key_actually_used)."""
        ...


def detect_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:  # torch missing or broken -> CPU
        pass
    return "cpu"


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


class AudioSeparatorBackend:
    """Runs models through audio-separator, loading each model once and keeping it in memory.

    If a model fails to load or run, it retries with the HT-Demucs fallback. If the GPU fails mid-run
    (out of memory, unsupported op), it retries the same model on CPU.
    """

    def __init__(self, model_dir: Path, work_dir: Path):
        self.model_dir = Path(model_dir)
        self.work_dir = Path(work_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.device = detect_device()
        self._separators: dict[tuple[str, bool], object] = {}
        self._lock = threading.Lock()

    def separate(self, input_path: Path, model_key: str) -> tuple[np.ndarray, int, str]:
        if not ffmpeg_available():
            raise RuntimeError("ffmpeg is not installed or not on PATH. Install it (e.g. `brew install ffmpeg`).")
        with self._lock:
            keys = [model_key] if model_key == FALLBACK_KEY else [model_key, FALLBACK_KEY]
            last_error: Exception | None = None
            for key in keys:
                for force_cpu in ((False, True) if self.device != "cpu" else (True,)):
                    try:
                        audio, sr = self._run(input_path, key, force_cpu)
                        return audio, sr, key
                    except Exception as exc:  # try the next option
                        last_error = exc
                        log.warning("Separation with %s (cpu=%s) failed: %s", key, force_cpu, exc)
                        self._separators.pop((key, force_cpu), None)
            raise RuntimeError(f"All separation models failed: {last_error}") from last_error

    def _get_separator(self, key: str, force_cpu: bool):
        cache_key = (key, force_cpu)
        if cache_key not in self._separators:
            from audio_separator.separator import Separator

            sep = Separator(
                log_level=logging.WARNING,
                model_file_dir=str(self.model_dir),
                output_dir=str(self.work_dir),
                output_format="WAV",
                output_single_stem="Vocals",
            )
            if force_cpu:
                import torch

                sep.torch_device = torch.device("cpu")
                sep.torch_device_mps = None
                sep.onnx_execution_provider = ["CPUExecutionProvider"]
            sep.load_model(model_filename=MODELS[key])
            self._separators[cache_key] = sep
        return self._separators[cache_key]

    def _run(self, input_path: Path, key: str, force_cpu: bool) -> tuple[np.ndarray, int]:
        sep = self._get_separator(key, force_cpu)
        out_dir = Path(tempfile.mkdtemp(dir=self.work_dir))
        try:
            sep.output_dir = str(out_dir)
            if getattr(sep, "model_instance", None) is not None:
                sep.model_instance.output_dir = str(out_dir)
            outputs = [Path(p) if Path(p).is_absolute() else out_dir / p for p in sep.separate(str(input_path))]
            vocals = [p for p in outputs if "vocals" in p.name.lower()] or outputs
            if not vocals:
                raise RuntimeError("audio-separator produced no output")
            return load_audio(vocals[0])
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)
