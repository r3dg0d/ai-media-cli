"""Invalid requests must fail before backend probing and keep stderr useful."""

from unittest.mock import Mock

import pytest
from PIL import Image

from ai_media.qwen import editing, generation, img2img, text2img
from ai_media.qwen.backend import QwenCudaRequiredError, QwenNotInstalledError
from ai_media.qwen.prompting import aspect_to_size


@pytest.mark.parametrize("cli", [text2img, img2img])
@pytest.mark.parametrize(
    "options",
    [["--steps", "0"], ["--guidance-scale", "nan"], ["--guidance-scale", "inf"]],
)
def test_invalid_request_never_probes_backend(cli, options, xdg_tmp, monkeypatch, capsys):
    image = xdg_tmp / "input.png"
    Image.new("RGB", (64, 64)).save(image)
    backend = Mock(side_effect=AssertionError("invalid request probed backend"))
    monkeypatch.setattr(generation, "QwenBackend", backend)
    monkeypatch.setattr(editing, "QwenBackend", backend)
    monkeypatch.setattr(cli, "QwenBackend", backend)
    args = ["test", "--quiet", "--model", "example/model", *options]
    if cli is img2img:
        args += ["--image", str(image)]
    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == 2
    backend.assert_not_called()
    output = capsys.readouterr()
    assert output.out == ""
    assert "error:" in output.err


@pytest.mark.parametrize("aspect", ["0:0", "1:0", "-1:2", "nan:1", "inf:1", "1x1", "bad"])
def test_invalid_aspect_is_usage_error(aspect, xdg_tmp, capsys):
    with pytest.raises(SystemExit) as exc:
        text2img.main(["test", "--aspect", aspect, "--quiet"])
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "--aspect:" in output.err


@pytest.mark.parametrize("cli", [text2img, img2img])
@pytest.mark.parametrize(
    "failure,code",
    [(QwenNotInstalledError(), 2), (QwenCudaRequiredError(), 2), (PermissionError("denied"), 1)],
)
@pytest.mark.parametrize("quiet", [True, False])
def test_runtime_failure_reported_once_on_stderr(
    cli, failure, code, quiet, xdg_tmp, monkeypatch, capsys
):
    run = "run_text2img" if cli is text2img else "run_img2img"
    monkeypatch.setattr(cli, run, Mock(side_effect=failure))
    args = ["test"] + (["--quiet"] if quiet else [])
    if cli is img2img:
        args += ["--image", str(xdg_tmp / "input.png")]
    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == code
    output = capsys.readouterr()
    assert output.err.count("error:") == 1
    assert str(failure) in output.err
    if quiet:
        assert output.out == ""


def test_missing_input_reported_on_stderr(xdg_tmp, capsys):
    with pytest.raises(SystemExit) as exc:
        img2img.main(["edit", "--image", str(xdg_tmp / "missing.png"), "--quiet"])
    assert exc.value.code == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "missing.png" in output.err


@pytest.mark.parametrize(
    "cli,options",
    [(text2img, ["--width", "32"]), (img2img, ["--strength", "nan"])],
)
def test_tool_specific_validation(cli, options, xdg_tmp, monkeypatch, capsys):
    image = xdg_tmp / "input.png"
    Image.new("RGB", (64, 64)).save(image)
    monkeypatch.setattr(generation, "QwenBackend", Mock(side_effect=AssertionError("probed")))
    monkeypatch.setattr(editing, "QwenBackend", Mock(side_effect=AssertionError("probed")))
    args = ["test", "--quiet", *options]
    if cli is img2img:
        args += ["--image", str(image)]
    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("cli", [text2img, img2img])
def test_malformed_config_is_usage_error(cli, xdg_tmp, capsys):
    config = xdg_tmp / "config" / "ai-media" / "config.toml"
    config.parent.mkdir()
    config.write_text("default_steps = [", encoding="utf-8")
    args = ["test", "--quiet"]
    if cli is img2img:
        args += ["--image", str(xdg_tmp / "input.png")]
    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == 2
    assert "could not load config:" in capsys.readouterr().err


def test_debug_preserves_runtime_traceback(xdg_tmp, monkeypatch):
    monkeypatch.setattr(text2img, "run_text2img", Mock(side_effect=PermissionError("denied")))
    with pytest.raises(PermissionError, match="denied"):
        text2img.main(["test", "--debug", "--quiet"])


def test_valid_custom_aspects():
    assert aspect_to_size("768x512") == (768, 512)
    assert aspect_to_size("2:1") == (1024, 512)
    assert aspect_to_size("1e308:1e308") == (1024, 1024)


def test_valid_orchestration_writes_image_and_metadata(xdg_tmp, monkeypatch):
    class Backend:
        model_id = "test/local"

        def generate(self, request):
            Image.new("RGB", (request.width, request.height)).save(request.output)
            return request.output

    monkeypatch.setattr(generation, "QwenBackend", lambda model_id: Backend())
    output = xdg_tmp / "output.png"
    with pytest.raises(SystemExit) as exc:
        text2img.main(
            [
                "test",
                "--output",
                str(output),
                "--width",
                "64",
                "--height",
                "64",
                "--steps",
                "1",
                "--quiet",
                "--no-preview",
            ]
        )
    assert exc.value.code == 0
    with Image.open(output) as image:
        assert image.size == (64, 64)
    assert output.with_suffix(".png.json").is_file()
