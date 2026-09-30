# ai-media-cli

Local-first AI media CLI suite for Vincent ([@r3dg0d](https://github.com/r3dg0d)).

| Command | Role |
| ------- | ---- |
| `text2img` / `img2img` *(Python entry points)* | Qwen-Image-2.1 text → image / edit |
| `text2img-qwen` / `img2img-qwen` *(NixOS wrappers)* | Same Qwen CLIs without shadowing system LLaDA |
| `3dai` | Multi-stage 3D asset pipeline (TRELLIS.2, fail-closed) |
| `editvideo` | SCAIL-2 character animation / video jobs |
| `ai-media doctor` | Environment / GPU / graphics diagnostics |

Model weights are **not** bundled. Shared infrastructure (terminal graphics,
preview, config, Rich UX, nvidia-smi parsing) works without a GPU.

## Workstation PATH note (NixOS / zionsec)

On this machine, **system** `text2img` / `img2img` / `llada-image` come from
**llada-cli** (LLaDA-Image Turbo) via `modules/local-ai-tools.nix`.

ai-media’s Qwen CLIs must **not** be installed as `~/.local/bin/text2img` —
that shadows LLaDA when `~/.local/bin` is prepended in `.bashrc`. Use:

```bash
./scripts/install_qwen_wrappers.sh
# → ~/.local/bin/text2img-qwen
# → ~/.local/bin/img2img-qwen
# → ~/.local/bin/ai-media
# Optional on machines without system LLaDA:
# INSTALL_AS_TEXT2IMG=1 ./scripts/install_qwen_wrappers.sh
```

| Name on PATH | Engine |
| ------------ | ------ |
| `text2img` / `img2img` | LLaDA (Nix system package) |
| `text2img-qwen` / `img2img-qwen` | Qwen-Image-2.1 (this repo + XDG venv) |

## Install

```bash
git clone https://github.com/r3dg0d/ai-media-cli.git   # when published
cd ai-media-cli   # or: cd ~/Projects/ai-media
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Optional Qwen deps (GPU machine):

```bash
./scripts/setup_qwen_env.sh
pip install -e ".[qwen]"
./scripts/install_qwen_wrappers.sh
text2img-qwen --doctor
```

Optional SCAIL-2 / editvideo (GPU machine, weights explicit):

```bash
./scripts/setup_scail_env.sh
./scripts/setup_scail_env.sh --download-weights --convert   # ~82 GiB
./scripts/install_editvideo_wrapper.sh
editvideo doctor
editvideo smoke --example animation_001 --steps 20
```

## Quick examples

```bash
text2img-qwen --help
text2img-qwen --doctor
img2img-qwen --help
3dai --help
editvideo --help
ai-media doctor
```

## NixOS packaging status

| Piece | Status |
| ----- | ------ |
| llada-cli (`text2img`/`img2img`/`llada-image`) | **Already Nix** — thin wrapper → existing LLaDA venv (`local-ai-tools.nix`) |
| aiwmremover | **Already Nix** — same pattern |
| Qwen / TRELLIS / SCAIL engines | **Not fully Nixified** — pip CUDA wheels + custom CUDA exts + multi-GB weights live in XDG venvs; wrappers only |
| Full store packaging of models | **Blocked** — do not re-download huge weights into the Nix store |

Prefer `scripts/install_*_wrapper.sh` over rewriting engines.

## Related

Text-to-video lives in its own repo: [r3dg0d/text2video](https://github.com/r3dg0d/text2video).

## Terminal image preview

`TerminalImageRenderer` prefers Kitty graphics protocol, then chafa, then ANSI
blocks, else none (non-TTY). Animations stop cleanly before pixels are written.

## Config

Image commands report invalid generation settings with exit code 2. Backend
readiness and CUDA failures also use code 2; file I/O failures use code 1.
Errors go to stderr even with `--quiet`; use `--debug` for runtime tracebacks.
Aspect ratios must have positive, finite components (for example `16:9`),
and explicit aspect dimensions must be at least 64 pixels (`768x512`).

XDG path: `~/.config/ai-media/config.toml` (created with defaults on first load).

## Status

See [STATUS.md](STATUS.md).

## Cancellation

`text2img`, `img2img`, `3dai`, and `editvideo` handle Ctrl+C (SIGINT) and SIGTERM
with exit code 130. Interrupts unwind active Python work, then run registered
shutdown callbacks once. Active editvideo/3dai jobs record an `interrupt` stage
with status `cancelled` when their job store remains writable. Interrupting a
preview after completion does not relabel the completed job.

Cancellation does not remove partial outputs or undo side effects. Job records
are best-effort; interruption before job creation or unavailable storage cannot
record cancellation. Native backend calls may delay Python signal delivery;
see [Python signal execution](https://docs.python.org/3/library/signal.html#execution-of-python-signal-handlers).
Real GPU inference and arbitrary backend descendant cleanup are not established
by the CPU-only signal tests.
