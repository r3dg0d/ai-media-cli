"""Real signals against isolated CPU-only CLI backends."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.mark.skipif(os.name != "posix", reason="POSIX process signals")
@pytest.mark.parametrize("tool", ["text2img", "img2img", "3dai", "editvideo"])
@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_installed_handler_interrupts_cli(tool, signum, tmp_path):
    ready = tmp_path / "ready"
    code = '''
import sys, time
from pathlib import Path
from importlib import import_module
tool, marker = sys.argv[1:]
modules = {"text2img":"ai_media.qwen.text2img", "img2img":"ai_media.qwen.img2img",
           "3dai":"ai_media.threedai.cli", "editvideo":"ai_media.editvideo.cli"}
cli = import_module(modules[tool])
from ai_media.shared.signals import on_shutdown
on_shutdown(lambda: Path(marker + ".callback").write_text("cleaned"))
def paused(*args, **kwargs):
    Path(marker).write_text("ready")
    time.sleep(30)
    raise AssertionError("backend resumed after signal")
if tool == "text2img":
    cli.run_text2img = paused
    args = ["fixture", "--quiet"]
elif tool == "img2img":
    cli.run_img2img = paused
    args = ["fixture", "--image", "fixture.png", "--quiet"]
elif tool == "3dai":
    cli.run_pipeline = paused
    args = ["run", "fixture.png"]
else:
    cli.run_edit = paused
    args = ["run", "fixture.mp4"]
cli.main(args)
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    for name in ["XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME"]:
        env[name] = str(tmp_path / name.lower())
    proc = subprocess.Popen([sys.executable, "-c", code, tool, str(ready)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), "fake backend did not start"
        proc.send_signal(signum)
        try:
            stdout, stderr = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            pytest.fail("installed handler did not interrupt the backend")
        assert proc.returncode == 130, (stdout, stderr)
        assert "Traceback" not in stderr
        assert "Interrupted" in stderr
        assert "backend resumed" not in stderr
        assert Path(str(ready) + ".callback").read_text() == "cleaned"
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=5)
