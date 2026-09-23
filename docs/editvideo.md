# editvideo (SCAIL-2)

Local **character animation / video** jobs backed by [zai-org/SCAIL-2](https://github.com/zai-org/SCAIL-2)
(`wan-scail2` branch) via `generate.py`.

Cloud URLs are refused. Weights are **not** bundled.

## Honest limitations

| Item | Reality |
|------|---------|
| **SCAIL-1.3B** | Config exists in `wan/configs`, but **no official 1.3B weights** ship on `zai-org/SCAIL-2`. HF card is the **14B** pack (~**82 GiB** `usedStorage`). `editvideo` refuses `--model SCAIL-1.3B` unless you bring your own matching weights (not supported out of the box). |
| **RTX 4090 24GB** | Use `--offload-model` (default) and `--t5-cpu` (default). Still may OOM — do not fake success. Prefer low res (`512×896`) and fewer `--steps` for smoke. |
| **Pose stack** | Full SCAIL-Pose (MMPose / SAM3) is heavy. First smoke should use **bundled** `examples/animation_001` (already has `ref.jpg`, masks, `rendered_v2.mp4`). |
| **flash_attn** | Listed in upstream `requirements.txt`; may fail to build on NixOS. Setup script installs it best-effort. |
| **wan branch** | After `hf download`, run `convert.py` → `SCAIL-2.safetensors` before generate. |

## Setup (zionsec / NixOS)

```bash
# 1) SCAIL clone (already expected at ~/Projects/SCAIL-2 @ wan-scail2)
export AI_MEDIA_SCAIL_REPO=$HOME/Projects/SCAIL-2

# 2) Env + deps (no weights yet)
./scripts/setup_scail_env.sh

# 3) Explicit giant download + convert (user-approved)
./scripts/setup_scail_env.sh --download-weights --convert

# 4) Point ~/.local/bin/editvideo at scail env (fixes qwen mis-wire)
./scripts/install_editvideo_wrapper.sh

export LD_LIBRARY_PATH=/run/opengl-driver/lib:${LD_LIBRARY_PATH:-}
editvideo doctor
```

Weights land under `~/.local/share/ai-media/models/scail-2/` (plus HF cache).

## Commands

```bash
editvideo --help
editvideo --version
editvideo doctor
editvideo models
editvideo examples
editvideo jobs
editvideo status <job_id>
editvideo open <job_id>          # xdg-open / configured opener — not Kitty

# Preprocess-only (probe a local mp4; no GPU)
editvideo run ./clip.mp4 -p "note"

# Full generate from bundled example (skip pose preprocess)
editvideo run --example animation_001 -p "The girl is dancing" --steps 20

# Smoke helper
editvideo smoke --example animation_001 --steps 20

# Dry-run (prints argv / plan, no GPU)
editvideo smoke --dry-run
```

Long GPU jobs on zionsec:

```bash
systemd-run --user --unit=editvideo-smoke \
  -p WorkingDirectory=$HOME \
  -- \
  bash -lc 'export LD_LIBRARY_PATH=/run/opengl-driver/lib:$LD_LIBRARY_PATH; \
    editvideo smoke --example animation_001 --steps 20 -o $HOME/Pictures/AI/editvideo/smoke.mp4'
```

Outputs default to `~/Pictures/AI/editvideo/` (else `~/Videos/AI/`).

## Architecture

```
editvideo CLI
  ├─ doctor      → env, CUDA, weights, SCAIL import, example readiness
  ├─ run/smoke   → Job (XDG cache) → generate.py subprocess (offload)
  ├─ jobs/status → shared Job store
  └─ open        → xdg-open / config video_opener
```

Env vars: `AI_MEDIA_SCAIL_VENV`, `AI_MEDIA_SCAIL_REPO`, `AI_MEDIA_SCAIL_MODELS`.
