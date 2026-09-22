"""Memory profiles: auto / performance / balanced / low-vram."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ai_media.shared.gpu import GpuInfo, primary_gpu

MemoryProfile = Literal["auto", "performance", "balanced", "low-vram"]


@dataclass(frozen=True)
class MemorySettings:
    profile: MemoryProfile
    resolved: Literal["performance", "balanced", "low-vram"]
    enable_attention_slicing: bool
    enable_vae_slicing: bool
    enable_cpu_offload: bool
    enable_sequential_offload: bool
    preferred_dtype: str  # bfloat16 | float16 | float32
    max_batch: int
    notes: str

    def as_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "resolved": self.resolved,
            "enable_attention_slicing": self.enable_attention_slicing,
            "enable_vae_slicing": self.enable_vae_slicing,
            "enable_cpu_offload": self.enable_cpu_offload,
            "enable_sequential_offload": self.enable_sequential_offload,
            "preferred_dtype": self.preferred_dtype,
            "max_batch": self.max_batch,
            "notes": self.notes,
        }


_PRESETS: dict[str, dict[str, object]] = {
    "performance": {
        "enable_attention_slicing": False,
        "enable_vae_slicing": False,
        "enable_cpu_offload": False,
        "enable_sequential_offload": False,
        "preferred_dtype": "bfloat16",
        "max_batch": 4,
        "notes": "Full GPU residency; needs ample VRAM.",
    },
    "balanced": {
        "enable_attention_slicing": True,
        "enable_vae_slicing": True,
        "enable_cpu_offload": True,
        "enable_sequential_offload": True,
        "preferred_dtype": "bfloat16",
        "max_batch": 1,
        "notes": "Sequential CPU offload for ~12–24 GB (RTX 4090 / system RAM capped).",
    },
    "low-vram": {
        "enable_attention_slicing": True,
        "enable_vae_slicing": True,
        "enable_cpu_offload": True,
        "enable_sequential_offload": True,
        "preferred_dtype": "float16",
        "max_batch": 1,
        "notes": "Aggressive offload for ≤8–10 GB VRAM.",
    },
}


def resolve_profile(
    profile: MemoryProfile = "auto",
    gpu: GpuInfo | None = None,
) -> MemorySettings:
    if profile == "auto":
        gpu = gpu if gpu is not None else primary_gpu()
        if gpu is None:
            resolved: Literal["performance", "balanced", "low-vram"] = "low-vram"
        elif gpu.memory_total_mb >= 20000:
            # 24GB cards still need offload when host RAM ~32GB (no swap).
            resolved = "balanced"
        elif gpu.memory_total_mb >= 11000:
            resolved = "balanced"
        else:
            resolved = "low-vram"
    else:
        resolved = profile  # type: ignore[assignment]

    preset = _PRESETS[resolved]
    return MemorySettings(
        profile=profile,
        resolved=resolved,
        enable_attention_slicing=bool(preset["enable_attention_slicing"]),
        enable_vae_slicing=bool(preset["enable_vae_slicing"]),
        enable_cpu_offload=bool(preset["enable_cpu_offload"]),
        enable_sequential_offload=bool(preset["enable_sequential_offload"]),
        preferred_dtype=str(preset["preferred_dtype"]),
        max_batch=int(preset["max_batch"]),  # type: ignore[arg-type]
        notes=str(preset["notes"]),
    )
