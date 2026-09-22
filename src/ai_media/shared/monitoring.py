"""Lightweight GPU/CPU monitoring snapshots for --monitor."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ai_media.shared.gpu import GpuInfo, query_gpus
from ai_media.shared.hardware import probe_hardware


@dataclass
class MonitorSnapshot:
    timestamp: float
    gpus: list[GpuInfo] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "gpus": [g.as_dict() for g in self.gpus],
            "note": self.note,
        }


class Monitor:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.history: list[MonitorSnapshot] = []

    def snapshot(self, note: str = "") -> MonitorSnapshot:
        snap = MonitorSnapshot(
            timestamp=time.time(),
            gpus=query_gpus() if self.enabled else [],
            note=note,
        )
        if self.enabled:
            self.history.append(snap)
        return snap

    def summary(self) -> dict[str, object]:
        hw = probe_hardware()
        last = self.history[-1].as_dict() if self.history else None
        return {"hardware": hw.as_dict(), "last": last, "samples": len(self.history)}
