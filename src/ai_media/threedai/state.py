"""Pipeline state machine persisted under XDG cache jobs."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from ai_media.shared.jobs import Job


class Stage(StrEnum):
    INIT = "init"
    INGEST = "ingest"
    RECONSTRUCT = "reconstruct"
    RETOPO = "retopo"
    UV = "uv"
    BAKE = "bake"
    TEXTURE = "texture"
    CRITIQUE = "critique"
    PACKAGE = "package"
    DONE = "done"
    FAILED = "failed"


ORDER = [
    Stage.INIT,
    Stage.INGEST,
    Stage.RECONSTRUCT,
    Stage.RETOPO,
    Stage.UV,
    Stage.BAKE,
    Stage.TEXTURE,
    Stage.CRITIQUE,
    Stage.PACKAGE,
    Stage.DONE,
]


def create_job(**meta: Any) -> Job:
    job = Job.create("3dai", **meta)
    job.status = Stage.INIT.value
    job.add_stage(Stage.INIT.value, "done")
    job.save()
    return job


def advance(job: Job, stage: Stage, status: str = "done", **extra: Any) -> Job:
    job.add_stage(stage.value, status, **extra)
    if status == "failed":
        job.status = Stage.FAILED.value
    elif stage is Stage.DONE:
        job.status = Stage.DONE.value
    else:
        job.status = stage.value
    job.save()
    return job
