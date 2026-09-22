"""Shared fixtures — isolate XDG dirs."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def xdg_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / "config"
    cache = tmp_path / "cache"
    data = tmp_path / "data"
    cfg.mkdir()
    cache.mkdir()
    data.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    return tmp_path
