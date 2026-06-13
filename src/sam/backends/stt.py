"""Speech-in. Stub reads stdin lines (headless/testable). Parakeet is the real
CPU path — the same onnx-asr int8 lineage Diana settled on (~245ms, GPU-free).

ParakeetSTT adds the one thing Diana's socket server doesn't: live mic capture
(via `arecord` — no PortAudio dep) with energy-based VAD segmentation. It reuses
Diana's pre-downloaded int8 model dir so SAM never re-fetches 660MB.

Design split for testability (no mic needed in tests):
  transcribe_array(audio) — pure model call on a float32 mono 16k array
  _segment(frames)        — VAD state machine, frames in → utterance arrays out
  listen()                — wires the live mic stream into the two above
"""

from __future__ import annotations

import os
import sys
import wave
from collections import deque
from typing import Iterable, Iterator, Protocol


class STT(Protocol):
    def listen(self) -> Iterator[str]: ...


class StdinSTT:
    """Headless default: each line typed (or piped) is one 'utterance'."""

    def listen(self) -> Iterator[str]:
        for line in sys.stdin:
            line = line.strip()
            if line:
                yield line


def _envf(key: str, default: str) -> float:
    return float(os.environ.get(key, default))


def _envi(key: str, default: str) -> int:
    return int(os.environ.get(key, default))


class ParakeetSTT:
    """parakeet-tdt-0.6b-v2 int8 over onnx-asr, CPU. Live mic + energy VAD.

    Reuses Diana's local int8 model dir if present, else pulls from HF by name.
    All capture/VAD knobs are env-overridable; defaults suit a quiet laptop mic.
    """

    SAMPLE_RATE = 16000
    FRAME_MS = 30  # 480 samples/frame at 16k

    def __init__(self) -> None:
        import numpy as np  # lazy: stub mode never imports these
        import onnx_asr

        self._np = np
        self._frame = int(self.SAMPLE_RATE * self.FRAME_MS / 1000)

        # VAD tuning (env-overridable).
        self._rms_threshold = _envf("SAM_VAD_RMS", "0.012")     # float32 RMS gate
        self._silence_ms = _envi("SAM_VAD_SILENCE_MS", "700")   # trailing silence → end
        self._min_ms = _envi("SAM_VAD_MIN_MS", "300")           # ignore blips
        self._max_ms = _envi("SAM_VAD_MAX_MS", "15000")         # hard utterance cap
        self._preroll_frames = max(1, _envi("SAM_VAD_PREROLL_MS", "210") // self.FRAME_MS)

        self._model = self._load(onnx_asr)

    # ── model ────────────────────────────────────────────────────────────────
    def _load(self, onnx_asr):
        """Prefer Diana's pre-downloaded int8 dir; fall back to an HF pull."""
        name = os.environ.get("SAM_STT_MODEL", "parakeet-tdt-0.6b-v2")
        local = os.environ.get(
            "SAM_STT_MODEL_DIR",
            os.path.expanduser(f"~/.local/share/diana/models/{name}-onnx"),
        )
        if os.path.exists(os.path.join(local, "encoder-model.int8.onnx")):
            print(f"SAM stt: onnx-asr {local} int8 (cpu)", file=sys.stderr, flush=True)
            return onnx_asr.load_model("nemo-conformer-tdt", local, quantization="int8")
        hf = name if name.startswith("nemo-") else f"nemo-{name}"
        print(f"SAM stt: onnx-asr {hf} int8 (cpu, HF)", file=sys.stderr, flush=True)
        return onnx_asr.load_model(hf, quantization="int8")

    def transcribe_array(self, audio) -> str:
        """Recognize a float32 mono 16k array. Falls back to a temp wav if the
        model rejects the in-memory array (no silent failure — logged)."""
        try:
            return (self._model.recognize(audio, sample_rate=self.SAMPLE_RATE) or "").strip()
        except Exception as e:  # noqa: BLE001
            print(f"SAM stt: array recognize failed ({type(e).__name__}: {str(e)[:60]}) "
                  f"— retrying via temp wav", file=sys.stderr, flush=True)
        try:
            path = self._to_wav(audio)
            try:
                return (self._model.recognize(path) or "").strip()
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        except Exception as e:  # noqa: BLE001
            print(f"SAM stt: transcribe FAILED ({type(e).__name__}: {str(e)[:60]})",
                  file=sys.stderr, flush=True)
            return ""

    def _to_wav(self, audio) -> str:
        import tempfile

        np = self._np
        pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="sam-stt-")
        os.close(fd)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.SAMPLE_RATE)
            w.writeframes(pcm.tobytes())
        return path

    # ── VAD ──────────────────────────────────────────────────────────────────
    def _segment(self, frames: Iterable):
        """Energy VAD: yield one float32 array per detected utterance.

        Pre-roll keeps a short silence tail before onset so word starts aren't
        clipped; an utterance ends after `silence_ms` of quiet (or `max_ms`).
        """
        np = self._np
        preroll: deque = deque(maxlen=self._preroll_frames)
        voiced: list = []
        in_speech = False
        trailing_silence = 0  # frames

        for frame in frames:
            rms = float(np.sqrt(np.mean(np.square(frame))) + 1e-9)
            loud = rms >= self._rms_threshold
            if not in_speech:
                preroll.append(frame)
                if loud:
                    in_speech = True
                    voiced = list(preroll)
                    preroll.clear()
                    trailing_silence = 0
                continue
            voiced.append(frame)
            trailing_silence = 0 if loud else trailing_silence + 1
            total_ms = len(voiced) * self.FRAME_MS
            ended = trailing_silence * self.FRAME_MS >= self._silence_ms
            if ended or total_ms >= self._max_ms:
                speech_ms = total_ms - trailing_silence * self.FRAME_MS
                in_speech, audio = False, np.concatenate(voiced)
                voiced, trailing_silence = [], 0
                if speech_ms >= self._min_ms:
                    yield audio

        # Stream ended mid-utterance (finite input / shutdown) → flush the tail
        # so the last thing said is never silently dropped.
        if in_speech and voiced:
            speech_ms = len(voiced) * self.FRAME_MS - trailing_silence * self.FRAME_MS
            if speech_ms >= self._min_ms:
                yield np.concatenate(voiced)

    # ── live mic ───────────────────────────────────────────────────────────--
    def _mic_frames(self):
        """Capture via `arecord` (ALSA) — no PortAudio/native python dep, and the
        binary is already on every desktop. Yields float32 mono 16k frames."""
        import subprocess

        np = self._np
        device = os.environ.get("SAM_MIC_DEVICE", "default")
        cmd = ["arecord", "-q", "-D", device, "-f", "S16_LE", "-c", "1",
               "-r", str(self.SAMPLE_RATE), "-t", "raw"]
        nbytes = self._frame * 2  # int16 = 2 bytes/sample
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        assert proc.stdout
        print(f"SAM stt: mic open (arecord {device}) — listening", file=sys.stderr, flush=True)
        try:
            while True:
                buf = self._read_exact(proc.stdout, nbytes)
                if buf is None:
                    break  # arecord died / EOF
                yield np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    @staticmethod
    def _read_exact(stream, n: int) -> bytes | None:
        """Pipes hand back short reads — loop until we have a full frame or EOF."""
        buf = b""
        while len(buf) < n:
            chunk = stream.read(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def listen(self) -> Iterator[str]:
        for utterance in self._segment(self._mic_frames()):
            text = self.transcribe_array(utterance)
            if text:
                yield text


def build(cfg) -> STT:
    return ParakeetSTT() if cfg.stt_backend == "parakeet" else StdinSTT()
