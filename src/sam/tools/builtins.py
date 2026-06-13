"""SAM's built-in tools — deliberately tight. Battery member, KDE host, low power.

Everything here is cheap and local. No network, no GPU. Add tools sparingly:
SAM's value is staying small, not matching Diana's reach.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime

from .. import power
from . import Registry, Tool


def _time(_: str = "") -> str:
    return datetime.now().strftime("It's %H:%M on %A, %d %b.")


def _battery(_: str = "") -> str:
    return power.status()


def _volume(level: str = "") -> str:
    """Set system volume 0-100 via wpctl (PipeWire) if present."""
    if not level.strip().isdigit():
        return "Tell me a volume between 0 and 100."
    pct = max(0, min(100, int(level)))
    if shutil.which("wpctl"):
        subprocess.run(
            ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct}%"],
            check=False,
        )
        return f"Volume set to {pct}%."
    return "No wpctl found — can't set volume here."


def _launch(app: str = "") -> str:
    """Launch a desktop app detached (KDE host). Best-effort."""
    app = app.strip()
    if not app:
        return "Which app?"
    exe = shutil.which(app)
    if not exe:
        return f"Couldn't find '{app}' on PATH."
    subprocess.Popen(
        [exe],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return f"Launched {app}."


def register(reg: Registry) -> Registry:
    reg.add(Tool("get_time", "Get the current time and date.", {}, _time))
    reg.add(Tool("get_battery", "Report battery charge and AC status.", {}, _battery))
    reg.add(
        Tool(
            "set_volume",
            "Set the system output volume.",
            {"level": {"type": "string", "description": "0-100"}},
            _volume,
        )
    )
    reg.add(
        Tool(
            "launch_app",
            "Launch a desktop application by command name.",
            {"app": {"type": "string", "description": "executable name, e.g. 'kate'"}},
            _launch,
        )
    )
    return reg
