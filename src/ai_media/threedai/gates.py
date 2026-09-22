"""Fail-closed gates — refuse cloud / unsafe transitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateResult:
    ok: bool
    reason: str = ""


def refuse_cloud(url: str | None) -> GateResult:
    if url and (url.startswith("http://") or url.startswith("https://")):
        return GateResult(False, "cloud URLs are not allowed (fail-closed)")
    return GateResult(True)


def require_local_path(path: str | None) -> GateResult:
    if not path:
        return GateResult(False, "local path required")
    if path.startswith("http://") or path.startswith("https://"):
        return GateResult(False, "remote paths blocked")
    return GateResult(True)


def check_stage_preconditions(stage: str, *, has_mesh: bool = False) -> GateResult:
    needs_mesh = stage in {"retopo", "uv", "bake", "texture", "package"}
    if needs_mesh and not has_mesh:
        return GateResult(False, f"stage {stage} requires a local mesh")
    return GateResult(True)
