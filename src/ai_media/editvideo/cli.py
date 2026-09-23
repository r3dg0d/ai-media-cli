"""editvideo CLI — SCAIL-2 character animation / video jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai_media import __version__
from ai_media.editvideo.doctor import doctor, print_doctor
from ai_media.editvideo.models import list_models
from ai_media.editvideo.preprocess import list_examples
from ai_media.editvideo.runner import run_edit
from ai_media.editvideo.tui import render_jobs
from ai_media.shared.jobs import Job
from ai_media.shared.media_preview import open_video
from ai_media.shared.signals import install_sigint_handler
from ai_media.shared.ui import banner, error, success


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="editvideo",
        description="Local SCAIL-2 character animation / video edit jobs",
    )
    p.add_argument("--version", action="store_true")
    p.add_argument("--json", action="store_true", help="JSON output where applicable")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--config", default=None, help="Unused reserved config path")
    p.add_argument("--dry-run", action="store_true", help="Print/plan without GPU generate")

    sub = p.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Run SCAIL-2 generate or preprocess-only")
    run_p.add_argument("video", nargs="?", default=None, help="Local video (preprocess-only)")
    run_p.add_argument("-p", "--prompt", default="")
    run_p.add_argument("--example", default=None, help="Bundled SCAIL example e.g. animation_001")
    run_p.add_argument("--image", default=None)
    run_p.add_argument("--mask-image", dest="mask_image", default=None)
    run_p.add_argument("--pose", default=None, help="Driving / rendered pose video")
    run_p.add_argument("--mask-video", dest="mask_video", default=None)
    run_p.add_argument("--model", default="SCAIL-14B", choices=["SCAIL-14B", "SCAIL-1.3B"])
    run_p.add_argument("--target-h", type=int, default=512)
    run_p.add_argument("--target-w", type=int, default=896)
    run_p.add_argument("--steps", type=int, default=40)
    run_p.add_argument("--seed", type=int, default=-1)
    run_p.add_argument("--offload-model", action=argparse.BooleanOptionalAction, default=True)
    run_p.add_argument("--t5-cpu", action=argparse.BooleanOptionalAction, default=True)
    run_p.add_argument("--replace", action="store_true")
    run_p.add_argument("-o", "--output", default=None)
    run_p.add_argument("--open", dest="do_open", action=argparse.BooleanOptionalAction, default=True)
    run_p.add_argument("--dry-run", action="store_true")

    smoke = sub.add_parser("smoke", help="Short smoke using example animation_001")
    smoke.add_argument("--example", default="animation_001")
    smoke.add_argument("-p", "--prompt", default="The character is moving naturally.")
    smoke.add_argument("--steps", type=int, default=20)
    smoke.add_argument("--target-h", type=int, default=512)
    smoke.add_argument("--target-w", type=int, default=896)
    smoke.add_argument("--model", default="SCAIL-14B")
    smoke.add_argument("--dry-run", action="store_true")
    smoke.add_argument("-o", "--output", default=None)

    st = sub.add_parser("status", help="Job status")
    st.add_argument("job_id")

    open_p = sub.add_parser("open", help="Open a completed job video (xdg-open)")
    open_p.add_argument("job_id")

    sub.add_parser("jobs", help="List jobs (TUI table)")
    sub.add_parser("models", help="List SCAIL models / weight honesty notes")
    sub.add_parser("examples", help="List SCAIL-2 bundled examples")
    sub.add_parser("doctor", help="Env / CUDA / weights / import diagnostics")
    return p


def main(argv: list[str] | None = None) -> None:
    install_sigint_handler()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        sys.exit(0)

    dry = "--dry-run" in (argv if argv is not None else sys.argv[1:])

    if args.cmd is None:
        parser.print_help()
        sys.exit(0)

    if args.cmd == "doctor":
        data = doctor()
        code = print_doctor(data, quiet=args.quiet)
        sys.exit(code)

    if args.cmd == "models":
        print(json.dumps(list_models(), indent=2))
        sys.exit(0)

    if args.cmd == "examples":
        print(json.dumps(list_examples(), indent=2))
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
        payload = {
            "job_id": job.job_id,
            "status": job.status,
            "stages": job.stages,
            "meta": job.meta,
            "dir": str(job.dir),
        }
        print(json.dumps(payload, indent=2))
        sys.exit(0)

    if args.cmd == "open":
        try:
            job = Job.load("editvideo", args.job_id)
        except FileNotFoundError:
            error(f"job not found: {args.job_id}")
            sys.exit(1)
        out = job.meta.get("output")
        if not out or not Path(out).is_file():
            # fall back to any mp4 in job dir
            mp4s = list(job.dir.glob("*.mp4"))
            if not mp4s:
                error("no output video on job")
                sys.exit(1)
            out = str(mp4s[0])
        ok = open_video(out)
        if not ok:
            error("xdg-open / video opener failed (not Kitty)")
            sys.exit(2)
        success(f"opened {out}")
        sys.exit(0)

    if args.cmd in {"run", "smoke"}:
        if not args.quiet:
            banner("editvideo", "SCAIL-2")
        try:
            if args.cmd == "smoke":
                job = run_edit(
                    prompt=args.prompt,
                    example=args.example,
                    model=args.model,
                    target_h=args.target_h,
                    target_w=args.target_w,
                    steps=args.steps,
                    output=args.output,
                    dry_run=dry,
                    open_video=not dry,
                )
            else:
                job = run_edit(
                    args.video,
                    prompt=args.prompt,
                    example=args.example,
                    image=args.image,
                    mask_image=args.mask_image,
                    pose=args.pose,
                    mask_video=args.mask_video,
                    model=args.model,
                    target_h=args.target_h,
                    target_w=args.target_w,
                    steps=args.steps,
                    offload=args.offload_model,
                    t5_cpu=args.t5_cpu,
                    replace=args.replace,
                    seed=args.seed,
                    output=args.output,
                    dry_run=dry or args.dry_run,
                    open_video=args.do_open and not (dry or args.dry_run),
                )
        except (RuntimeError, FileNotFoundError, OSError) as e:
            error(str(e))
            sys.exit(2)
        if args.json:
            print(
                json.dumps(
                    {
                        "job_id": job.job_id,
                        "status": job.status,
                        "dir": str(job.dir),
                        "meta": job.meta,
                    },
                    indent=2,
                )
            )
        else:
            success(f"job {job.job_id} → {job.status}")
            if job.meta.get("output"):
                success(f"output: {job.meta['output']}")
        sys.exit(0 if job.status in {"completed", "planned", "dry_run"} else 2)

    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
