"""CLI --help and --version smoke tests."""

from __future__ import annotations

import pytest

from ai_media.editvideo.cli import build_parser as editvideo_parser
from ai_media.editvideo.cli import main as editvideo_main
from ai_media.qwen.img2img import build_parser as img2img_parser
from ai_media.qwen.img2img import main as img2img_main
from ai_media.qwen.text2img import build_parser as text2img_parser
from ai_media.qwen.text2img import main as text2img_main
from ai_media.shared.diagnostics import main as ai_media_main
from ai_media.threedai.cli import build_parser as threedai_parser
from ai_media.threedai.cli import main as threedai_main


@pytest.mark.parametrize(
    "build",
    [text2img_parser, img2img_parser, threedai_parser, editvideo_parser],
)
def test_help_smoke(build):
    p = build()
    help_text = p.format_help()
    assert "usage:" in help_text.lower() or "Usage" in help_text


def test_text2img_version(capsys):
    with pytest.raises(SystemExit) as ei:
        text2img_main(["--version"])
    assert ei.value.code == 0
    assert capsys.readouterr().out.strip()


def test_img2img_version(capsys):
    with pytest.raises(SystemExit) as ei:
        img2img_main(["--version"])
    assert ei.value.code == 0


def test_3dai_version(capsys):
    with pytest.raises(SystemExit) as ei:
        threedai_main(["--version"])
    assert ei.value.code == 0


def test_editvideo_version(capsys):
    with pytest.raises(SystemExit) as ei:
        editvideo_main(["--version"])
    assert ei.value.code == 0


def test_text2img_flags_present():
    help_text = text2img_parser().format_help()
    for flag in [
        "--seed",
        "--steps",
        "--width",
        "--height",
        "--aspect",
        "--memory",
        "--transparent",
        "--preview",
        "--monitor",
        "--enhance-prompt",
        "--doctor",
        "--benchmark",
    ]:
        assert flag in help_text


def test_ai_media_doctor_json(xdg_tmp, capsys):
    with pytest.raises(SystemExit) as ei:
        ai_media_main(["doctor", "--json"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "version" in out
    assert "terminal_graphics" in out
