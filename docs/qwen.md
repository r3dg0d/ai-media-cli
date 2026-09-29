# Qwen-Image-2.1

- HF id: `Qwen/Qwen-Image-2.1`
- Diffusers: `QwenImage21Pipeline` (Day-0 support)
- Setup: `scripts/setup_qwen_env.sh` → venv at `$XDG_DATA_HOME/ai-media/envs/qwen`
- Requires: `transformers>=5.17`, git `diffusers`, `torch>=2.4`, CUDA
- NixOS: `export LD_LIBRARY_PATH=/run/opengl-driver/lib`
- CLIs: `text2img`, `img2img`


## NixOS PATH (zionsec)

Install wrappers as **`text2img-qwen` / `img2img-qwen`** (`scripts/install_qwen_wrappers.sh`).
Do not place Qwen as `~/.local/bin/text2img` — that shadows system LLaDA (`llada-cli`).

## Memory

- ≤24GB (e.g. RTX 4090): always `enable_model_cpu_offload()`
- `performance` may `.to("cuda")` only if free VRAM > 30GB
- CPU-only inference is refused (raises `QwenCudaRequiredError`)

## Outputs

Default PNGs land under `~/Pictures/AI/text2img` or `~/Pictures/AI/img2img`.

Weights are not in this repo. Without the GPU env, `generate()` raises `QwenNotInstalledError` with the setup hint.
