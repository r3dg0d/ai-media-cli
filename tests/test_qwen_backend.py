import sys
from unittest.mock import MagicMock, patch

import pytest

from ai_media.qwen.backend import (
    GenerateRequest,
    QwenBackend,
    QwenNotInstalledError,
    apply_transparent_prompt,
    default_pictures_path,
)
from ai_media.qwen.prompting import NATIVE_ASPECT_RATIOS, aspect_to_size, enhance_prompt


def test_doctor_structure():
    d = QwenBackend().doctor()
    assert d["model_id"] == "Qwen/Qwen-Image-2.1"
    assert "hint" in d
    assert "setup_qwen_env" in d["hint"]
    assert "pipeline_class" in d
    assert "cuda_name" in d
    assert "vram_total_gb" in d or "vram_free_gb" in d


def test_generate_raises():
    be = QwenBackend()
    with pytest.raises(QwenNotInstalledError) as ei:
        be.generate(prompt="hi")
    assert "setup_qwen_env" in str(ei.value)


def _fake_torch():
    torch = MagicMock()
    gen = MagicMock()
    torch.Generator.return_value.manual_seed.return_value = gen
    return torch


def test_generate_mocked(tmp_path):
    """Unit-test generate path without GPU / weights."""
    out = tmp_path / "out.png"
    fake_img = MagicMock()
    fake_result = MagicMock()
    fake_result.images = [fake_img]

    be = QwenBackend()
    be._torch_ok = True
    be._diffusers_ok = True
    be._cuda = True
    be._pipe = MagicMock(return_value=fake_result)
    be._pipeline_class = "QwenImage21Pipeline"
    be._placement = "cpu_offload"
    be._ensure_pipeline = lambda memory_profile="auto": None  # type: ignore[method-assign]

    with patch.dict(sys.modules, {"torch": _fake_torch()}):
        path = be.generate(
            GenerateRequest(prompt="a cat", output=out, seed=42, steps=4, width=64, height=64)
        )
    assert path == out
    fake_img.save.assert_called_once_with(out)
    be._pipe.assert_called_once()
    kwargs = be._pipe.call_args.kwargs
    assert kwargs["prompt"] == "a cat"
    assert kwargs["width"] == 64
    assert kwargs["num_inference_steps"] == 4


def test_generate_img2img_passes_image_list(tmp_path):
    src = tmp_path / "in.png"
    src.write_bytes(b"fake")
    out = tmp_path / "edited.png"
    fake_img = MagicMock()
    fake_result = MagicMock()
    fake_result.images = [fake_img]
    pil_ref = MagicMock()

    be = QwenBackend()
    be._pipe = MagicMock(return_value=fake_result)
    be._ensure_pipeline = lambda memory_profile="auto": None  # type: ignore[method-assign]

    open_img = MagicMock()
    open_img.convert.return_value = pil_ref
    with (
        patch.dict(sys.modules, {"torch": _fake_torch()}),
        patch("PIL.Image.open", return_value=open_img),
    ):
        path = be.generate(
            GenerateRequest(prompt="edit me", image=src, output=out, steps=4)
        )
    assert path == out
    kwargs = be._pipe.call_args.kwargs
    assert kwargs["image"] == [pil_ref]
    assert "width" not in kwargs


def test_aspect():
    assert aspect_to_size("1:1") == (1024, 1024)
    w, h = aspect_to_size("16:9")
    assert w > h
    assert NATIVE_ASPECT_RATIOS["1:1"] == (2048, 2048)
    assert aspect_to_size("16:9", native=True) == (2752, 1536)


def test_enhance():
    assert enhance_prompt("hello", enabled=True).endswith(".")


def test_generate_request_validation():
    with pytest.raises(ValueError, match="prompt"):
        GenerateRequest(prompt="")
    with pytest.raises(ValueError, match="steps"):
        GenerateRequest(prompt="ok", steps=0)
    with pytest.raises(ValueError, match="width"):
        GenerateRequest(prompt="ok", width=32)
    with pytest.raises(ValueError, match="strength"):
        GenerateRequest(prompt="ok", strength=1.5)
    with pytest.raises(ValueError, match="memory_profile"):
        GenerateRequest(prompt="ok", memory_profile="turbo")
    req = GenerateRequest(prompt="ok", memory_profile="balanced", steps=20)
    assert req.prompt == "ok"
    assert req.memory_profile == "balanced"


def test_transparent_prompt_wrap():
    wrapped = apply_transparent_prompt("a dragon sticker")
    assert "RGBA image with transparency" in wrapped
    assert "background is transparent" in wrapped
    again = apply_transparent_prompt(wrapped)
    assert again.count("RGBA image with transparency") == 1


def test_default_pictures_path():
    p = default_pictures_path(img2img=False, seed=1)
    assert "Pictures" in p.parts
    assert "text2img" in p.parts
    assert p.suffix == ".png"
    p2 = default_pictures_path(img2img=True)
    assert "img2img" in p2.parts
