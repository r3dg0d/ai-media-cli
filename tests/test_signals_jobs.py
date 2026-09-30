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


def test_shutdown_callbacks_are_once_only_even_after_callback_failure():
    reset_for_tests()
    called = []

    def failing():
        called.append("failing")
        raise RuntimeError("fixture callback failure")

    on_shutdown(failing)
    on_shutdown(lambda: called.append("next"))
    try:
        request_shutdown()
        request_shutdown()
        assert called == ["failing", "next"]
    finally:
        reset_for_tests()
