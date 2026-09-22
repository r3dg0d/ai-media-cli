"""Text-to-image generation orchestration (animation → backend → preview)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ai_media.qwen.backend import GenerateRequest, QwenBackend, QwenNotInstalledError
from ai_media.qwen.prompting import enhance_prompt
from ai_media.shared.animation import BounceAnimation
from ai_media.shared.config import Config
from ai_media.shared.media_preview import maybe_open_image, preview_image
from ai_media.shared.metadata import write_sidecar
from ai_media.shared.monitoring import Monitor
from ai_media.shared.output import default_output_path
from ai_media.shared.ui import error, success


def run_text2img(
    *,
    prompt: str,
    output: Path | None = None,
    seed: int | None = None,
    steps: int = 40,
    width: int = 1024,
    height: int = 1024,
    memory: str = "auto",
    transparent: bool = False,
    fmt: str = "png",
    metadata: bool = True,
    preview: bool = True,
    open_image_flag: bool = False,
    monitor: bool = False,
    enhance: bool = False,
    quiet: bool = False,
    negative_prompt: str = "",
    guidance_scale: float = 4.0,
    cfg: Config | None = None,
    backend: QwenBackend | None = None,
) -> Path:
    prompt = enhance_prompt(prompt, enabled=enhance)
    out = output or default_output_path(
        "t2i",
        directory=Path.home() / "Pictures" / "AI" / "text2img",
        ext=fmt,
        seed=seed,
    )
    mon = Monitor(enabled=monitor)
    mon.snapshot("start")
    anim = BounceAnimation("Generating image", enabled=not quiet)
    anim.start()
    be = backend or QwenBackend()
    try:
        req = GenerateRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            steps=steps,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            transparent=transparent,
            output=out,
            memory_profile=memory,
            enhance_prompt=enhance,
        )
        t0 = time.perf_counter()
        path = be.generate(req)
        elapsed = time.perf_counter() - t0
    except QwenNotInstalledError as e:
        anim.stop()
        if not quiet:
            error(str(e))
        raise
    finally:
        # Always stop animation before any preview/render
        anim.stop()

    mon.snapshot("done")
    if metadata:
        meta: dict[str, Any] = {
            "prompt": prompt,
            "seed": seed,
            "steps": steps,
            "width": width,
            "height": height,
            "transparent": transparent,
            "model": be.model_id,
            "elapsed_s": elapsed,
        }
        write_sidecar(path, meta)
    if preview:
        preview_image(path, cfg=cfg)
    if open_image_flag:
        maybe_open_image(path, mode="always", cfg=cfg)
    if not quiet:
        success(f"Wrote {path}")
    return path
