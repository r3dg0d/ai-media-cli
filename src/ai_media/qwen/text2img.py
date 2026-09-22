"""text2img CLI entry — Qwen-Image-2.1 text-to-image."""

from __future__ import annotations

import argparse
import json
import sys
import time

from ai_media import __version__
from ai_media.qwen.backend import QwenBackend, QwenNotInstalledError
from ai_media.qwen.generation import run_text2img
from ai_media.qwen.prompting import aspect_to_size
from ai_media.shared.config import load_config
from ai_media.shared.diagnostics import run_doctor
from ai_media.shared.signals import install_sigint_handler
from ai_media.shared.ui import banner, error


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="text2img",
        description="Qwen-Image-2.1 text-to-image (local)",
    )
    p.add_argument("prompt", nargs="?", default=None, help="Text prompt")
    p.add_argument("-p", "--prompt-flag", dest="prompt_opt", help="Prompt (alt)")
    p.add_argument("-o", "--output", help="Output image path")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--aspect", default=None, help="Aspect e.g. 1:1, 16:9, 9:16")
    p.add_argument(
        "--native-aspect",
        action="store_true",
        help="Use upstream native 2K aspect table (2048+; heavy on 24GB)",
    )
    p.add_argument(
        "--memory",
        choices=["auto", "performance", "balanced", "low-vram"],
        default=None,
    )
    p.add_argument("--transparent", action="store_true", help="RGBA / transparent")
    p.add_argument("--format", dest="fmt", default=None, choices=["png", "webp", "jpg"])
    p.add_argument("--metadata", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--preview", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--open", dest="open_image", action="store_true")
    p.add_argument("--monitor", action="store_true")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--benchmark", action="store_true", help="Print elapsed timing")
    p.add_argument("--enhance-prompt", action="store_true")
    p.add_argument("--negative-prompt", default='blurry, low quality, deformed, ugly')
    p.add_argument("--guidance-scale", type=float, default=4.0)
    p.add_argument("--model", default=None, help="HF model id override")
    p.add_argument("--doctor", action="store_true")
    p.add_argument("--version", action="store_true")
    return p


def main(argv: list[str] | None = None) -> None:
    install_sigint_handler()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        sys.exit(0)
    if args.doctor:
        be = QwenBackend(model_id=args.model)
        print(json.dumps(be.doctor(), indent=2))
        sys.exit(run_doctor(as_json=False) or 0)

    prompt = args.prompt_opt or args.prompt
    if not prompt:
        parser.error("prompt is required (unless --doctor / --version)")

    cfg = load_config(create=True)
    width = args.width if args.width is not None else cfg.default_width
    height = args.height if args.height is not None else cfg.default_height
    if args.aspect:
        width, height = aspect_to_size(args.aspect, native=args.native_aspect)
    steps = args.steps if args.steps is not None else cfg.default_steps
    memory = args.memory or cfg.memory_profile
    fmt = args.fmt or cfg.default_format

    if not args.quiet:
        banner("text2img", "Qwen-Image-2.1")

    t0 = time.perf_counter()
    try:
        path = run_text2img(
            prompt=prompt,
            output=args.output,
            seed=args.seed,
            steps=steps,
            width=width,
            height=height,
            memory=memory,
            transparent=args.transparent,
            fmt=fmt,
            metadata=args.metadata,
            preview=args.preview,
            open_image_flag=args.open_image,
            monitor=args.monitor,
            enhance=args.enhance_prompt,
            quiet=args.quiet,
            negative_prompt=args.negative_prompt,
            guidance_scale=args.guidance_scale,
            cfg=cfg,
            backend=QwenBackend(model_id=args.model) if args.model else None,
        )
    except QwenNotInstalledError as e:
        if not args.quiet:
            error(str(e))
        sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(130)

    if args.benchmark:
        print(f"benchmark_s={time.perf_counter() - t0:.3f} output={path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
