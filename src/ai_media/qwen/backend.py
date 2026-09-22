"""Pluggable Qwen-Image-2.1 backend (diffusers) with real BF16 CUDA inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

QWEN_MODEL_ID = "Qwen/Qwen-Image-2.1"
SETUP_HINT = "run scripts/setup_qwen_env.sh"

# Upstream RGBA prompt wrappers (Qwen-Image-2.1 README)
_RGBA_PREFIX = "This is an RGBA image with transparency. "
_RGBA_SUFFIX = " The image has alpha channel and the background is transparent."

_VALID_MEMORY = frozenset({"auto", "performance", "balanced", "low-vram"})


class QwenNotInstalledError(RuntimeError):
    """Raised when generate is called without model/deps installed."""

    def __init__(self, detail: str = "") -> None:
        msg = (
            f"Qwen-Image-2.1 backend is not ready. {SETUP_HINT}"
            + (f" ({detail})" if detail else "")
        )
        super().__init__(msg)
        self.detail = detail


class QwenCudaRequiredError(RuntimeError):
    """Raised when CUDA is unavailable — CPU inference is not supported."""

    def __init__(self, detail: str = "") -> None:
        msg = (
            "Qwen-Image-2.1 requires CUDA; refusing silent CPU fallback for large inference."
            + (f" {detail}" if detail else "")
        )
        super().__init__(msg)


class ImageBackend(Protocol):
    def generate(self, **kwargs: Any) -> Path: ...

    def doctor(self) -> dict[str, Any]: ...


@dataclass
class GenerateRequest:
    prompt: str
    negative_prompt: str = ""
    seed: int | None = None
    steps: int = 40
    width: int = 1024
    height: int = 1024
    guidance_scale: float = 4.0
    transparent: bool = False
    output: Path | None = None
    memory_profile: str = "auto"
    enhance_prompt: bool = False
    # img2img / edit
    image: Path | None = None
    strength: float = 0.8
    # optional extra reference images (multi-ref edit, up to 10 total)
    images: list[Path] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if self.steps < 1:
            raise ValueError("steps must be >= 1")
        if self.width < 64 or self.height < 64:
            raise ValueError("width and height must be >= 64")
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError("strength must be in [0.0, 1.0]")
        if self.memory_profile not in _VALID_MEMORY:
            raise ValueError(
                f"memory_profile must be one of {sorted(_VALID_MEMORY)}, "
                f"got {self.memory_profile!r}"
            )
        if self.guidance_scale <= 0:
            raise ValueError("guidance_scale must be > 0")
        if self.output is not None and not isinstance(self.output, Path):
            self.output = Path(self.output)
        if self.image is not None and not isinstance(self.image, Path):
            self.image = Path(self.image)
        if self.images:
            self.images = [Path(p) for p in self.images]


def apply_transparent_prompt(prompt: str) -> str:
    """Wrap prompt with upstream RGBA prefix/suffix if not already present."""
    text = prompt.strip()
    marker = "RGBA image with transparency"
    if marker in text:
        return text
    body = text.rstrip(". ")
    return f"{_RGBA_PREFIX}{body}.{_RGBA_SUFFIX}"


def default_pictures_path(*, img2img: bool, seed: int | None = None) -> Path:
    """Default PNG under ~/Pictures/AI/text2img or img2img."""
    kind = "img2img" if img2img else "text2img"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    parts = ["qwen", ts]
    if seed is not None:
        parts.append(f"s{seed}")
    name = "_".join(parts) + ".png"
    return Path.home() / "Pictures" / "AI" / kind / name


class QwenBackend:
    """
    Qwen-Image-2.1 via diffusers ``QwenImage21Pipeline`` (BF16 + sequential CPU offload on ≤24GB).
    """

    model_id = QWEN_MODEL_ID

    def __init__(self, model_id: str | None = None, dtype: str = "bfloat16") -> None:
        self.model_id = model_id or QWEN_MODEL_ID
        self.dtype = dtype
        self._pipe = None
        self._import_error: str | None = None
        self._diffusers_ok = False
        self._torch_ok = False
        self._cuda = False
        self._placement: str | None = None
        self._pipeline_class: str | None = None
        self._memory_profile_used: str | None = None
        self._probe_imports()

    def _probe_imports(self) -> None:
        try:
            import torch  # noqa: F401

            self._torch_ok = True
            self._cuda = bool(torch.cuda.is_available())
        except ImportError as e:
            self._import_error = f"torch missing: {e}"
            return
        try:
            import diffusers  # noqa: F401
            import transformers  # noqa: F401

            self._diffusers_ok = True
        except ImportError as e:
            self._import_error = f"diffusers/transformers missing: {e}"

    def _vram_gb(self) -> tuple[float | None, float | None]:
        """Return (total_gb, free_gb) from CUDA, else (None, None)."""
        if not self._torch_ok:
            return None, None
        import torch

        if not torch.cuda.is_available():
            return None, None
        free_b, total_b = torch.cuda.mem_get_info()
        return total_b / (1024**3), free_b / (1024**3)

    def _cuda_name(self) -> str | None:
        if not self._torch_ok or not self._cuda:
            return None
        import torch

        try:
            return torch.cuda.get_device_name(0)
        except Exception:
            return None

    def _should_cpu_offload(self, memory_profile: str) -> bool:
        """
        Always offload on ≤24GB VRAM.
        ``performance`` may place fully on CUDA only when free VRAM > 30GB.
        """
        total_gb, free_gb = self._vram_gb()
        if total_gb is not None and total_gb <= 24.0:
            return True
        if memory_profile == "performance" and free_gb is not None and free_gb > 30.0:
            return False
        return True

    def doctor(self) -> dict[str, Any]:
        total_gb, free_gb = self._vram_gb()
        pipe_cls = self._pipeline_class or try_import_pipeline_class()
        gpu = None
        try:
            from ai_media.shared.gpu import primary_gpu

            gpu = primary_gpu()
        except Exception:
            gpu = None

        ready = bool(self._diffusers_ok and self._cuda)
        status = "ready" if ready else "needs_setup"
        if self._pipe is not None:
            status = "pipeline_loaded"

        return {
            "model_id": self.model_id,
            "dtype": self.dtype,
            "torch": self._torch_ok,
            "diffusers": self._diffusers_ok,
            "cuda": self._cuda,
            "cuda_name": self._cuda_name() or (gpu.name if gpu else None),
            "vram_total_gb": round(total_gb, 2) if total_gb is not None else (
                round(gpu.memory_total_gb, 2) if gpu else None
            ),
            "vram_free_gb": round(free_gb, 2) if free_gb is not None else (
                round(gpu.memory_free_mb / 1024.0, 2) if gpu else None
            ),
            "pipeline_class": pipe_cls,
            "pipeline_loaded": self._pipe is not None,
            "placement": self._placement,
            "memory_profile_used": self._memory_profile_used,
            "import_error": self._import_error,
            "hint": SETUP_HINT,
            "status": status,
            "note": (
                "Real QwenImage21Pipeline path: BF16 + enable_sequential_cpu_offload() "
                "on ≤24GB; use_kv_cache=False; true_cfg_scale. "
            ),
        }

    def _ensure_pipeline(self, memory_profile: str = "auto") -> None:
        if self._pipe is not None:
            return
        if not self._torch_ok or not self._diffusers_ok:
            raise QwenNotInstalledError(self._import_error or "deps missing")

        import torch

        if not torch.cuda.is_available():
            raise QwenCudaRequiredError(
                "torch.cuda.is_available() is False. "
                "On NixOS set LD_LIBRARY_PATH=/run/opengl-driver/lib"
            )

        try:
            from diffusers import QwenImage21Pipeline
        except ImportError as e:
            raise QwenNotInstalledError(
                f"QwenImage21Pipeline not importable (need recent git diffusers): {e}"
            ) from e

        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        torch_dtype = dtype_map.get(self.dtype, torch.bfloat16)

        # Prefer dtype= (diffusers ≥0.35 / QwenImage21); fall back to torch_dtype.
        try:
            pipe = QwenImage21Pipeline.from_pretrained(
                self.model_id,
                dtype=torch_dtype,
            )
        except TypeError:
            pipe = QwenImage21Pipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch_dtype,
            )
        self._pipeline_class = type(pipe).__name__

        # On ≤24GB VRAM, model_cpu_offload OOMs (~17GB peak then kill).
        # Proven path on zionsec RTX 4090: sequential_cpu_offload + use_kv_cache=False.
        if self._should_cpu_offload(memory_profile):
            # ≤24GB: sequential only. model_cpu_offload peaked ~17GB RAM then OOM-killed.
            pipe.enable_sequential_cpu_offload()
            self._placement = "sequential_cpu_offload"
        else:
            pipe.to("cuda")
            self._placement = "cuda"

        if memory_profile in ("balanced", "low-vram", "auto"):
            for meth in ("enable_attention_slicing", "enable_vae_slicing"):
                fn = getattr(pipe, meth, None)
                if callable(fn):
                    try:
                        fn()
                    except Exception:
                        pass

        self._memory_profile_used = memory_profile
        self._pipe = pipe

    def generate(self, req: GenerateRequest | None = None, **kwargs: Any) -> Path:
        """Run text2img or img2img/edit and save a PNG. Requires CUDA."""
        if req is None:
            req = GenerateRequest(**kwargs)

        self._ensure_pipeline(req.memory_profile)

        import torch
        from PIL import Image

        assert self._pipe is not None

        prompt = req.prompt
        if req.transparent:
            prompt = apply_transparent_prompt(prompt)

        generator = None
        if req.seed is not None:
            generator = torch.Generator("cuda").manual_seed(int(req.seed))

        call: dict[str, Any] = {
            "prompt": prompt,
            "num_inference_steps": int(req.steps),
            "generator": generator,
            # Proven required on 24GB: KV cache spikes RAM during denoise.
            "use_kv_cache": False,
            # QwenImage21Pipeline uses true_cfg_scale (not guidance_scale)
            "true_cfg_scale": float(req.guidance_scale),
        }
        neg = (req.negative_prompt or "").strip()
        if not neg and float(req.guidance_scale) > 1.0:
            # CFG requires a negative prompt; empty disables true_cfg_scale.
            neg = " "
        if neg:
            call["negative_prompt"] = neg

        ref_paths: list[Path] = []
        if req.image is not None:
            ref_paths.append(Path(req.image))
        ref_paths.extend(Path(p) for p in req.images)
        # Upstream multi-ref/edit API: image=[PIL.Image, ...] (up to 10)
        if ref_paths:
            if len(ref_paths) > 10:
                raise ValueError("Qwen-Image-2.1 supports at most 10 reference images")
            pil_refs = [Image.open(p).convert("RGBA") for p in ref_paths]
            call["image"] = pil_refs
        else:
            call["width"] = int(req.width)
            call["height"] = int(req.height)

        result = self._pipe(**call)
        image = result.images[0]

        out = req.output
        if out is None:
            out = default_pictures_path(img2img=bool(ref_paths), seed=req.seed)
        else:
            out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        # Preserve RGBA when transparent / model emits alpha
        image.save(out)
        return out


def try_import_pipeline_class() -> str | None:
    """Return pipeline class name if importable, else None."""
    try:
        from diffusers import QwenImage21Pipeline  # type: ignore[attr-defined]

        return QwenImage21Pipeline.__name__
    except Exception:
        try:
            import diffusers

            return f"diffusers={getattr(diffusers, '__version__', '?')} (no QwenImage21Pipeline)"
        except ImportError:
            return None
