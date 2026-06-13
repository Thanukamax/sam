"""Tiny tool registry. A tool is a name + description + JSON-schema params + fn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the args object
    fn: Callable[..., str]


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def add(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def as_ollama_schema(self) -> list[dict[str, Any]]:
        """Tool list in the shape Ollama's /api/chat `tools` field expects."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": t.parameters,
                        "required": list(t.parameters.keys()),
                    },
                },
            }
            for t in self._tools.values()
        ]


def default_registry() -> Registry:
    from . import builtins

    return builtins.register(Registry())
