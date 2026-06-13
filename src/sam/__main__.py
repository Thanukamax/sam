"""CLI entry. `sam` (daemon) or `sam --once "..."` (single turn, for testing)."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import load
from .runtime import Runtime


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sam", description="SAM — CPU-only battery agent (EVA #3)")
    p.add_argument("--once", metavar="TEXT", help="run one turn on TEXT and exit")
    p.add_argument("--version", action="version", version=f"sam {__version__}")
    args = p.parse_args(argv)

    cfg = load()
    rt = Runtime(cfg)

    if args.once is not None:
        rt.handle(args.once)
        return 0

    # Daemon mode. Banner to stderr so stdout stays clean for piped use.
    print(f"SAM {__version__} up — llm={cfg.llm_backend} model={cfg.llm_model} "
          f"cpu_only={cfg.cpu_only}. Ctrl-D to stop.", file=sys.stderr)
    try:
        rt.serve()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
