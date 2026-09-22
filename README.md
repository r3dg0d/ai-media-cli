# ai-media-cli

Local-first AI media CLI suite for Vincent ([@r3dg0d](https://github.com/r3dg0d)).

| Command | Role |
| ------- | ---- |
| `text2img` | Qwen-Image-2.1 text → image |
| `img2img` | Qwen-Image-2.1 image edit / img2img |
| `3dai` | Multi-stage 3D asset pipeline (local, fail-closed) |
| `editvideo` | Video edit job runner + TUI shell |
| `ai-media doctor` | Environment / GPU / graphics diagnostics |

Model weights are **not** bundled. Shared infrastructure (terminal graphics,
preview, config, Rich UX, nvidia-smi parsing) works without a GPU.

## Install

```bash
git clone https://github.com/r3dg0d/ai-media-cli.git
cd ai-media-cli
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Optional Qwen deps (GPU machine):

```bash
./scripts/setup_qwen_env.sh
pip install -e ".[qwen]"
```

## Quick examples

```bash
text2img --help
text2img --doctor
img2img --help
3dai --help
editvideo --help
ai-media doctor
```

## Terminal image preview

`TerminalImageRenderer` prefers Kitty graphics protocol, then chafa, then ANSI
blocks, else none (non-TTY). Animations stop cleanly before pixels are written.

## Config

XDG path: `~/.config/ai-media/config.toml` (created with defaults on first load).

## Status

See [STATUS.md](STATUS.md) for implemented vs GPU-pending work.
License: [MIT](LICENSE). Third-party model notices: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
