"""Text-out. Stub prints (headless default); piper is the real CPU voice."""

from __future__ import annotations

import shutil
import subprocess
from typing import Protocol


class TTS(Protocol):
    def say(self, text: str) -> None: ...


class StubTTS:
    """Headless default — SAM has no frontend, so 'speaking' is stdout."""

    def say(self, text: str) -> None:
        print(f"SAM> {text}", flush=True)


class PiperTTS:
    """Piper: fast, fully-CPU neural TTS. Falls back to espeak, then stdout."""

    def say(self, text: str) -> None:
        if shutil.which("piper") and shutil.which("aplay"):
            p = subprocess.Popen(["piper", "--output-raw"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)
            subprocess.Popen(["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw"],
                             stdin=p.stdout)
            assert p.stdin
            p.stdin.write(text.encode())
            p.stdin.close()
            return
        if shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", text], check=False)
            return
        print(f"SAM> {text}", flush=True)


def build(cfg) -> TTS:
    return PiperTTS() if cfg.tts_backend == "piper" else StubTTS()
