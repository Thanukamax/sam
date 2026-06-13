"""Wires backends + agent into the listen → think → act → speak loop."""

from __future__ import annotations

from .agent import Agent
from .backends import llm as llm_mod
from .backends import stt as stt_mod
from .backends import tts as tts_mod
from .config import Config
from .tools import default_registry


class Runtime:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.tools = default_registry()
        self.agent = Agent(llm_mod.build(cfg), self.tools, max_steps=cfg.max_steps)
        self.stt = stt_mod.build(cfg)
        self.tts = tts_mod.build(cfg)

    def handle(self, text: str) -> str:
        """One turn: reason over `text`, speak the reply, return it."""
        reply = self.agent.run(text)
        self.tts.say(reply)
        return reply

    def serve(self) -> None:
        """Headless main loop: pull utterances from STT until the stream ends."""
        for utterance in self.stt.listen():
            self.handle(utterance)
