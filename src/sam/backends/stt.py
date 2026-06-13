"""Speech-in. Stub reads stdin lines (headless/testable). Parakeet is the real
CPU path — the same onnx-asr int8 lineage Diana settled on (~245ms, GPU-free).

The real backend is a documented stub here: wiring a live mic capture + VAD is
the first real-work task once the scaffold is accepted. Keeping it explicit so
nobody mistakes the placeholder for a finished feature.
"""

from __future__ import annotations

import sys
from typing import Iterator, Protocol


class STT(Protocol):
    def listen(self) -> Iterator[str]: ...


class StdinSTT:
    """Headless default: each line typed (or piped) is one 'utterance'."""

    def listen(self) -> Iterator[str]:
        for line in sys.stdin:
            line = line.strip()
            if line:
                yield line


class ParakeetSTT:
    """parakeet-tdt-0.6b-v2 int8 over onnx-asr, CPU. NOT YET IMPLEMENTED.

    Plan (inherits Diana's proven config):
      - onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", quantization="int8")
      - sounddevice mic capture + simple energy VAD for utterance boundaries
      - transcribe each segment, yield text
    """

    def listen(self) -> Iterator[str]:
        raise NotImplementedError(
            "ParakeetSTT not wired yet — install the 'voice' extra and implement "
            "mic capture. Use SAM_STT=stub for now."
        )


def build(cfg) -> STT:
    return ParakeetSTT() if cfg.stt_backend == "parakeet" else StdinSTT()
