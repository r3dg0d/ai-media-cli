from ai_media.shared.gpu import GpuInfo, query_gpus
from ai_media.shared.memory import resolve_profile


def test_resolve_auto_no_gpu():
    s = resolve_profile("auto", gpu=None)
    assert s.resolved == "low-vram"
    assert s.enable_cpu_offload is True


def test_resolve_performance():
    gpu = GpuInfo(0, "Test", 24576, 0, 24576, 0, 40)
    s = resolve_profile("auto", gpu=gpu)
    assert s.resolved == "performance"


def test_resolve_balanced():
    gpu = GpuInfo(0, "Test", 12288, 0, 12288, 0, 40)
    s = resolve_profile("auto", gpu=gpu)
    assert s.resolved == "balanced"


def test_explicit_low_vram():
    s = resolve_profile("low-vram")
    assert s.resolved == "low-vram"


def test_query_gpus_no_crash():
    # May be empty in CI
    assert isinstance(query_gpus(), list)
