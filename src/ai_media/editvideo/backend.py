"""Invoke SCAIL-2 generate.py with offload-friendly defaults."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_media.editvideo import paths
from ai_media.editvideo.models import default_model


class ScailNotReadyError(RuntimeError):
    """Raised when env/weights/repo are insufficient — fail closed, never fake."""


@dataclass
class GenerateRequest:
    image: Path
    mask_image: Path
    pose: Path
    mask_video: Path
    prompt: str = ""
    save_file: Path | None = None
    model: str = "SCAIL-14B"
    target_h: int = 512
    target_w: int = 896
    sample_steps: int = 40
    sample_shift: float = 3.0
    sample_guide_scale: float = 5.0
    offload_model: bool = True
    t5_cpu: bool = True
    replace_flag: bool = False
    seed: int = -1
    segment_len: int | None = None
    dry_run: bool = False


def nixos_ld_library_path() -> str:
    """Prepend typical NixOS CUDA / driver libs like other ai-media wrappers."""
    extras = [
        "/run/opengl-driver/lib",
        "/run/opengl-driver-32/lib",
    ]
    # Optional nix store hints if already on LD_LIBRARY_PATH
    current = os.environ.get("LD_LIBRARY_PATH", "")
    parts = [p for p in extras if Path(p).exists()]
    if current:
        parts.append(current)
    return ":".join(parts)


def python_for_scail() -> Path:
    venv_py = paths.scail_venv() / "bin" / "python"
    if venv_py.is_file():
        return venv_py
    return Path(sys.executable)


def build_generate_argv(req: GenerateRequest) -> list[str]:
    repo = paths.scail_repo()
    if repo is None:
        raise ScailNotReadyError("SCAIL-2 repo not found (set AI_MEDIA_SCAIL_REPO)")
    ckpt = paths.find_ckpt_dir()
    if ckpt is None:
        raise ScailNotReadyError("SCAIL-2 checkpoint dir not found")
    st = paths.find_safetensors(ckpt)
    if st is None:
        raise ScailNotReadyError(
            "Converted SCAIL-2.safetensors not found. "
            "Run: python convert.py --scail-dir CKPT --save-path "
            f"{paths.models_root() / 'SCAIL-2.safetensors'}"
        )

    model = req.model.upper()
    if model == "SCAIL-1.3B":
        # Refuse unless a dedicated 1.3B weight file is clearly present
        # (official SCAIL-2 HF card is 14B-only).
        raise ScailNotReadyError(
            "SCAIL-1.3B weights are not published for SCAIL-2 (HF is 14B-only). "
            "Use --model SCAIL-14B with --offload-model."
        )

    py = python_for_scail()
    gen = repo / "generate.py"
    argv = [
        str(py),
        str(gen),
        "--model",
        model,
        "--ckpt_dir",
        str(ckpt),
        "--scail_path",
        str(st),
        "--target_h",
        str(req.target_h),
        "--target_w",
        str(req.target_w),
        "--image",
        str(req.image),
        "--mask_image",
        str(req.mask_image),
        "--pose",
        str(req.pose),
        "--mask_video",
        str(req.mask_video),
        "--prompt",
        req.prompt,
        "--offload_model",
        "true" if req.offload_model else "false",
        "--sample_steps",
        str(req.sample_steps),
        "--sample_shift",
        str(req.sample_shift),
        "--sample_guide_scale",
        str(req.sample_guide_scale),
        "--base_seed",
        str(req.seed),
    ]
    if req.t5_cpu:
        argv.append("--t5_cpu")
    if req.replace_flag:
        argv.append("--replace_flag")
    if req.segment_len is not None:
        argv.extend(["--segment_len", str(req.segment_len)])
    if req.save_file is not None:
        argv.extend(["--save_file", str(req.save_file)])
    return argv


def run_generate(req: GenerateRequest, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    argv = build_generate_argv(req)
    repo = paths.scail_repo()
    assert repo is not None
    run_env = os.environ.copy()
    run_env["LD_LIBRARY_PATH"] = nixos_ld_library_path()
    # Ensure SCAIL repo is importable
    pp = run_env.get("PYTHONPATH", "")
    run_env["PYTHONPATH"] = str(repo) + (os.pathsep + pp if pp else "")
    if env:
        run_env.update(env)

    meta: dict[str, Any] = {
        "argv": argv,
        "cwd": str(repo),
        "dry_run": req.dry_run,
    }
    if req.dry_run:
        return meta

    proc = subprocess.run(
        argv,
        cwd=str(repo),
        env=run_env,
        check=False,
        capture_output=True,
        text=True,
    )
    meta["returncode"] = proc.returncode
    meta["stdout_tail"] = (proc.stdout or "")[-8000:]
    meta["stderr_tail"] = (proc.stderr or "")[-8000:]
    if proc.returncode != 0:
        raise RuntimeError(
            f"generate.py failed (exit {proc.returncode}). "
            f"stderr_tail:\n{meta['stderr_tail']}"
        )
    if req.save_file is not None:
        if not req.save_file.is_file() or req.save_file.stat().st_size == 0:
            raise RuntimeError(
                f"generation returned success but output video is missing or empty: {req.save_file}"
            )
        meta["output"] = str(req.save_file.resolve())
    return meta


def default_model_name() -> str:
    return default_model()
