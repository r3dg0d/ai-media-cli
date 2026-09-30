"""Interrupted CPU-only workflows preserve honest job state."""

import pytest

from ai_media.shared.jobs import Job, jobs_root


@pytest.mark.parametrize("phase", ["preprocess_only", "scail_preprocess", "scail_generate", "3dai"])
def test_interrupted_workflow_persists_cancelled_job(phase, xdg_tmp, monkeypatch):
    from ai_media.editvideo import runner
    from ai_media.threedai import pipeline

    source = xdg_tmp / "input.bin"
    source.write_bytes(b"fixture")

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    if phase == "3dai":
        monkeypatch.setattr(pipeline, "_run_stage", interrupted)
        def invoke():
            return pipeline.run_pipeline(str(source), stages=["ingest"])
        tool = "3dai"
    else:
        monkeypatch.setattr(runner, "write_probe",
                            (lambda *args: None) if phase == "scail_generate" else interrupted)
        monkeypatch.setattr(runner, "run_generate", interrupted)
        if phase == "preprocess_only":
            def invoke():
                return runner.run_edit(str(source))
        else:
            def invoke():
                return runner.run_edit(image=str(source), mask_image=str(source),
                                       pose=str(source), mask_video=str(source),
                                       output=str(xdg_tmp / "output.mp4"), open_video=False)
        tool = "editvideo"
    with pytest.raises(KeyboardInterrupt):
        invoke()
    states = list(jobs_root(tool).glob("*/state.json"))
    assert len(states) == 1
    loaded = Job.load(tool, states[0].parent.name)
    assert loaded.status == "cancelled"
    assert loaded.stages[-1] == {"name": "interrupt", "status": "cancelled"}
    assert "output" not in loaded.meta


@pytest.mark.parametrize("status", ["completed", "done", "planned", "dry_run"])
def test_interrupt_after_terminal_job_does_not_relabel_it(status, xdg_tmp):
    job = Job.create("fixture")
    job.status = status
    job.save()
    with pytest.raises(KeyboardInterrupt), job.cancel_on_interrupt():
        raise KeyboardInterrupt
    assert Job.load("fixture", job.job_id).status == status


def test_storage_failure_does_not_replace_keyboard_interrupt(xdg_tmp, monkeypatch, capsys):
    job = Job.create("fixture")

    def blocked():
        raise PermissionError("fixture store unavailable")

    monkeypatch.setattr(job, "save", blocked)
    with pytest.raises(KeyboardInterrupt), job.cancel_on_interrupt():
        raise KeyboardInterrupt
    assert "could not record cancelled job" in capsys.readouterr().err
