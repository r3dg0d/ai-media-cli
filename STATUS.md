# Status — ai-media-cli 0.1.0

Last updated: 2026-10-02 19:30 PT (published repo + editvideo cancel persist)

## Implemented (unit-testable, no GPU)

| Area | Status |
| ---- | ------ |
| Repo layout, MIT license, docs, CI, flake.nix | done |
| XDG config `~/.config/ai-media/config.toml` | done |
| Kitty / chafa / ANSI / none terminal graphics | done |
| media_preview (TTY-safe prompts, imv/xdg-open argv) | done |
| Rich UI + BounceAnimation (stop before render) | done |
| nvidia-smi parse, memory profiles, hardware probe | done |
| Jobs under XDG cache, signals Ctrl+C | done |
| CLI entry points: text2img, img2img, 3dai, editvideo, ai-media | done |
| Full argparse surfaces + `--help` / `--version` / `--doctor` | done |
| Qwen backend pluggable interface + NotInstalled errors | done |
| **Qwen `QwenImage21Pipeline` real generate path** (BF16, CPU offload ≤24GB, CUDA required) | done |
| Native 2K aspect map + `--native-aspect`; RGBA prompt wrap | done |
| Defaults under `~/Pictures/AI/{text2img,img2img}` | done |
| `scripts/setup_qwen_env.sh` → XDG venv + `transformers>=5.17` + NixOS `LD_LIBRARY_PATH` | done |
| TRELLIS backend/export stubs | done |
| 3dai state machine + fail-closed gates + JSON stages | done |
| editvideo runner/preprocess/TUI list + fail-closed | done |
| pytest suite (graphics, preview, config, CLI, jobs, gates, Qwen mocks) | done |
| setup scripts (no weight download by default) | done |

## Needs GPU / local model env

| Area | Notes |
| ---- | ----- |
| Qwen weights on disk | Run `scripts/setup_qwen_env.sh` then optionally `--download-weights` (not done in CI) |
| img2img / multi-ref on GPU | Wired (`image=[PIL…]`); verify on 4090 with offload |
| Prompt enhance via LLM | Currently light local polish only |
| TRELLIS reconstruct | Upstream install + weights |
| editvideo model stages | SCAIL/etc. placeholders; preprocess only |
| 3dai real retopo/bake/texture | Stages write JSON placeholders |
| chafa/imv integration on target box | Detected via PATH in doctor |
| asciinema demos under `demos/casts/` | `.gitkeep` only |

## Non-goals (this foundation)

- Bundling or downloading multi-GB weights in CI
- Cloud inference APIs
- Secrets / credentials

## 2026-09-22 — text2img / img2img working on an RTX 4090 (NixOS)

- Backend: BF16 + `enable_sequential_cpu_offload()` + `use_kv_cache=False` + `true_cfg_scale`
- Proven CLI runs:
  - `text2img` → `~/Pictures/AI/text2img/cli-fox-seed7.png` (512², 8 steps, ~29s)
  - `img2img` → `~/Pictures/AI/img2img/astronaut-watercolor-seed9.png` (1024², 8 steps, ~79s)

## 2026-09-29 — Phase 4 PATH honesty (zionsec)

- System `text2img` / `img2img` = **llada-cli** (do not shadow from `~/.local/bin`).
- Qwen exposed as `text2img-qwen` / `img2img-qwen` via `scripts/install_qwen_wrappers.sh`.
- Umbrella `~/.local/bin/ai-media` → XDG qwen venv `ai-media doctor`.
- Desktop entries: `~/.local/share/applications/matrix-ai-*.desktop` (help/doctor only).
- GitHub: published at https://github.com/r3dg0d/ai-media-cli (`origin` on this clone).
- Full Nix of Qwen/TRELLIS/SCAIL still blocked (CUDA wheels + huge weights); keep venv wrappers.

## 2026-09-22 — preview + TRELLIS stack

- Ghostty/Kitty graphics: `GHOSTTY_*` + `AI_MEDIA_GRAPHICS` + `--graphics`
- imv open fallbacks; `open_image_mode=auto`
- TRELLIS.2 cloned; env with torch/xformers; CUDA exts built (cumesh, flex_gemm, nvdiffrast, o_voxel)
- `3dai doctor` → trellis status **ready** (weights download separate)
- SCAIL-2 cloned; `scripts/setup_scail_env.sh` scaffold (weights not pulled)

## 2026-10-02 — editvideo completion is saved before open

- Finished editvideo jobs are marked `completed` (with the output path) before the open-video prompt. Interrupting that prompt no longer leaves the job at `running`.
