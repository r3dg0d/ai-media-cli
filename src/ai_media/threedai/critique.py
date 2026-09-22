"""critique stage helper (placeholder — local only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def run(job_dir: Path, **kwargs: Any) -> Path:
    path = Path(job_dir) / "critique.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"stage": "critique", "kwargs": kwargs}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
