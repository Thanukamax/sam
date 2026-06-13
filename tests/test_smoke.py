"""Smoke tests — run the whole loop in stub mode, no models, no network."""

from __future__ import annotations

from sam.config import Config
from sam.runtime import Runtime
from sam.tools import default_registry


def _rt() -> Runtime:
    # Force stub backends regardless of the ambient environment.
    return Runtime(Config(llm_backend="stub", stt_backend="stub", tts_backend="stub"))


def test_time_tool_routes():
    reply = _rt().agent.run("what time is it?")
    assert ":" in reply  # the formatted clock string


def test_battery_tool_routes():
    reply = _rt().agent.run("how's the battery?")
    assert "atter" in reply.lower() or "AC" in reply  # "Battery..." or "...on AC"


def test_unknown_falls_back_to_text():
    reply = _rt().agent.run("tell me a story")
    assert reply  # stub echoes, never crashes


def test_registry_has_core_tools():
    names = {t.name for t in default_registry().all()}
    assert {"get_time", "get_battery", "set_volume", "launch_app"} <= names


def test_handle_returns_and_speaks(capsys):
    reply = _rt().handle("time")
    out = capsys.readouterr().out
    assert "SAM>" in out and reply
