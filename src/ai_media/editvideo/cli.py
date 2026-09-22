"""editvideo CLI skeleton."""

from __future__ import annotations

import argparse
import json
import sys

from ai_media import __version__
from ai_media.editvideo.models import list_models
from ai_media.editvideo.runner import run_edit
from ai_media.editvideo.tui import render_jobs
from ai_media.shared.jobs import Job
from ai_media.shared.signals import install_sigint_handler
from ai_media.shared.ui import banner, error, success


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="editvideo", description="Local video edit jobs")
    p.add_argument("--version", action="store_true")
    sub = p.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Plan/preprocess a local video job")
    run_p.add_argument("video", help="Local video path")
    run_p.add_argument("-p", "--prompt", default=None)

    st = sub.add_parser("status", help="Job status")
    st.add_argument("job_id")

    sub.add_parser("jobs", help="List jobs (TUI table)")
    sub.add_parser("models", help="List model placeholders")
    sub.add_parser("doctor", help="Diagnostics")
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
        print(json.dumps({"tool": "editvideo", "cloud": False, "models": list_models()}, indent=2))
        sys.exit(0)
    if args.cmd == "models":
        print(json.dumps(list_models(), indent=2))
        sys.exit(0)
    if args.cmd == "jobs":
        render_jobs()
        sys.exit(0)
    if args.cmd == "status":
        try:
            job = Job.load("editvideo", args.job_id)
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
        banner("editvideo", "local job runner")
        try:
            job = run_edit(args.video, prompt=args.prompt)
        except (RuntimeError, FileNotFoundError) as e:
            error(str(e))
            sys.exit(2)
        success(f"job {job.job_id} → {job.status}")
        sys.exit(0)
    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
