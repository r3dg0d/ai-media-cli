"""ai-media doctor — environment diagnostics CLI entry."""

from __future__ import annotations

import argparse
import json
import shutil
import sys

from ai_media import __version__
from ai_media.shared.config import load_config
from ai_media.shared.gpu import nvidia_smi_available, query_gpus
from ai_media.shared.hardware import probe_hardware
from ai_media.shared.memory import resolve_profile
from ai_media.shared.terminal_graphics import TerminalImageRenderer
from ai_media.shared.ui import banner, get_console, info_panel


def run_doctor(*, as_json: bool = False) -> int:
    hw = probe_hardware()
    caps = TerminalImageRenderer.detect().capabilities()
    mem = resolve_profile("auto")
    cfg = load_config(create=True)

    report = {
        "version": __version__,
        "hardware": hw.as_dict(),
        "nvidia_smi": nvidia_smi_available(),
        "gpus": [g.as_dict() for g in query_gpus()],
        "memory_profile": mem.as_dict(),
        "terminal_graphics": caps.as_dict(),
        "tools": {
            "chafa": shutil.which("chafa") is not None,
            "imv": shutil.which("imv") is not None,
            "xdg-open": shutil.which("xdg-open") is not None,
        },
        "config_path": str(cfg.config_path()),
        "qwen": _qwen_status(),
    }

    if as_json:
        print(json.dumps(report, indent=2))
        return 0

    console = get_console()
    banner("ai-media doctor", f"v{__version__}", console=console)
    info_panel("Hardware", {
        "system": hw.system,
        "machine": hw.machine,
        "python": hw.python,
        "cpus": hw.cpu_count,
        "ram_mb": hw.ram_total_mb,
        "gpus": len(hw.gpus),
    }, console=console)
    info_panel("Terminal graphics", caps.as_dict(), console=console)
    info_panel("Memory (auto)", mem.as_dict(), console=console)
    info_panel("Qwen backend", report["qwen"], console=console)
    return 0


def _qwen_status() -> dict[str, object]:
    status: dict[str, object] = {
        "diffusers": False,
        "transformers": False,
        "torch": False,
        "cuda": False,
        "hint": "run scripts/setup_qwen_env.sh",
    }
    try:
        import torch  # noqa: F401

        status["torch"] = True
        status["cuda"] = bool(torch.cuda.is_available())
    except ImportError:
        pass
    try:
        import diffusers  # noqa: F401

        status["diffusers"] = True
    except ImportError:
        pass
    try:
        import transformers  # noqa: F401

        status["transformers"] = True
    except ImportError:
        pass
    return status


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ai-media", description="ai-media utilities")
    sub = parser.add_subparsers(dest="cmd")
    doctor = sub.add_parser("doctor", help="Environment diagnostics")
    doctor.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--version", action="store_true", help="Print version")
    args = parser.parse_args(argv)
    if args.version or args.cmd is None:
        if args.cmd is None and not args.version:
            # default to doctor when no subcommand? print help-ish
            if args.version:
                print(__version__)
                sys.exit(0)
            parser.print_help()
            sys.exit(0)
        print(__version__)
        sys.exit(0)
    if args.cmd == "doctor":
        sys.exit(run_doctor(as_json=args.json))
    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
