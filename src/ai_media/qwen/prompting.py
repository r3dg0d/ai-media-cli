"""Prompt helpers / optional enhance-prompt stub + aspect ratio maps."""

from __future__ import annotations

from math import isfinite

# Native 2K aspect table from Qwen-Image-2.1 upstream README / research memo.
NATIVE_ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "1:1": (2048, 2048),
    "4:3": (2400, 1792),
    "3:4": (1792, 2400),
    "3:2": (2528, 1696),
    "2:3": (1696, 2528),
    "16:9": (2752, 1536),
    "9:16": (1536, 2752),
}

# Alias for callers that expect ASPECT_RATIOS
ASPECT_RATIOS = NATIVE_ASPECT_RATIOS


def enhance_prompt(prompt: str, *, enabled: bool = False) -> str:
    """
    Optional prompt enhancer.

    Real LLM enhancement is deferred; when enabled we apply light cleanup only
    so CLIs remain testable offline.
    """
    text = " ".join(prompt.split())
    if not enabled:
        return text
    # Lightweight deterministic polish (no network)
    if not text.endswith((".", "!", "?")):
        text = text + "."
    return text


def aspect_to_size(
    aspect: str,
    base: int = 1024,
    *,
    native: bool = False,
) -> tuple[int, int]:
    """
    Map aspect ratio string to width/height.

    By default scales near ``base`` (1024 recommended on 24GB before native 2K).
    With ``native=True``, use the upstream 2K ``NATIVE_ASPECT_RATIOS`` table.
    """
    aspect = aspect.strip().lower().replace(" ", "")
    if native and aspect in NATIVE_ASPECT_RATIOS:
        return NATIVE_ASPECT_RATIOS[aspect]

    presets = {
        "1:1": (base, base),
        "16:9": (base, int(base * 9 / 16)),
        "9:16": (int(base * 9 / 16), base),
        "4:3": (base, int(base * 3 / 4)),
        "3:4": (int(base * 3 / 4), base),
        "3:2": (base, int(base * 2 / 3)),
        "2:3": (int(base * 2 / 3), base),
    }
    if aspect in presets:
        w, h = presets[aspect]
        return _round64(w), _round64(h)
    if "x" in aspect:
        a, b = aspect.split("x", 1)
        w, h = int(a), int(b)
        if w < 64 or h < 64:
            raise ValueError("aspect dimensions must be >= 64")
        return _round64(w), _round64(h)
    if ":" in aspect:
        a, b = aspect.split(":", 1)
        aw, ah = float(a), float(b)
        if not (isfinite(aw) and isfinite(ah) and aw > 0 and ah > 0):
            raise ValueError("aspect ratio components must be finite and > 0")
        if aw >= ah:
            w = base
            h = int(base * (ah / aw))
        else:
            h = base
            w = int(base * (aw / ah))
        return _round64(w), _round64(h)
    raise ValueError(f"unknown aspect: {aspect}")


def _round64(n: int) -> int:
    return max(64, int(round(n / 64) * 64))
