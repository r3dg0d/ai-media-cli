"""editvideo / SCAIL-2 readiness checks (honest fail-closed)."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from typing import Any

from ai_media.editvideo import paths
from ai_media.editvideo.models import default_model, list_models


def _which(name: str) -> str | None:
    return shutil.which(name)


def _try_import(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def _cuda_probe() -> dict[str, Any]:
    info: dict[str, Any] = {"torch": False, "cuda": False, "device": None, "vram_gb": None}
    try:
        import torch

        info["torch"] = True
        info["torch_version"] = torch.__version__
        info["cuda"] = bool(torch.cuda.is_available())
        if info["cuda"]:
            info["device"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["vram_gb"] = round(props.total_memory / (1024**3), 2)
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)
    return info


def _weights_status() -> dict[str, Any]:
    ckpt = paths.find_ckpt_dir()
    st = paths.find_safetensors(ckpt)
    out: dict[str, Any] = {
        "ckpt_dir": str(ckpt) if ckpt else None,
        "safetensors": str(st) if st else None,
        "wan_vae": False,
        "model_dir": False,
        "umt5": False,
        "ready_for_wan": False,
        "approx_size_note": "~82 GiB for full zai-org/SCAIL-2 (HF usedStorage)",
    }
    if ckpt is None:
        return out
    out["wan_vae"] = (ckpt / "Wan2.1_VAE.pth").is_file()
    out["model_dir"] = (ckpt / "model").is_dir()
    out["umt5"] = (ckpt / "umt5-xxl").is_dir()
    # wan branch needs converted safetensors; sat layout alone is not enough
    out["ready_for_wan"] = bool(out["wan_vae"] and out["model_dir"] and out["umt5"] and st)
    out["ready_ckpt_only"] = bool(out["wan_vae"] and out["model_dir"] and out["umt5"])
    return out


def doctor(*, as_json: bool = True) -> dict[str, Any]:
    repo = paths.scail_repo()
    venv = paths.scail_venv()
    example = paths.resolve_example_inputs("animation_001")
    cuda = _cuda_probe()
    weights = _weights_status()

    python_ok = sys.version_info >= (3, 10) and sys.version_info < (3, 13)
    checks = {
        "tool": "editvideo",
        "cloud": False,
        "python": {
            "version": sys.version.split()[0],
            "ok_for_scail": python_ok,
            "note": "SCAIL upstream wants 3.10–3.12 inclusive",
        },
        "venv": {
            "path": str(venv),
            "exists": venv.is_dir(),
            "python": str(venv / "bin" / "python") if (venv / "bin" / "python").is_file() else None,
        },
        "scail_repo": {
            "path": str(repo) if repo else None,
            "generate_py": bool(repo and (repo / "generate.py").is_file()),
            "convert_py": bool(repo and (repo / "convert.py").is_file()),
        },
        "imports": {
            "torch": _try_import("torch"),
            "wan": _try_import("wan"),
            "einops": _try_import("einops"),
            "flash_attn": _try_import("flash_attn"),
        },
        "cuda": cuda,
        "weights": weights,
        "example_animation_001": {
            "ready": example is not None,
            "files": {k: str(v) for k, v in example.items()} if example else None,
        },
        "ld_library_path_hint": "/run/opengl-driver/lib (NixOS) + typical nix cuda/gcc libs",
        "models": list_models(),
        "default_model": default_model(),
        "scail_1_3b_note": (
            "SCAIL-1.3B is a code config only for SCAIL-2; official HF weights are 14B-only. "
            "Prefer SCAIL-14B + --offload_model on RTX 4090 24GB."
        ),
        "binaries": {
            "ffmpeg": _which("ffmpeg"),
            "ffprobe": _which("ffprobe"),
            "xdg-open": _which("xdg-open"),
            "hf": _which("hf") or _which("huggingface-cli"),
            "uv": _which("uv"),
        },
    }

    ready = True
    blockers: list[str] = []
    if not checks["scail_repo"]["generate_py"]:
        ready = False
        blockers.append("SCAIL-2 repo with generate.py not found (set AI_MEDIA_SCAIL_REPO)")
    if not weights.get("ready_ckpt_only"):
        ready = False
        blockers.append(
            "SCAIL-2 weights missing (run scripts/setup_scail_env.sh --download-weights)"
        )
    if not weights.get("safetensors"):
        # wan branch typically needs convert; warn hard but allow doctor ready=False
        ready = False
        blockers.append(
            "Converted SCAIL-2.safetensors missing (python convert.py --scail-dir … --save-path …)"
        )
    if not cuda.get("cuda"):
        ready = False
        blockers.append("CUDA not available in this Python (check venv + LD_LIBRARY_PATH)")
    if cuda.get("vram_gb") is not None and float(cuda["vram_gb"]) < 20:
        blockers.append(
            f"VRAM {cuda['vram_gb']}GB is tight for SCAIL-14B; use offload + low res; OOM possible"
        )
    if not checks["imports"]["torch"]:
        ready = False
        blockers.append("torch not importable (activate scail venv / fix wrapper)")

    checks["ready"] = ready
    checks["blockers"] = blockers
    if as_json:
        return checks
    return checks


def print_doctor(data: dict[str, Any] | None = None, *, quiet: bool = False) -> int:
    data = data or doctor()
    print(json.dumps(data, indent=2))
    if data.get("ready"):
        return 0
    if not quiet:
        for b in data.get("blockers", []):
            print(f"blocker: {b}", file=sys.stderr)
    return 2
