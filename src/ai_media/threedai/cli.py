"""3dai CLI skeleton."""

from __future__ import annotations

import argparse
import json
import sys

from ai_media import __version__
from ai_media.shared.jobs import Job
from ai_media.shared.signals import install_sigint_handler
from ai_media.shared.ui import banner, error, success
from ai_media.threedai.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="3dai", description="Local 3D AI asset pipeline")
    p.add_argument("--version", action="store_true")
    sub = p.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Run pipeline on a local input")
    run_p.add_argument("input", help="Local image/mesh path")
    run_p.add_argument("--stages", nargs="*", default=None)

    status_p = sub.add_parser("status", help="Show job status")
    status_p.add_argument("job_id")

    sub.add_parser("doctor", help="3dai diagnostics")
    return p


def main(argv: list[str] | None = None) -> None:
    install_sigint_handler()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        sys.exit(0)
    if args.cmd is None:
        parser.print_help()
        sys.exit(0)
    if args.cmd == "doctor":
        from ai_media.trellis.backend import TrellisBackend
        report = {"tool": "3dai", "cloud": False, "trellis": TrellisBackend().doctor()}
        print(json.dumps(report, indent=2))
        sys.exit(0)
    if args.cmd == "status":
        try:
            job = Job.load("3dai", args.job_id)
        except FileNotFoundError:
            error(f"job not found: {args.job_id}")
            sys.exit(1)
        print(json.dumps({
            "job_id": job.job_id,
            "status": job.status,
            "stages": job.stages,
            "dir": str(job.dir),
        }, indent=2))
        sys.exit(0)
    if args.cmd == "run":
        banner("3dai", "local pipeline")
        try:
            job = run_pipeline(args.input, stages=args.stages)
        except RuntimeError as e:
            error(str(e))
            sys.exit(2)
        success(f"job {job.job_id} → {job.status} ({job.dir})")
        sys.exit(0)
    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
