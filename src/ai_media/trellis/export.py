"""Mesh / asset export helpers (stub formats)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_manifest(path: Path, assets: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(assets, indent=2) + "\n", encoding="utf-8")
    return path


def supported_formats() -> list[str]:
    return ["glb", "obj", "ply", "manifest.json"]
