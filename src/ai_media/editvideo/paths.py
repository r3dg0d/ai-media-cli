"""XDG / env paths for SCAIL-2 editvideo."""

from __future__ import annotations

import os
from pathlib import Path

from ai_media.shared.config import xdg_cache_home, xdg_data_home


HF_REPO_ID = "zai-org/SCAIL-2"
DEFAULT_SCAIL_REPO_CANDIDATES = (
    Path.home() / "Projects" / "SCAIL-2",
    Path("/home/neo/Projects/SCAIL-2"),
)


def scail_venv() -> Path:
    override = os.environ.get("AI_MEDIA_SCAIL_VENV")
    if override:
        return Path(override).expanduser()
    return xdg_data_home() / "ai-media" / "envs" / "scail"


def scail_repo() -> Path | None:
    override = os.environ.get("AI_MEDIA_SCAIL_REPO")
    if override:
        p = Path(override).expanduser()
        return p if p.is_dir() else None
    for cand in DEFAULT_SCAIL_REPO_CANDIDATES:
        if cand.is_dir() and (cand / "generate.py").is_file():
            return cand
    return None


def models_root() -> Path:
    override = os.environ.get("AI_MEDIA_SCAIL_MODELS")
    if override:
        return Path(override).expanduser()
    return xdg_data_home() / "ai-media" / "models" / "scail-2"


def hf_hub_cache() -> Path:
    return Path(os.environ.get("HF_HUB_CACHE", xdg_cache_home() / "huggingface" / "hub"))


def default_output_dir() -> Path:
    pics = Path.home() / "Pictures" / "AI" / "editvideo"
    vids = Path.home() / "Videos" / "AI"
    if pics.parent.is_dir() or not vids.parent.is_dir():
        return pics
    return vids


def find_ckpt_dir() -> Path | None:
    """Locate downloaded SCAIL-2 checkpoint directory (Wan VAE + model + umt5)."""
    roots = [
        models_root(),
        Path(os.environ.get("HF_HOME", xdg_cache_home() / "huggingface")),
        hf_hub_cache(),
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        # Explicit layout
        if (root / "Wan2.1_VAE.pth").is_file() and (root / "model").is_dir():
            return root
        # snapshot dirs
        for snap in root.rglob("Wan2.1_VAE.pth"):
            parent = snap.parent
            if parent in seen:
                continue
            seen.add(parent)
            if (parent / "model").is_dir() and (parent / "umt5-xxl").is_dir():
                return parent
    return None


def find_safetensors(ckpt_dir: Path | None = None) -> Path | None:
    """Converted wan-branch SCAIL-2.safetensors (optional but preferred)."""
    candidates: list[Path] = []
    root = models_root()
    candidates.extend(
        [
            root / "SCAIL-2.safetensors",
            root / "scail-2.safetensors",
        ]
    )
    if ckpt_dir is not None:
        candidates.extend(
            [
                ckpt_dir / "SCAIL-2.safetensors",
                ckpt_dir.parent / "SCAIL-2.safetensors",
            ]
        )
    for p in candidates:
        if p.is_file():
            return p
    # any large safetensors near models root
    if root.is_dir():
        for p in sorted(root.glob("*.safetensors")):
            if p.stat().st_size > 1_000_000_000:
                return p
    return None


def example_dir(name: str = "animation_001") -> Path | None:
    repo = scail_repo()
    if repo is None:
        return None
    d = repo / "examples" / name
    return d if d.is_dir() else None


def resolve_example_inputs(name: str = "animation_001") -> dict[str, Path] | None:
    """Bundled preprocessed assets — skip SCAIL-Pose for smoke."""
    d = example_dir(name)
    if d is None:
        return None
    image = d / "ref.jpg"
    if not image.is_file():
        image = d / "ref.png"
    mask_image = d / "ref_mask.jpg"
    if not mask_image.is_file():
        mask_image = d / "ref_mask.png"
    pose = d / "rendered_v2.mp4"
    mask_video = d / "rendered_mask_v2.mp4"
    required = {
        "image": image,
        "mask_image": mask_image,
        "pose": pose,
        "mask_video": mask_video,
    }
    if all(p.is_file() for p in required.values()):
        return required
    return None
