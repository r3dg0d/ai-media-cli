"""Video / example preprocess helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ai_media.editvideo import paths


def probe(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    out: dict[str, Any] = {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "exists": True,
        "ffprobe": False,
    }
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            proc = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0 and proc.stdout:
                data = json.loads(proc.stdout)
                out["ffprobe"] = True
                out["format"] = data.get("format", {})
                streams = data.get("streams") or []
                vstreams = [s for s in streams if s.get("codec_type") == "video"]
                if vstreams:
                    vs = vstreams[0]
                    out["width"] = vs.get("width")
                    out["height"] = vs.get("height")
                    out["codec"] = vs.get("codec_name")
                    out["nb_frames"] = vs.get("nb_frames")
        except Exception as e:  # noqa: BLE001
            out["ffprobe_error"] = str(e)
    else:
        out["note"] = "ffprobe not on PATH"
    return out


def write_probe(path: Path, out: Path) -> Path:
    data = probe(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def list_examples() -> list[dict[str, Any]]:
    repo = paths.scail_repo()
    if repo is None:
        return []
    ex = repo / "examples"
    if not ex.is_dir():
        return []
    rows = []
    for d in sorted(ex.iterdir()):
        if not d.is_dir():
            continue
        resolved = paths.resolve_example_inputs(d.name)
        rows.append(
            {
                "name": d.name,
                "path": str(d),
                "prepared": resolved is not None,
            }
        )
    return rows
