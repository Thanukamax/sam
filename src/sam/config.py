"""SAM configuration — env-overridable, sane CPU-only defaults.

Every knob is an env var so the systemd unit can set them without a config file.
Defaults are chosen for the battery envelope: a 1.5B reasoner, CPU-forced.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Config:
    # Reasoner backend: "stub" (no deps, heuristic routing) or "ollama".
    llm_backend: str = _env("SAM_LLM", "stub")
    # Small, tool-capable, fits the battery budget. Present on this box already.
    llm_model: str = _env("SAM_MODEL", "qwen2.5:1.5b")
    ollama_host: str = _env("SAM_OLLAMA_HOST", "http://127.0.0.1:11434")

    # Speech: "stub" prints text (headless-friendly, no audio deps).
    stt_backend: str = _env("SAM_STT", "stub")
    tts_backend: str = _env("SAM_TTS", "stub")

    # Hard CPU-only contract: forbid GPU layers in the reasoner. The whole point.
    cpu_only: bool = _env("SAM_CPU_ONLY", "1") == "1"

    # Tool-loop safety bound.
    max_steps: int = int(_env("SAM_MAX_STEPS", "4"))


def load() -> Config:
    return Config()
