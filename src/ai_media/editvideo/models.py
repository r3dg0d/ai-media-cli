"""Model registry placeholders (no downloads)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRef:
    name: str
    purpose: str
    install_hint: str


REGISTRY = [
    ModelRef("scail-2", "pose / video", "see THIRD_PARTY_NOTICES.md + research notes"),
    ModelRef("placeholder-inpaint", "frame edit", "not bundled"),
]


def list_models() -> list[dict[str, str]]:
    return [{"name": m.name, "purpose": m.purpose, "hint": m.install_hint} for m in REGISTRY]
