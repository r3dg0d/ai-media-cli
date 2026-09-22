"""Declared editvideo model slots (no silent downloads)."""

from __future__ import annotations

from typing import Any


def list_models() -> list[dict[str, Any]]:
    return [
        {
            "id": "scail-2",
            "name": "SCAIL-2",
            "repo": "https://github.com/zai-org/SCAIL-2",
            "status": "optional",
            "setup": "scripts/setup_scail_env.sh",
            "notes": "Wan-based character animation; large weights; --offload_model recommended on 24GB",
        },
        {
            "id": "scail-pose",
            "name": "SCAIL-Pose (preprocess)",
            "status": "optional",
            "notes": "Pose/mask prep for SCAIL-2; separate OpenMMLab stack",
        },
    ]
