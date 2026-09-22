"""Image/video preview and open helpers (never hang non-TTY)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

from ai_media.shared.config import Config, OpenMode, PreviewMode, load_config
from ai_media.shared.terminal_graphics import GraphicsCapability, TerminalImageRenderer

OpenModeArg = OpenMode | Literal["auto", "always", "never", "prompt"]


def _is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def preview_image(
    path: str | Path,
    *,
    mode: PreviewMode | None = None,
    renderer: TerminalImageRenderer | None = None,
    cfg: Config | None = None,
) -> GraphicsCapability | None:
    """Render image in-terminal per config preview_mode."""
    cfg = cfg or load_config(create=False)
    preview = mode or cfg.preview_mode
    path = Path(path)
    if preview == "never":
        return None
    if preview == "auto" and not sys.stdout.isatty():
        return None
    if preview == "prompt":
        if not _is_interactive():
            return None
        answer = input(f"Preview {path.name} in terminal? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            return None
    r = renderer or TerminalImageRenderer.detect()
    return r.render(path)


def open_image(
    path: str | Path,
    *,
    viewer: str | None = None,
    cfg: Config | None = None,
) -> bool:
    """Open image with imv (argv list) or configured viewer. Returns True if launched."""
    cfg = cfg or load_config(create=False)
    path = Path(path).resolve()
    candidates = []
    primary = viewer or cfg.image_viewer
    if primary:
        candidates.append(primary)
    for fallback in ("imv", "xdg-open"):
        if fallback not in candidates:
            candidates.append(fallback)
    for cmd_name in candidates:
        exe = shutil.which(cmd_name)
        if not exe:
            continue
        # Always argv list — never shell
        subprocess.Popen([exe, str(path)], start_new_session=True)
        return True
    return False


def open_video(
    path: str | Path,
    *,
    opener: str | None = None,
    cfg: Config | None = None,
) -> bool:
    """Open video via xdg-open (or configured opener)."""
    cfg = cfg or load_config(create=False)
    path = Path(path).resolve()
    cmd_name = opener or cfg.video_opener
    exe = shutil.which(cmd_name)
    if not exe:
        return False
    subprocess.Popen([exe, str(path)], start_new_session=True)
    return True


def prompt_open_video(
    path: str | Path,
    *,
    mode: OpenModeArg | None = None,
    cfg: Config | None = None,
    input_fn=input,
) -> bool:
    """
    Optionally open a video.

    - never: no-op
    - always: open without asking
    - auto: open only if interactive TTY
    - prompt: ask only if TTY interactive; never hang non-TTY
    """
    cfg = cfg or load_config(create=False)
    open_mode: OpenModeArg = mode or cfg.open_video_mode
    path = Path(path)

    if open_mode == "never":
        return False
    if open_mode == "always":
        return open_video(path, cfg=cfg)
    if open_mode == "auto":
        if not _is_interactive():
            return False
        return open_video(path, cfg=cfg)
    # prompt
    if not _is_interactive():
        return False
    answer = input_fn(f"Open video {path.name}? [y/N] ").strip().lower()
    if answer in {"y", "yes"}:
        return open_video(path, cfg=cfg)
    return False


def maybe_open_image(
    path: str | Path,
    *,
    mode: OpenModeArg | None = None,
    cfg: Config | None = None,
    input_fn=input,
) -> bool:
    cfg = cfg or load_config(create=False)
    open_mode: OpenModeArg = mode or cfg.open_image_mode
    path = Path(path)
    if open_mode == "never":
        return False
    if open_mode == "always":
        return open_image(path, cfg=cfg)
    if open_mode == "auto":
        if not _is_interactive():
            return False
        return open_image(path, cfg=cfg)
    if not _is_interactive():
        return False
    answer = input_fn(f"Open image {path.name} in viewer? [y/N] ").strip().lower()
    if answer in {"y", "yes"}:
        return open_image(path, cfg=cfg)
    return False
