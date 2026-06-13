"""Battery / AC awareness — the reason SAM exists.

SAM is the *battery* member, so it cares about power state. These helpers read
sysfs directly (no deps) and are used both for the `battery` tool and to let the
runtime tune its own behaviour (e.g. back off when capacity is low).
"""

from __future__ import annotations

from pathlib import Path

_PSY = Path("/sys/class/power_supply")


def _read(p: Path) -> str | None:
    try:
        return p.read_text().strip()
    except OSError:
        return None


def on_ac() -> bool:
    """True if any AC adapter reports online. Defaults True if unknown (don't
    aggressively throttle on a machine we can't read)."""
    for ac in _PSY.glob("A*/online"):
        v = _read(ac)
        if v is not None:
            return v == "1"
    return True


def capacity() -> int | None:
    """Battery charge percentage, or None on a desktop / unreadable battery."""
    for bat in _PSY.glob("BAT*/capacity"):
        v = _read(bat)
        if v and v.isdigit():
            return int(v)
    return None


def status() -> str:
    """One-line human summary for the `battery` tool."""
    cap = capacity()
    if cap is None:
        return "No battery detected (on AC / desktop)."
    state = "charging" if on_ac() else "on battery"
    return f"Battery at {cap}% ({state})."
