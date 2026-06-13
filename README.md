# SAM

**Small Agent, Mobile** — the CPU-only, frontend-less battery agent.
EVA family member **#3**.

```
EVA — a family of situation-specific local KDE agents
 ├─ #1  Diana    heavy all-purpose agent · GPU · voice orb
 ├─ #2  watcher  tiny always-on wake-word listener
 └─ #3  SAM      ← you are here · CPU-only · headless · battery
```

When the laptop drops to **Sim mode** (integrated GPU, on battery), running
Diana's full GPU stack is the wrong call — it drains the battery and the dGPU is
parked anyway. So [`eva-router`](https://github.com/Thanukamax/eva-router) hands
off: heavy Diana steps down, **SAM** takes over. No orb, no GPU models — a tiny
reasoner, a tight tool set, a fast wake.

## Design contract

- **CPU-only, enforced.** The Ollama backend sends `num_gpu: 0`. No VRAM, no dGPU
  wake. `SAM_CPU_ONLY=1` is the law, set again at the systemd-unit level.
- **No frontend.** Headless daemon. "Speaking" is stdout by default; real voice
  (Piper) is opt-in. Input is stdin/pipe by default; mic (Parakeet) is opt-in.
- **Small by choice.** Default reasoner is `qwen2.5:1.5b`. SAM's job is to stay
  in the battery envelope, not to match Diana's reach.
- **Runs with zero models.** Ships in `stub` mode — heuristic routing, no deps,
  no network — so it's installable and testable immediately.

## Quickstart

```bash
# one turn, stub mode — no models needed
uv run --project . sam --once "what time is it"
uv run --project . sam --once "battery?"
uv run --project . sam --once "volume 35"

# headless daemon (reads utterances from stdin in stub mode)
uv run --project . sam

# real reasoning over local Ollama, CPU-forced
SAM_LLM=ollama SAM_MODEL=qwen2.5:1.5b uv run --project . sam --once "set volume to 20"

# full voice: live mic (Parakeet int8 CPU) → tool-loop → reply
uv sync --extra voice
SAM_STT=parakeet SAM_LLM=ollama uv run --project . sam
```

## Install (wire into the EVA router)

```bash
./scripts/install.sh
```

This links `sam.service` **and** `eva-mini.service` (the name `eva-router` looks
for) into your systemd user units. The router then promotes SAM automatically the
next time supergfx flips to `Integrated`. Or start it by hand:

```bash
systemctl --user start sam.service
```

## Configuration (all env vars)

| Var | Default | Meaning |
|---|---|---|
| `SAM_LLM` | `stub` | reasoner: `stub` or `ollama` |
| `SAM_MODEL` | `qwen2.5:1.5b` | Ollama model (keep it small) |
| `SAM_OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama endpoint |
| `SAM_STT` | `stub` | speech-in: `stub` (stdin) or `parakeet` (live mic) |
| `SAM_TTS` | `stub` | speech-out: `stub` (stdout) or `piper` |
| `SAM_CPU_ONLY` | `1` | forbid GPU layers in the reasoner |
| `SAM_MAX_STEPS` | `4` | tool-loop ceiling |
| `SAM_STT_MODEL_DIR` | Diana's `…/models/parakeet-tdt-0.6b-v2-onnx` | reuse the int8 model, no re-download |
| `SAM_MIC_DEVICE` | `default` | ALSA capture device for `arecord` |
| `SAM_VAD_RMS` | `0.012` | energy gate; raise it if a hot mic triggers on silence |
| `SAM_VAD_SILENCE_MS` | `700` | trailing quiet that ends an utterance |
| `SAM_VAD_MIN_MS` | `300` | ignore blips shorter than this |
| `SAM_SET_GAIN` | `1` | pin mic gain before capture (set `0` to leave the mixer alone) |
| `SAM_CAPTURE_PCT` | `40%` | ALSA Capture level SAM pins to (matches the VAD calibration) |
| `SAM_MIC_BOOST` | `0` | ALSA Mic Boost dB SAM pins to |
| `SAM_MIXER_CARD` | `0` | ALSA card index for the mixer controls |

## Tools

`get_time` · `get_battery` · `set_volume` (PipeWire/wpctl) · `launch_app` (KDE).
Add tools sparingly — small is the point.

## Optional extras

```bash
uv sync --extra ollama   # httpx, for the Ollama backend
uv sync --extra voice    # onnx-asr + sounddevice + piper-tts (real speech)
uv sync --extra dev      # pytest
```

## Test

```bash
uv run --extra dev pytest -q   # smoke tests, stub mode, no models/network
```

## Status

**v0.1.0.** The loop, tools, config, router wiring, and stub backends are real
and tested. **Voice is wired:** `ParakeetSTT` does live mic capture (`arecord`) +
energy-VAD segmentation + Parakeet-TDT int8 CPU transcription, reusing Diana's
pre-downloaded model. The full *spoken-audio → tool-loop → reply* path is verified
end to end; the VAD state machine has its own deterministic tests (no mic needed).
Remaining polish: Piper voice-out tuning, and live VAD-threshold calibration for
your mic gain (`SAM_VAD_RMS`).

## Troubleshooting

- **`volume` says no wpctl** — install `wireplumber` (PipeWire). SAM won't fake it.
- **Ollama backend hangs / wakes GPU** — confirm `SAM_CPU_ONLY=1`; the request
  must carry `num_gpu: 0`. Check `ollama ps` shows 100% CPU.
- **Mic triggers constantly / never** — it's the energy gate vs your mic gain.
  SAM pins the gain before capture (`SAM_CAPTURE_PCT`, default `40%`) so the gate
  stays valid; if it still mis-fires, recalibrate with `scripts/calibrate_vad.sh`
  and adjust `SAM_VAD_RMS`. On a shared mic, another app (e.g. a voice assistant)
  may re-crank the gain — SAM re-pins on each `listen()`, but set `SAM_SET_GAIN=0`
  if you'd rather manage the mixer yourself.
- **`arecord: command not found`** — install `alsa-utils`. SAM captures through
  it on purpose (no PortAudio/native dep); it's already on most desktops.
- **Wrong mic** — set `SAM_MIC_DEVICE` (e.g. `plughw:0,0`); list with `arecord -l`.
