"""editvideo job runner — SCAIL-2 generate path (fail-closed)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_media.editvideo import paths
from ai_media.editvideo.backend import GenerateRequest, ScailNotReadyError, run_generate
from ai_media.editvideo.jobs import new_job
from ai_media.editvideo.models import default_model
from ai_media.editvideo.preprocess import write_probe
from ai_media.shared.jobs import Job
from ai_media.shared.media_preview import prompt_open_video


def run_edit(
    video: str | None = None,
    *,
    prompt: str | None = None,
    allow_cloud: bool = False,
    example: str | None = None,
    image: str | None = None,
    mask_image: str | None = None,
    pose: str | None = None,
    mask_video: str | None = None,
    model: str | None = None,
    target_h: int = 512,
    target_w: int = 896,
    steps: int = 40,
    offload: bool = True,
    t5_cpu: bool = True,
    replace: bool = False,
    seed: int = -1,
    output: str | None = None,
    dry_run: bool = False,
    open_video: bool = True,
    skip_generate: bool = False,
) -> Job:
    if allow_cloud:
        raise RuntimeError("cloud edits are disabled (fail-closed)")

    inputs: dict[str, Path] | None = None
    if example:
        inputs = paths.resolve_example_inputs(example)
        if inputs is None:
            raise FileNotFoundError(
                f"example '{example}' not prepared under SCAIL-2/examples "
                "(need ref(+mask) + rendered_v2 + rendered_mask_v2)"
            )
    elif image and mask_image and pose and mask_video:
        inputs = {
            "image": Path(image),
            "mask_image": Path(mask_image),
            "pose": Path(pose),
            "mask_video": Path(mask_video),
        }
        for p in inputs.values():
            if not p.is_file():
                raise FileNotFoundError(p)
    elif video:
        if video.startswith("http://") or video.startswith("https://"):
            raise RuntimeError("remote video URLs blocked")
        path = Path(video)
        if not path.is_file():
            raise FileNotFoundError(path)
        # Legacy preprocess-only mode when SCAIL inputs are incomplete
        job = new_job(video=str(path.resolve()), prompt=prompt, mode="preprocess_only")
        with job.cancel_on_interrupt():
            job.add_stage("preprocess", "running")
            probe_path = write_probe(path, job.dir / "probe.json")
            job.add_stage("preprocess", "done", path=str(probe_path))
            job.add_stage(
                "models",
                "skipped",
                reason=(
                    "need --example NAME or --image/--mask-image/--pose/--mask-video "
                    "for SCAIL-2 generate"
                ),
            )
            plan = {
                "prompt": prompt,
                "stages": ["preprocess"],
                "cloud": False,
                "note": "preprocess-only; no generate",
            }
            (job.dir / "plan.json").write_text(
                json.dumps(plan, indent=2) + "\n", encoding="utf-8"
            )
            job.status = "planned"
            job.save()
            return job
    else:
        raise RuntimeError(
            "provide --example, or --image + --mask-image + --pose + --mask-video, "
            "or a local video path for preprocess-only"
        )

    model_name = (model or default_model()).upper()
    out_dir = paths.default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_file = Path(output) if output else out_dir / f"scail2_{example or 'run'}_{stamp}.mp4"

    job = new_job(
        prompt=prompt,
        example=example,
        model=model_name,
        image=str(inputs["image"]),
        pose=str(inputs["pose"]),
        mode="scail2",
    )
    with job.cancel_on_interrupt():
        job.add_stage("preprocess", "running")
        write_probe(inputs["pose"], job.dir / "pose_probe.json")
        job.add_stage("preprocess", "done")

        plan: dict[str, Any] = {
            "prompt": prompt or "",
            "model": model_name,
            "target_h": target_h,
            "target_w": target_w,
            "steps": steps,
            "offload": offload,
            "t5_cpu": t5_cpu,
            "replace": replace,
            "inputs": {k: str(v) for k, v in inputs.items()},
            "save_file": str(save_file),
            "cloud": False,
            "dry_run": dry_run,
        }
        (job.dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        job.add_stage("plan", "done")

        if skip_generate:
            job.add_stage("generate", "skipped", reason="skip_generate")
            job.status = "planned"
            job.save()
            return job

        req = GenerateRequest(
            image=inputs["image"],
            mask_image=inputs["mask_image"],
            pose=inputs["pose"],
            mask_video=inputs["mask_video"],
            prompt=prompt or "",
            save_file=save_file,
            model=model_name,
            target_h=target_h,
            target_w=target_w,
            sample_steps=steps,
            offload_model=offload,
            t5_cpu=t5_cpu,
            replace_flag=replace,
            seed=seed,
            dry_run=dry_run,
        )

        job.add_stage("generate", "running")
        job.status = "running"
        job.save()
        try:
            meta = run_generate(req)
            (job.dir / "generate.json").write_text(
                json.dumps(meta, indent=2) + "\n", encoding="utf-8"
            )
            if dry_run:
                job.add_stage("generate", "dry_run")
                job.status = "dry_run"
            else:
                if not save_file.is_file() or save_file.stat().st_size == 0:
                    raise RuntimeError(
                        "generation returned success but output video is missing or empty: "
                        f"{save_file}"
                    )
                # copy into job dir for bookkeeping
                dest = job.dir / save_file.name
                if save_file.resolve() != dest.resolve():
                    shutil.copy2(save_file, dest)
                job.meta["output"] = str(save_file.resolve())
                job.add_stage("generate", "done", output=str(save_file))
                job.status = "completed"
                if open_video:
                    prompt_open_video(save_file)
        except ScailNotReadyError as e:
            job.add_stage("generate", "failed", error=str(e))
            job.status = "failed"
            job.save()
            raise
        except Exception as e:  # noqa: BLE001
            job.add_stage("generate", "failed", error=str(e))
            job.status = "failed"
            job.save()
            raise

        job.save()
        return job
