"""The tool-loop. Backend-agnostic: feed it text, get a reply, tools run in between.

Bounded by cfg.max_steps so a confused small model can't spin. Tool errors are
returned to the model as text (no silent failures) so it can recover or apologise.
"""

from __future__ import annotations

import json
from typing import Any

from .backends.llm import LLM
from .tools import Registry


class Agent:
    def __init__(self, llm: LLM, tools: Registry, max_steps: int = 4) -> None:
        self._llm = llm
        self._tools = tools
        self._max_steps = max_steps

    def run(self, text: str) -> str:
        messages: list[dict[str, Any]] = [{"role": "user", "content": text}]
        for _ in range(self._max_steps):
            step = self._llm.step(messages, self._tools)
            if not step.tool_calls:
                return step.content or "(no reply)"
            # Record the assistant's tool intent, then execute each call.
            messages.append({"role": "assistant", "content": step.content,
                             "tool_calls": [{"function": {"name": c.name, "arguments": c.args}}
                                            for c in step.tool_calls]})
            for call in step.tool_calls:
                messages.append({"role": "tool", "name": call.name,
                                 "content": self._invoke(call.name, call.args)})
        # Hit the step ceiling — return whatever the last tool said.
        last_tool = next((m["content"] for m in reversed(messages) if m["role"] == "tool"), "")
        return last_tool or "I got stuck on that one."

    def _invoke(self, name: str, args: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"[error] no such tool: {name}"
        try:
            return tool.fn(**args)
        except TypeError:
            # Model passed odd args — be forgiving, try positional first value.
            try:
                return tool.fn(*list(args.values())[:1]) if args else tool.fn()
            except Exception as e:  # noqa: BLE001 - surface, never swallow
                return f"[error] {name}: {e}"
        except Exception as e:  # noqa: BLE001
            return f"[error] {name}: {e}"

    @staticmethod
    def _fmt(args: dict[str, Any]) -> str:
        return json.dumps(args, separators=(",", ":"))
