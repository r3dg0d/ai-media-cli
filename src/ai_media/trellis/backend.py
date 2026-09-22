"""TRELLIS backend stub — no cloud, no weight download."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

SETUP_HINT = "Install TRELLIS deps on a GPU machine; see docs/trellis.md"


class TrellisNotInstalledError(RuntimeError):
    def __init__(self, detail: str = "") -> None:
        extra = f" ({detail})" if detail else ""
        super().__init__(f"TRELLIS backend not ready. {SETUP_HINT}{extra}")


@dataclass
class TrellisBackend:
    model_id: str = "microsoft/TRELLIS-image-large"

    def doctor(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "status": "stub",
            "hint": SETUP_HINT,
        }

    def reconstruct(self, image: Path, **kwargs: Any) -> Path:
        raise TrellisNotInstalledError("reconstruct not wired")
