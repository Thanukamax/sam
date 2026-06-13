#!/usr/bin/env bash
# Measure the mic's silence floor and suggest a SAM_VAD_RMS gate.
# Stay quiet for the recording. Re-run whenever mic gain changes.
#
#   ./scripts/calibrate_vad.sh [seconds] [alsa-device]
set -euo pipefail

SECS="${1:-5}"
DEV="${2:-${SAM_MIC_DEVICE:-default}}"
RAW="$(mktemp --suffix=.raw)"
trap 'rm -f "$RAW"' EXIT

echo "Recording ${SECS}s of SILENCE from '$DEV' — stay quiet..."
arecord -q -D "$DEV" -f S16_LE -c 1 -r 16000 -t raw -d "$SECS" "$RAW"

HERE="$(cd "$(dirname "$0")/.." && pwd)"
uv run --project "$HERE" --extra voice python - "$RAW" <<'PY'
import sys, numpy as np
pcm = np.fromfile(sys.argv[1], dtype=np.int16).astype(np.float32) / 32768.0
fr = 480  # 30ms @ 16k
rms = np.array([np.sqrt(np.mean(pcm[i*fr:(i+1)*fr]**2)) for i in range(len(pcm)//fr)])[8:]
floor = float(rms.max())
print(f"silence floor: median {np.median(rms):.4f}  p95 {np.percentile(rms,95):.4f}  max {floor:.4f}")
if floor > 0.15:
    print(f"⚠ floor is high ({floor:.3f}) — mic gain is likely too hot. Lower it:")
    print("   amixer -c 0 sset 'Mic Boost' 0 ; amixer -c 0 sset Capture 40%")
    print("   then re-run this script.")
else:
    sug = round(floor * 1.6, 3)
    print(f"→ suggested SAM_VAD_RMS = {sug}  (1.6x the loudest silence frame)")
    print(f"   set it in systemd/sam.service or: SAM_VAD_RMS={sug} sam")
PY
