"""XDG config load/save."""

from __future__ import annotations

from ai_media.shared.config import Config, load_config, save_config


def test_load_creates_defaults(xdg_tmp):
    cfg = load_config(create=True)
    assert cfg.config_path().is_file()
    assert cfg.preview_mode == "auto"
    assert cfg.memory_profile == "auto"
    assert cfg.qwen_model_id == "Qwen/Qwen-Image-2.1"
    assert cfg.open_video_mode == "prompt"


def test_roundtrip(xdg_tmp):
    cfg = Config(default_steps=28, quiet=True)
    path = save_config(cfg)
    loaded = load_config(path, create=False)
    assert loaded.default_steps == 28
    assert loaded.quiet is True
