"""editvideo job helpers on XDG cache."""

from __future__ import annotations

from typing import Any

from ai_media.shared.jobs import Job


def new_job(**meta: Any) -> Job:
    job = Job.create("editvideo", **meta)
    job.status = "created"
    job.save()
    return job
