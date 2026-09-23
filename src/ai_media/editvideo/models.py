"""SCAIL-2 model registry with honest weight availability notes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRef:
    name: str
    purpose: str
    install_hint: str
    weights_available: bool
    recommended_vram_gb: int


REGISTRY = [
    ModelRef(
        name="SCAIL-14B",
        purpose="SCAIL-2 end-to-end / pose-driven character animation (wan branch)",
        install_hint=(
            "hf download zai-org/SCAIL-2 (~82 GiB total: Wan VAE + umt5-xxl + DiT). "
            "Then convert for wan branch: python convert.py --scail-dir DIR "
            "--save-path ~/.local/share/ai-media/models/scail-2/SCAIL-2.safetensors. "
            "On 24GB use --offload_model true and prefer --t5-cpu."
        ),
        weights_available=True,
        recommended_vram_gb=24,
    ),
    ModelRef(
        name="SCAIL-1.3B",
        purpose="Smaller SCAIL config present in wan code; official weights NOT published for SCAIL-2",
        install_hint=(
            "generate.py accepts --model SCAIL-1.3B and configs/config-1.3b.json exists, "
            "but zai-org/SCAIL-2 only ships the 14B checkpoint. No separate 1.3B HF repo. "
            "editvideo will refuse SCAIL-1.3B unless you provide a matching local safetensors."
        ),
        weights_available=False,
        recommended_vram_gb=12,
    ),
]


def list_models() -> list[dict[str, object]]:
    return [
        {
            "name": m.name,
            "purpose": m.purpose,
            "hint": m.install_hint,
            "weights_available": m.weights_available,
            "recommended_vram_gb": m.recommended_vram_gb,
        }
        for m in REGISTRY
    ]


def default_model() -> str:
    """Prefer 1.3B only when weights exist; otherwise SCAIL-14B."""
    return "SCAIL-14B"
