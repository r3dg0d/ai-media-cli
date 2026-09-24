
import pytest

from ai_media.editvideo.runner import run_edit
from ai_media.threedai.gates import refuse_cloud
from ai_media.threedai.pipeline import run_pipeline


def test_refuse_cloud():
    assert refuse_cloud("https://evil.example/x").ok is False
    assert refuse_cloud("/tmp/local.png").ok is True


@pytest.fixture()
def trellis_absent(monkeypatch):
    from ai_media.trellis.backend import TrellisBackend

    monkeypatch.setattr(TrellisBackend, "doctor", lambda self: {"status": "missing"})


def test_pipeline_local(xdg_tmp, tmp_path, trellis_absent):
    img = tmp_path / "in.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    job = run_pipeline(str(img), stages=["ingest", "reconstruct"])
    assert job.state_path().is_file()
    assert (job.dir / "ingest.json").is_file()


def test_pipeline_package_needs_mesh(xdg_tmp, tmp_path, trellis_absent):
    img = tmp_path / "in.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    with pytest.raises(RuntimeError, match="requires a local mesh"):
        run_pipeline(str(img), stages=["ingest", "reconstruct", "package"])


def test_pipeline_blocks_url(xdg_tmp):
    with pytest.raises(RuntimeError):
        run_pipeline("https://example.com/a.png")


def test_editvideo_run(xdg_tmp, tmp_path):
    vid = tmp_path / "c.mp4"
    vid.write_bytes(b"\x00\x00")
    job = run_edit(str(vid), prompt="test")
    assert job.status == "planned"
    assert (job.dir / "probe.json").is_file()


def test_editvideo_blocks_url(xdg_tmp):
    with pytest.raises(RuntimeError):
        run_edit("https://example.com/v.mp4")
