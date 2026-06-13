"""SAM — Small Agent, Mobile.

EVA family member #3: a CPU-only, frontend-less agent that takes over when the
laptop drops to Sim mode (integrated GPU, on battery). No orb, no GPU models —
just a tiny reasoner, a tight tool set, and a fast wake.

  EVA member #1 — Diana   : heavy all-purpose agent (GPU, voice orb)
  EVA member #2 — watcher : tiny wake-word listener
  EVA member #3 — SAM     : this. battery-side, CPU-only, headless.

The eva-router promotes SAM (sam.service) the moment supergfx flips to Integrated.
"""

__version__ = "0.1.0"
