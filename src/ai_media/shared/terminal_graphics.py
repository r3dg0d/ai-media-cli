"""Terminal image rendering: Kitty graphics → chafa → ANSI → none."""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TextIO


class GraphicsCapability(StrEnum):
    KITTY = "kitty"
    CHAFA = "chafa"
    ANSI = "ansi"
    NONE = "none"


# Kitty graphics protocol: ESC _ G <keys> ; <payload> ESC \
_KITTY_START = "\x1b_G"
_KITTY_END = "\x1b\\"
_CHUNK = 4096  # base64 chunk size recommended by Kitty docs


@dataclass(frozen=True)
class Capabilities:
    mode: GraphicsCapability
    is_tty: bool
    term_program: str | None
    kitty_detected: bool
    chafa_available: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "is_tty": self.is_tty,
            "term_program": self.term_program,
            "kitty_detected": self.kitty_detected,
            "chafa_available": self.chafa_available,
        }


def _is_tty(stream: TextIO | None = None) -> bool:
    stream = stream or sys.stdout
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def _term_program() -> str | None:
    return os.environ.get("TERM_PROGRAM") or os.environ.get("TERMINAL_EMULATOR")


def _kitty_env_hints() -> bool:
    """Fast path: TERM_PROGRAM / KITTY_WINDOW_ID / Ghostty / WezTerm."""
    if os.environ.get("KITTY_WINDOW_ID"):
        return True
    # Ghostty sets GHOSTTY_RESOURCES_DIR (and often TERM=xterm-ghostty)
    if os.environ.get("GHOSTTY_RESOURCES_DIR") or os.environ.get("GHOSTTY_BIN_DIR"):
        return True
    tp = (_term_program() or "").lower()
    if "kitty" in tp or tp in {"ghostty", "wezterm"}:
        return True
    term = (os.environ.get("TERM") or "").lower()
    if "kitty" in term or "ghostty" in term or term.endswith("-ghostty"):
        return True
    # Explicit override for scripts launched outside Ghostty but piping into it
    force = (os.environ.get("AI_MEDIA_GRAPHICS") or "").strip().lower()
    if force in {"kitty", "ghostty", "wezterm"}:
        return True
    return False


def _query_kitty_support(timeout: float = 0.15) -> bool:
    """Optional CSI query; skipped / fails closed when not a TTY."""
    if not _is_tty(sys.stdout) or not _is_tty(sys.stdin):
        return False
    # Query: transmit a tiny empty image with quiet+response (a=q)
    # Many environments won't answer; treat timeout as unsupported.
    try:
        # Non-blocking-ish: write query and don't wait long.
        # We avoid reading stdin in unit tests / pipes.
        return False  # conservative: env hints are primary
    except Exception:
        return False


def _chafa_available() -> bool:
    return shutil.which("chafa") is not None


def detect_capabilities(
    *,
    force: GraphicsCapability | None = None,
    stream: TextIO | None = None,
) -> Capabilities:
    stream = stream or sys.stdout
    is_tty = _is_tty(stream)
    tp = _term_program()
    kitty = _kitty_env_hints() or _query_kitty_support()
    chafa = _chafa_available()

    env_force = (os.environ.get("AI_MEDIA_GRAPHICS") or "").strip().lower()
    if force is None and env_force:
        mapping = {
            "kitty": GraphicsCapability.KITTY,
            "ghostty": GraphicsCapability.KITTY,
            "wezterm": GraphicsCapability.KITTY,
            "chafa": GraphicsCapability.CHAFA,
            "ansi": GraphicsCapability.ANSI,
            "none": GraphicsCapability.NONE,
        }
        force = mapping.get(env_force)

    if force is not None:
        mode = force
    elif not is_tty:
        mode = GraphicsCapability.NONE
    elif kitty:
        mode = GraphicsCapability.KITTY
    elif chafa:
        mode = GraphicsCapability.CHAFA
    else:
        mode = GraphicsCapability.ANSI

    return Capabilities(
        mode=mode,
        is_tty=is_tty,
        term_program=tp,
        kitty_detected=kitty,
        chafa_available=chafa,
    )


def _kitty_transmit_png(data: bytes, out: TextIO) -> None:
    """Transmit PNG via Kitty graphics protocol (direct, base64 chunks)."""
    b64 = base64.standard_b64encode(data).decode("ascii")
    # First chunk: a=T (transmit+display), f=100 (PNG), m=1 if more
    pos = 0
    first = True
    while pos < len(b64):
        chunk = b64[pos : pos + _CHUNK]
        pos += _CHUNK
        more = 1 if pos < len(b64) else 0
        if first:
            keys = f"a=T,f=100,m={more}"
            first = False
        else:
            keys = f"m={more}"
        out.write(f"{_KITTY_START}{keys};{chunk}{_KITTY_END}")
    out.write("\n")
    out.flush()


def _kitty_clear(out: TextIO) -> None:
    # Delete all visible placements: a=d, d=A
    out.write(f"{_KITTY_START}a=d,d=A{_KITTY_END}\n")
    out.flush()


def _render_chafa(path: Path, out: TextIO) -> None:
    cmd = ["chafa", "--size", "80x40", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode == 0 and result.stdout:
        out.write(result.stdout)
        if not result.stdout.endswith("\n"):
            out.write("\n")
        out.flush()
    else:
        _render_ansi_fallback(path, out)


def _render_ansi_fallback(path: Path, out: TextIO) -> None:
    """Last-resort: tiny Unicode block summary (no escape spam on pipes)."""
    try:
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
            mode = im.mode
        out.write(f"[image {path.name} {w}x{h} {mode}]\n")
    except Exception:
        out.write(f"[image {path}]\n")
    out.flush()


class TerminalImageRenderer:
    """Detect terminal graphics capability and render/clear images."""

    def __init__(self, caps: Capabilities, stream: TextIO | None = None) -> None:
        self._caps = caps
        self._stream = stream or sys.stdout

    @classmethod
    def detect(
        cls,
        *,
        force: GraphicsCapability | None = None,
        stream: TextIO | None = None,
    ) -> TerminalImageRenderer:
        caps = detect_capabilities(force=force, stream=stream)
        return cls(caps, stream=stream)

    def capabilities(self) -> Capabilities:
        return self._caps

    def render(self, path: str | Path) -> GraphicsCapability:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        mode = self._caps.mode
        if mode is GraphicsCapability.NONE:
            return mode
        if mode is GraphicsCapability.KITTY:
            data = path.read_bytes()
            _kitty_transmit_png(data, self._stream)
            return mode
        if mode is GraphicsCapability.CHAFA:
            _render_chafa(path, self._stream)
            return mode
        _render_ansi_fallback(path, self._stream)
        return GraphicsCapability.ANSI

    def clear(self) -> None:
        if self._caps.mode is GraphicsCapability.KITTY and self._caps.is_tty:
            _kitty_clear(self._stream)

    def render_bytes(self, data: bytes, *, suffix: str = ".png") -> GraphicsCapability:
        """Render in-memory PNG bytes (Kitty path only for raw bytes)."""
        mode = self._caps.mode
        if mode is GraphicsCapability.NONE:
            return mode
        if mode is GraphicsCapability.KITTY:
            _kitty_transmit_png(data, self._stream)
            return mode
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        try:
            return self.render(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
