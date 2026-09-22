from ai_media.shared.jobs import Job
from ai_media.shared.signals import (
    is_shutdown_requested,
    on_shutdown,
    request_shutdown,
    reset_for_tests,
)


def test_shutdown_callback():
    reset_for_tests()
    called = []
    on_shutdown(lambda: called.append(1))
    request_shutdown()
    assert is_shutdown_requested()
    assert called == [1]
    reset_for_tests()


def test_job_roundtrip(xdg_tmp):
    job = Job.create("testtool", foo="bar")
    assert job.state_path().is_file()
    job.add_stage("a", "done")
    loaded = Job.load("testtool", job.job_id)
    assert loaded.meta["foo"] == "bar"
    assert loaded.stages[-1]["name"] == "a"
