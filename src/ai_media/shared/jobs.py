"""XDG cache job directories and JSON state files."""

from __future__ import annotations

import json
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_media.shared.config import xdg_cache_home


def jobs_root(tool: str) -> Path:
    root = xdg_cache_home() / "ai-media" / "jobs" / tool
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class Job:
    tool: str
    job_id: str
    status: str = "created"
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    meta: dict[str, Any] = field(default_factory=dict)
    stages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def dir(self) -> Path:
        return jobs_root(self.tool) / self.job_id

    def state_path(self) -> Path:
        return self.dir / "state.json"

    def save(self) -> Path:
        self.updated_at = datetime.now(UTC).isoformat()
        self.dir.mkdir(parents=True, exist_ok=True)
        data = {
            "tool": self.tool,
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "meta": self.meta,
            "stages": self.stages,
        }
        path = self.state_path()
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path

    def add_stage(self, name: str, status: str, **extra: Any) -> None:
        entry = {"name": name, "status": status, **extra}
        self.stages.append(entry)
        self.status = status if status in {"failed", "cancelled"} else self.status
        if status == "running":
            self.status = "running"
        if status == "done" and name == self.stages[-1]["name"]:
            # caller may set completed explicitly
            pass
        self.save()

    @contextmanager
    def cancel_on_interrupt(self) -> Iterator[None]:
        """Persist cancellation of active work, then preserve the interrupt."""
        try:
            yield
        except KeyboardInterrupt:
            if self.status not in {"completed", "done", "planned", "dry_run"}:
                try:
                    self.add_stage("interrupt", "cancelled")
                except Exception as error:
                    # Storage errors must not hide the original cancellation.
                    print(f"warning: could not record cancelled job: {error}", file=sys.stderr)
            raise

    @classmethod
    def create(cls, tool: str, **meta: Any) -> Job:
        job = cls(tool=tool, job_id=uuid.uuid4().hex[:12], meta=dict(meta))
        job.save()
        return job

    @classmethod
    def load(cls, tool: str, job_id: str) -> Job:
        path = jobs_root(tool) / job_id / "state.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            tool=data["tool"],
            job_id=data["job_id"],
            status=data.get("status", "unknown"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            meta=data.get("meta", {}),
            stages=data.get("stages", []),
        )
