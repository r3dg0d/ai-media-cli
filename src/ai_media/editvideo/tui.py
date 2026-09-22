"""Minimal Rich TUI shell for editvideo jobs."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ai_media.shared.jobs import Job, jobs_root


def render_jobs(console: Console | None = None) -> None:
    console = console or Console()
    root = jobs_root("editvideo")
    table = Table(title="editvideo jobs")
    table.add_column("id")
    table.add_column("status")
    table.add_column("dir")
    for d in sorted(root.iterdir()) if root.exists() else []:
        if not d.is_dir():
            continue
        state = d / "state.json"
        if not state.is_file():
            continue
        try:
            job = Job.load("editvideo", d.name)
        except Exception:
            continue
        table.add_row(job.job_id, job.status, str(job.dir))
    console.print(table)
