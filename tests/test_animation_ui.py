from ai_media.shared.animation import BounceAnimation
from ai_media.shared.ui import banner, get_console


def test_animation_start_stop():
    anim = BounceAnimation("test", enabled=False)
    anim.start()
    anim.stop()  # must not raise


def test_banner_smoke(capsys):
    console = get_console()
    banner("t", "s", console=console)


def test_error_goes_to_stderr_not_stdout(capsys):
    from ai_media.shared.ui import error

    error("disk full")
    output = capsys.readouterr()
    assert output.out == ""
    assert "disk full" in output.err

