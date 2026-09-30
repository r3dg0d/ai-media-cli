"""Image editing / img2img orchestration."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ai_media.qwen.backend import GenerateRequest, QwenBackend
from ai_media.qwen.prompting import enhance_prompt
from ai_media.shared.animation import BounceAnimation
from ai_media.shared.config import Config
from ai_media.shared.media_preview import maybe_open_image, preview_image
from ai_media.shared.metadata import write_sidecar
from ai_media.shared.monitoring import Monitor
from ai_media.shared.output import default_output_path
from ai_media.shared.ui import success


def run_img2img(
    *,
    prompt: str,
    image: Path,
    output: Path | None = None,
    seed: int | None = None,
    steps: int = 40,
    strength: float = 0.8,
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
    model_id: str | None = None,
) -> Path:
    prompt = enhance_prompt(prompt, enabled=enhance)
    image = Path(image)
    if not image.is_file():
        raise FileNotFoundError(image)
    out = output or default_output_path(
        "i2i",
        directory=Path.home() / "Pictures" / "AI" / "img2img",
        ext=fmt,
        seed=seed,
    )
    req = GenerateRequest(
        prompt=prompt,
        negative_prompt=negative_prompt,
        seed=seed,
        steps=steps,
        guidance_scale=guidance_scale,
        transparent=transparent,
        output=out,
        memory_profile=memory,
        enhance_prompt=enhance,
        image=image,
        strength=strength,
    )
    be = backend or QwenBackend(model_id=model_id)
    mon = Monitor(enabled=monitor)
    mon.snapshot("start")
    anim = BounceAnimation("Editing image", enabled=not quiet)
    anim.start()
    elapsed = 0.0
    try:
        t0 = time.perf_counter()
        path = be.generate(req)
        elapsed = time.perf_counter() - t0
    finally:
        anim.stop()

    mon.snapshot("done")
    if metadata:
        meta: dict[str, Any] = {
            "prompt": prompt,
            "image": str(image),
            "seed": seed,
            "steps": steps,
            "strength": strength,
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
