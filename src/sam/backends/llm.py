"""Reasoner backends.

`StubLLM`   — zero deps, heuristic keyword→tool routing. Lets SAM run and be
              tested with no models at all. Good enough for the core demo loop.
`OllamaLLM` — real tool-calling over local Ollama, CPU-FORCED (num_gpu=0). This
              is the contract that keeps SAM in the battery envelope.

Both expose `step(messages, tools) -> Step`. The agent loops on that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..tools import Registry


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass
class Step:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLM(Protocol):
    def step(self, messages: list[dict[str, Any]], tools: Registry) -> Step: ...


# ── Stub ─────────────────────────────────────────────────────────────────────
class StubLLM:
    """No-model heuristic. Routes obvious intents to tools, else echoes.

    Intentionally dumb — it exists so the loop, tools, and runtime are testable
    without pulling a model. Swap in OllamaLLM for real reasoning.
    """

    _KEYWORDS = {
        "time": ("get_time", {}),
        "date": ("get_time", {}),
        "battery": ("get_battery", {}),
        "charge": ("get_battery", {}),
        "power": ("get_battery", {}),
    }

    def step(self, messages: list[dict[str, Any]], tools: Registry) -> Step:
        # Already have a tool result in history → summarise it as the answer.
        for m in reversed(messages):
            if m.get("role") == "tool":
                return Step(content=str(m.get("content", "")))
        user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        low = user.lower()
        if low.startswith(("volume", "set volume")):
            digits = "".join(c for c in low if c.isdigit())
            if tools.get("set_volume") and digits:
                return Step(tool_calls=[ToolCall("set_volume", {"level": digits})])
        if low.startswith(("open ", "launch ", "start ")):
            app = user.split(maxsplit=1)[1] if " " in user else ""
            if tools.get("launch_app"):
                return Step(tool_calls=[ToolCall("launch_app", {"app": app})])
        for kw, (tool, args) in self._KEYWORDS.items():
            if kw in low and tools.get(tool):
                return Step(tool_calls=[ToolCall(tool, args)])
        return Step(content=f"(stub) I heard: {user!r}. Try 'time', 'battery', 'volume 40'.")


# ── Ollama (CPU-forced) ──────────────────────────────────────────────────────
SYSTEM = (
    "You are SAM, a terse on-device assistant running CPU-only on battery. "
    "Prefer one short sentence. Use a tool when it answers the request directly."
)


class OllamaLLM:
    def __init__(self, host: str, model: str, cpu_only: bool = True) -> None:
        import httpx  # local import: only needed for this backend

        self._client = httpx.Client(base_url=host, timeout=120.0)
        self._model = model
        # num_gpu=0 is the hard CPU-only contract — no VRAM, no dGPU wake.
        self._options: dict[str, Any] = {"num_gpu": 0} if cpu_only else {}

    def step(self, messages: list[dict[str, Any]], tools: Registry) -> Step:
        body = {
            "model": self._model,
            "messages": [{"role": "system", "content": SYSTEM}, *messages],
            "tools": tools.as_ollama_schema(),
            "stream": False,
            "options": self._options,
        }
        data = self._client.post("/api/chat", json=body).raise_for_status().json()
        msg = data.get("message", {})
        calls = [
            ToolCall(c["function"]["name"], c["function"].get("arguments", {}))
            for c in msg.get("tool_calls", [])
        ]
        return Step(content=msg.get("content", ""), tool_calls=calls)


def build(cfg) -> LLM:
    if cfg.llm_backend == "ollama":
        return OllamaLLM(cfg.ollama_host, cfg.llm_model, cpu_only=cfg.cpu_only)
    return StubLLM()
