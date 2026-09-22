#!/usr/bin/env bash
# Setup Qwen-Image-2.1 deps on a GPU machine. Does NOT download weights by default.
#
# Venv location (XDG):
#   ${XDG_DATA_HOME:-$HOME/.local/share}/ai-media/envs/qwen
# Override with AI_MEDIA_QWEN_VENV.
#
# NixOS: PyTorch needs the NVIDIA driver libs. Before activating / running:
#   export LD_LIBRARY_PATH=/run/opengl-driver/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
#
set -euo pipefail

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV_DIR="${AI_MEDIA_QWEN_VENV:-$XDG_DATA_HOME/ai-media/envs/qwen}"

echo "==> ai-media-cli Qwen env setup"
echo "    venv: $VENV_DIR"
echo "    This installs Python packages only. Model weights are pulled explicitly."
echo ""
echo "    NixOS note: export LD_LIBRARY_PATH=/run/opengl-driver/lib"
echo "    (prepend to existing LD_LIBRARY_PATH) so torch finds NVIDIA libs."
echo ""

mkdir -p "$(dirname "$VENV_DIR")"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install -U pip
python -m pip install "torch>=2.4" --index-url "${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu124}" || \
  python -m pip install "torch>=2.4"
# transformers>=5.17 required by Qwen-Image-2.1 (upstream README)
python -m pip install "transformers>=5.17" "accelerate>=0.34" pillow
python -m pip install "git+https://github.com/huggingface/diffusers" || \
  python -m pip install "diffusers>=0.31"

echo ""
echo "Optional weight download (MULTI-GB) — only if you pass --download-weights:"
if [[ "${1:-}" == "--download-weights" ]]; then
  python - <<'PY'
from huggingface_hub import snapshot_download
print("Downloading Qwen/Qwen-Image-2.1 …")
snapshot_download("Qwen/Qwen-Image-2.1")
print("done")
PY
else
  echo "  skipped. Re-run with: $0 --download-weights"
fi

echo ""
echo "Activate: source $VENV_DIR/bin/activate"
echo "NixOS:    export LD_LIBRARY_PATH=/run/opengl-driver/lib:\${LD_LIBRARY_PATH:-}"
echo "Then:     pip install -e '.[qwen]' && text2img --doctor"
