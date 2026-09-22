"""Image → 3D reconstruction orchestration stub."""

from __future__ import annotations

from pathlib import Path

from ai_media.trellis.backend import TrellisBackend


def reconstruct_image(image: Path, *, output_dir: Path | None = None) -> Path:
    be = TrellisBackend()
    return be.reconstruct(image, output_dir=output_dir)
