"""Placeholder pipeline stages that write JSON state (no external cloud)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_media.shared.jobs import Job
from ai_media.threedai.gates import check_stage_preconditions, refuse_cloud, require_local_path
from ai_media.threedai.state import Stage, advance, create_job


def run_pipeline(
    input_path: str,
    *,
    stages: list[str] | None = None,
    allow_cloud: bool = False,
) -> Job:
    if allow_cloud:
        raise RuntimeError("allow_cloud is not supported — fail-closed")
    g = require_local_path(input_path)
    if not g.ok:
        raise RuntimeError(g.reason)
    g2 = refuse_cloud(input_path)
    if not g2.ok:
        raise RuntimeError(g2.reason)

    job = create_job(input=input_path)
    # Copy a tiny marker into job dir
    marker = job.dir / "input_ref.txt"
    marker.write_text(str(Path(input_path).resolve()) + "\n", encoding="utf-8")

    planned = stages or [
        "ingest",
        "reconstruct",
        "retopo",
        "uv",
        "bake",
        "texture",
        "critique",
        "package",
    ]
    has_mesh = False
    for name in planned:
        pre = check_stage_preconditions(name, has_mesh=has_mesh)
        if not pre.ok and name != "ingest" and name != "reconstruct":
            # reconstruct is stubbed as producing a placeholder mesh json
            if name == "reconstruct":
                pass
            else:
                advance(job, Stage.FAILED, "failed", reason=pre.reason)
                raise RuntimeError(pre.reason)
        stage = Stage(name) if name in Stage._value2member_map_ else Stage.INGEST
        result = _run_stage(job, name)
        if name == "reconstruct":
            if result.get("status") == "error":
                advance(job, Stage.FAILED, "failed", reason=result.get("error", "reconstruct failed"))
                raise RuntimeError(result.get("error", "reconstruct failed"))
            if result.get("status") == "ok":
                has_mesh = True
            else:
                # skipped — still continue but note no mesh
                has_mesh = False
        advance(job, stage, "done", result=result)
    advance(job, Stage.DONE, "done")
    return job


def _run_stage(job: Job, name: str) -> dict[str, Any]:
    out = job.dir / f"{name}.json"
    payload: dict[str, Any] = {"stage": name, "status": "placeholder", "cloud": False}
    if name == "reconstruct":
        try:
            from ai_media.trellis.backend import TrellisBackend

            be = TrellisBackend()
            doc = be.doctor()
            payload["doctor"] = {
                k: doc.get(k)
                for k in ("status", "o_voxel", "pipeline_class", "import_error")
            }
            if doc.get("pipeline_class") and doc.get("o_voxel"):
                src = (job.dir / "input_ref.txt").read_text(encoding="utf-8").strip()
                glb = be.reconstruct(Path(src), output_dir=job.dir / "mesh")
                payload["status"] = "ok"
                payload["glb"] = str(glb)
            else:
                payload["status"] = "skipped"
                payload["reason"] = (
                    doc.get("import_error")
                    or doc.get("o_voxel_error")
                    or "trellis/o_voxel not ready — run scripts/setup_trellis_env.sh"
                )
        except Exception as e:  # noqa: BLE001
            payload["status"] = "error"
            payload["error"] = str(e)
    out.write_text(__import__("json").dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"path": str(out), **{k: v for k, v in payload.items() if k != "doctor"}}
