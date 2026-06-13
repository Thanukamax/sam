"""Voice-path tests: the Parakeet VAD segmenter.

Skipped automatically when the voice extra or Diana's int8 model dir is absent,
so the core stub suite still runs anywhere. These need numpy + onnx-asr + the
model (ParakeetSTT loads it in __init__), but exercise NO microphone — frames
are synthesised, so the state machine is tested deterministically.
"""

from __future__ import annotations

import os

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("onnx_asr")

_MODEL = os.path.expanduser("~/.local/share/diana/models/parakeet-tdt-0.6b-v2-onnx")
pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(_MODEL, "encoder-model.int8.onnx")),
    reason="parakeet int8 model dir not present",
)

from sam.backends.stt import ParakeetSTT  # noqa: E402


@pytest.fixture(scope="module")
def stt() -> ParakeetSTT:
    return ParakeetSTT()


def _loud(stt: ParakeetSTT, n_frames: int) -> list:
    fr = stt._frame
    tone = 0.1 * np.sin(2 * np.pi * 220 * np.arange(fr * n_frames) / 16000)
    return list(tone.astype(np.float32).reshape(-1, fr))


def _sil(stt: ParakeetSTT, n: int) -> list:
    return [np.zeros(stt._frame, np.float32) for _ in range(n)]


def test_single_utterance_closed_by_silence(stt):
    frames = _sil(stt, 10) + _loud(stt, 40) + _sil(stt, 30)  # >700ms trailing
    assert len(list(stt._segment(iter(frames)))) == 1


def test_end_of_stream_flushes_tail(stt):
    frames = _sil(stt, 10) + _loud(stt, 40) + _sil(stt, 10)  # <700ms → flush on end
    assert len(list(stt._segment(iter(frames)))) == 1


def test_two_utterances_separated_by_gap(stt):
    frames = _sil(stt, 10) + _loud(stt, 40) + _sil(stt, 30) + _loud(stt, 40) + _sil(stt, 30)
    assert len(list(stt._segment(iter(frames)))) == 2


def test_pure_silence_yields_nothing(stt):
    assert list(stt._segment(iter(_sil(stt, 40)))) == []


def test_subminimum_blip_ignored(stt):
    frames = _sil(stt, 10) + _loud(stt, 3) + _sil(stt, 30)  # 90ms < SAM_VAD_MIN_MS
    assert list(stt._segment(iter(frames))) == []
