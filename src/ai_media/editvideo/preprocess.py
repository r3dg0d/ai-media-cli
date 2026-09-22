"""Video preprocess stubs (probe / scene markers as JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def probe(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    return {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "exists": True,
        "ffprobe": False,
        "note": "ffprobe integration deferred",
    }


def write_probe(path: Path, out: Path) -> Path:
    data = probe(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out
