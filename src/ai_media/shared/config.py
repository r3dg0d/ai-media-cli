"""XDG config for ai-media (~/.config/ai-media/config.toml)."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import tomli_w

PreviewMode = Literal["auto", "always", "never", "prompt"]
MemoryProfile = Literal["auto", "performance", "balanced", "low-vram"]
OpenMode = Literal["auto", "always", "never", "prompt"]


def xdg_config_home() -> Path:
    raw = os.environ.get("XDG_CONFIG_HOME")
    if raw:
        return Path(raw)
    return Path.home() / ".config"


def xdg_cache_home() -> Path:
    raw = os.environ.get("XDG_CACHE_HOME")
    if raw:
        return Path(raw)
    return Path.home() / ".cache"


def xdg_data_home() -> Path:
    raw = os.environ.get("XDG_DATA_HOME")
    if raw:
        return Path(raw)
    return Path.home() / ".local" / "share"


@dataclass
class Config:
    """User-facing defaults matching the ai-media mission."""

    # Preview / open behavior
    preview_mode: PreviewMode = "auto"
    open_image_mode: OpenMode = "auto"
    open_video_mode: OpenMode = "prompt"
    image_viewer: str = "imv"
    video_opener: str = "xdg-open"

    # Generation defaults
    memory_profile: MemoryProfile = "auto"
    default_steps: int = 40
    default_width: int = 1024
    default_height: int = 1024
    default_format: str = "png"
    write_metadata: bool = True
    enhance_prompt: bool = False

    # UX
    quiet: bool = False
    verbose: bool = False
    show_monitor: bool = True
    animation: bool = True

    # Models (HF ids / local paths — no weights bundled)
    qwen_model_id: str = "Qwen/Qwen-Image-2.1"
    qwen_dtype: str = "bfloat16"
    trellis_model_id: str = "microsoft/TRELLIS-image-large"

    # Paths
    output_dir: str = field(default_factory=lambda: str(Path.cwd() / "outputs"))

    def config_path(self) -> Path:
        return xdg_config_home() / "ai-media" / "config.toml"

    def cache_dir(self) -> Path:
        return xdg_cache_home() / "ai-media"

    def jobs_dir(self) -> Path:
        return self.cache_dir() / "jobs"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


_DEFAULT = Config()


def load_config(path: Path | None = None, *, create: bool = True) -> Config:
    """Load TOML config; optionally write defaults if missing."""
    cfg_path = path or _DEFAULT.config_path()
    if not cfg_path.exists():
        cfg = Config()
        if create:
            save_config(cfg, cfg_path)
        return cfg
    with cfg_path.open("rb") as fh:
        data = tomllib.load(fh)
    return Config.from_dict(data)


def save_config(cfg: Config, path: Path | None = None) -> Path:
    cfg_path = path or cfg.config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with cfg_path.open("wb") as fh:
        tomli_w.dump(cfg.to_dict(), fh)
    return cfg_path
