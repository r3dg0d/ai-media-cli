"""Job runner — placeholder stages, fail-closed for cloud."""

from __future__ import annotations

import json
from pathlib import Path

from ai_media.editvideo.jobs import new_job
from ai_media.editvideo.preprocess import write_probe
from ai_media.shared.jobs import Job


def run_edit(
    video: str,
    *,
    prompt: str | None = None,
    allow_cloud: bool = False,
) -> Job:
    if allow_cloud:
        raise RuntimeError("cloud edits are disabled (fail-closed)")
    if video.startswith("http://") or video.startswith("https://"):
        raise RuntimeError("remote video URLs blocked")
    path = Path(video)
    if not path.is_file():
        raise FileNotFoundError(path)

    job = new_job(video=str(path.resolve()), prompt=prompt)
    job.add_stage("preprocess", "running")
    probe_path = write_probe(path, job.dir / "probe.json")
    job.add_stage("preprocess", "done", path=str(probe_path))

    job.add_stage("models", "skipped", reason="weights not installed")
    plan = {
        "prompt": prompt,
        "stages": ["preprocess", "edit", "mux"],
        "cloud": False,
    }
    (job.dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    job.add_stage("plan", "done")
    job.status = "planned"
    job.save()
    return job
