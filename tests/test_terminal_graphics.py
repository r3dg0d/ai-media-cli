"""Terminal graphics: non-TTY must not emit escape garbage."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from ai_media.shared.terminal_graphics import (
    GraphicsCapability,
    TerminalImageRenderer,
    detect_capabilities,
)


def _png(tmp_path: Path) -> Path:
    path = tmp_path / "tiny.png"
    Image.new("RGB", (8, 8), color=(255, 0, 0)).save(path)
    return path


def test_non_tty_detect_none(monkeypatch):
    buf = io.StringIO()
    # StringIO is not a TTY
    caps = detect_capabilities(stream=buf)
    assert caps.mode is GraphicsCapability.NONE
    assert caps.is_tty is False


def test_non_tty_render_no_escapes(tmp_path, monkeypatch):
    buf = io.StringIO()
    png = _png(tmp_path)
    r = TerminalImageRenderer.detect(stream=buf)
    assert r.capabilities().mode is GraphicsCapability.NONE
    mode = r.render(png)
    assert mode is GraphicsCapability.NONE
    out = buf.getvalue()
    assert "\x1b" not in out
    assert out == ""


def test_force_kitty_emits_protocol(tmp_path):
    buf = io.StringIO()
    # Force kitty even on non-tty stream for unit coverage of encoder
    r = TerminalImageRenderer.detect(force=GraphicsCapability.KITTY, stream=buf)
    # Override caps.is_tty awareness: render still writes when forced
    png = _png(tmp_path)
    # Manually set mode via force — detect with force sets mode kitty
    assert r.capabilities().mode is GraphicsCapability.KITTY
    r.render(png)
    out = buf.getvalue()
    assert "\x1b_G" in out
    assert "f=100" in out
    assert "\x1b\\" in out


def test_clear_kitty(tmp_path):
    buf = io.StringIO()
    r = TerminalImageRenderer(
        __import__("ai_media.shared.terminal_graphics", fromlist=["Capabilities"]).Capabilities(
            mode=GraphicsCapability.KITTY,
            is_tty=True,
            term_program="kitty",
            kitty_detected=True,
            chafa_available=False,
        ),
        stream=buf,
    )
    r.clear()
    assert "a=d" in buf.getvalue()


def test_capabilities_dict():
    caps = detect_capabilities(force=GraphicsCapability.ANSI)
    d = caps.as_dict()
    assert d["mode"] == "ansi"


def test_ghostty_env_hint(monkeypatch):
    monkeypatch.setenv("GHOSTTY_RESOURCES_DIR", "/usr/share/ghostty")
    monkeypatch.delenv("KITTY_WINDOW_ID", raising=False)
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    # Force tty so mode isn't NONE
    import io
    buf = io.StringIO()
    monkeypatch.setattr(buf, "isatty", lambda: True)
    caps = detect_capabilities(stream=buf)
    assert caps.kitty_detected is True
    assert caps.mode is GraphicsCapability.KITTY


def test_ai_media_graphics_env_force(monkeypatch):
    monkeypatch.setenv("AI_MEDIA_GRAPHICS", "chafa")
    import io
    buf = io.StringIO()
    monkeypatch.setattr(buf, "isatty", lambda: True)
    caps = detect_capabilities(stream=buf)
    assert caps.mode is GraphicsCapability.CHAFA
