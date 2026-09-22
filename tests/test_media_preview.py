"""Preview / open prompts must not hang non-TTY."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ai_media.shared.config import Config
from ai_media.shared.media_preview import (
    maybe_open_image,
    preview_image,
    prompt_open_video,
)


def _png(tmp_path: Path) -> Path:
    p = tmp_path / "a.png"
    Image.new("RGB", (4, 4), color=(0, 255, 0)).save(p)
    return p


def test_preview_never(tmp_path):
    png = _png(tmp_path)
    cfg = Config(preview_mode="never")
    assert preview_image(png, cfg=cfg) is None


def test_preview_auto_non_tty(tmp_path, monkeypatch):
    png = _png(tmp_path)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    cfg = Config(preview_mode="auto")
    assert preview_image(png, cfg=cfg) is None


def test_prompt_open_video_non_tty_no_hang(tmp_path, monkeypatch):
    vid = tmp_path / "x.mp4"
    vid.write_bytes(b"\x00")
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)

    def boom(_prompt: str) -> str:
        raise AssertionError("input() must not be called on non-TTY")

    assert prompt_open_video(vid, mode="prompt", input_fn=boom) is False
    assert prompt_open_video(vid, mode="never", input_fn=boom) is False


def test_prompt_open_video_interactive_yes(tmp_path, monkeypatch):
    vid = tmp_path / "x.mp4"
    vid.write_bytes(b"\x00")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr(
        "ai_media.shared.media_preview.open_video",
        lambda *a, **k: True,
    )
    assert prompt_open_video(vid, mode="prompt", input_fn=lambda _: "y") is True
    assert prompt_open_video(vid, mode="prompt", input_fn=lambda _: "n") is False


def test_maybe_open_image_never(tmp_path):
    png = _png(tmp_path)
    assert maybe_open_image(png, mode="never") is False
