#!/usr/bin/env bash
# Install SAM's systemd user unit and link it to the eva-router's mini slot.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

ln -sf "$HERE/systemd/sam.service" "$UNIT_DIR/sam.service"
# eva-router promotes MINI_UNIT (default eva-mini.service). Alias sam → that name
# so the router finds SAM without editing the router.
ln -sf "$HERE/systemd/sam.service" "$UNIT_DIR/eva-mini.service"

systemctl --user daemon-reload
echo "Installed. sam.service + eva-mini.service linked."
echo "Try a turn:   uv run --project '$HERE' sam --once 'battery?'"
echo "Arm via router (already running) — it'll start SAM next time you hit Sim mode."
echo "Or start now:  systemctl --user start sam.service"
