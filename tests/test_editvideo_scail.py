"""editvideo SCAIL wiring tests (no GPU / no weights required)."""

from __future__ import annotations

import pytest

from ai_media.editvideo.backend import GenerateRequest, ScailNotReadyError, build_generate_argv
from ai_media.editvideo.doctor import doctor
from ai_media.editvideo.models import list_models
from ai_media.editvideo.runner import run_edit


def test_models_honest_about_1_3b():
    models = {m["name"]: m for m in list_models()}
    assert models["SCAIL-14B"]["weights_available"] is True
    assert models["SCAIL-1.3B"]["weights_available"] is False


def test_doctor_json_shape(xdg_tmp):
    d = doctor()
    assert d["tool"] == "editvideo"
    assert d["cloud"] is False
    assert "blockers" in d
    assert "ready" in d
    assert "weights" in d


def test_editvideo_preprocess_only(xdg_tmp, tmp_path):
    vid = tmp_path / "c.mp4"
    vid.write_bytes(b"\x00\x00")
    job = run_edit(str(vid), prompt="test")
    assert job.status == "planned"
    assert (job.dir / "probe.json").is_file()


def test_editvideo_blocks_url(xdg_tmp):
    with pytest.raises(RuntimeError):
        run_edit("https://example.com/v.mp4")


def test_scail_1_3b_refused(monkeypatch, tmp_path):
    # Minimal fake repo + weights so we reach the 1.3B guard
    repo = tmp_path / "SCAIL-2"
    repo.mkdir()
    (repo / "generate.py").write_text("# stub\n", encoding="utf-8")
    ckpt = tmp_path / "ckpt"
    ckpt.mkdir()
    (ckpt / "Wan2.1_VAE.pth").write_bytes(b"x")
    (ckpt / "model").mkdir()
    (ckpt / "umt5-xxl").mkdir()
    st = tmp_path / "SCAIL-2.safetensors"
    st.write_bytes(b"y" * 10)

    monkeypatch.setenv("AI_MEDIA_SCAIL_REPO", str(repo))
    monkeypatch.setenv("AI_MEDIA_SCAIL_MODELS", str(tmp_path / "models"))
    # point finders via env models dir containing safetensors + fake ckpt discovery
    # find_ckpt_dir searches models_root — put layout there
    models = tmp_path / "models"
    models.mkdir()
    for name in ("Wan2.1_VAE.pth",):
        (models / name).write_bytes(b"x")
    (models / "model").mkdir()
    (models / "umt5-xxl").mkdir()
    (models / "SCAIL-2.safetensors").write_bytes(b"y" * 10)

    img = tmp_path / "a.jpg"
    img.write_bytes(b"img")
    req = GenerateRequest(
        image=img,
        mask_image=img,
        pose=img,
        mask_video=img,
        model="SCAIL-1.3B",
    )
    with pytest.raises(ScailNotReadyError, match="1.3B"):
        build_generate_argv(req)


def test_cli_help():
    from ai_media.editvideo.cli import build_parser

    p = build_parser()
    help_text = p.format_help()
    assert "doctor" in help_text
    assert "smoke" in help_text


@pytest.mark.parametrize("result", ["missing", "empty", "valid", "dry_run"])
def test_runner_requires_output_before_completion(xdg_tmp, tmp_path, monkeypatch, result):
    from ai_media.editvideo import runner
    from ai_media.shared.jobs import Job, jobs_root

    source = tmp_path / "input.bin"
    source.write_bytes(b"fixture")
    output = tmp_path / "generated.mp4"
    monkeypatch.setattr(runner, "write_probe", lambda *args: None)

    def fake_generate(req):
        if result == "empty":
            req.save_file.write_bytes(b"")
        elif result == "valid":
            req.save_file.write_bytes(b"fake video bytes")
        return {"returncode": 0, "dry_run": req.dry_run}

    monkeypatch.setattr(runner, "run_generate", fake_generate)
    kwargs = dict(image=str(source), mask_image=str(source), pose=str(source),
                  mask_video=str(source), output=str(output), open_video=False,
                  dry_run=result == "dry_run")
    if result in {"missing", "empty"}:
        with pytest.raises(RuntimeError, match="missing or empty"):
            run_edit(**kwargs)
        states = list(jobs_root("editvideo").glob("*/state.json"))
        assert len(states) == 1
        loaded = Job.load("editvideo", states[0].parent.name)
        assert loaded.status == "failed"
        assert loaded.stages[-1]["status"] == "failed"
        assert "output" not in loaded.meta
    else:
        job = run_edit(**kwargs)
        assert job.status == ("dry_run" if result == "dry_run" else "completed")
        if result == "valid":
            assert job.meta["output"] == str(output.resolve())
            assert (job.dir / output.name).read_bytes() == output.read_bytes()
        else:
            assert not output.exists()
            assert "output" not in job.meta


@pytest.mark.parametrize("result", ["missing", "empty", "valid", "dry_run"])
def test_backend_validates_explicit_output(tmp_path, monkeypatch, result):
    from types import SimpleNamespace

    from ai_media.editvideo import backend

    output = tmp_path / "generated.mp4"
    req = GenerateRequest(image=output, mask_image=output, pose=output, mask_video=output,
                          save_file=output, dry_run=result == "dry_run")
    monkeypatch.setattr(backend, "build_generate_argv", lambda req: ["fake-generate"])
    monkeypatch.setattr(backend.paths, "scail_repo", lambda: tmp_path)

    def fake_run(*args, **kwargs):
        if result == "empty":
            output.write_bytes(b"")
        elif result == "valid":
            output.write_bytes(b"fake video bytes")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    if result in {"missing", "empty"}:
        with pytest.raises(RuntimeError, match="missing or empty"):
            backend.run_generate(req)
    else:
        meta = backend.run_generate(req)
        if result == "valid":
            assert meta["output"] == str(output.resolve())
        else:
            assert "returncode" not in meta
            assert not output.exists()
