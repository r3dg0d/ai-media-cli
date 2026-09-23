#!/usr/bin/env bash
# Setup SCAIL-2 inference env for editvideo on NixOS / Linux.
# Does NOT download multi-GB weights unless --download-weights is passed.
#
# Venv (XDG): ${XDG_DATA_HOME:-$HOME/.local/share}/ai-media/envs/scail
# Models:     ${XDG_DATA_HOME:-$HOME/.local/share}/ai-media/models/scail-2
# Repo:       $AI_MEDIA_SCAIL_REPO or ~/Projects/SCAIL-2
#
# Torch index: cu128 by default (match trellis/qwen envs on zionsec).
#
set -euo pipefail

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV_DIR="${AI_MEDIA_SCAIL_VENV:-$XDG_DATA_HOME/ai-media/envs/scail}"
MODELS_DIR="${AI_MEDIA_SCAIL_MODELS:-$XDG_DATA_HOME/ai-media/models/scail-2}"
SCAIL_REPO="${AI_MEDIA_SCAIL_REPO:-$HOME/Projects/SCAIL-2}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu128}"
DOWNLOAD_WEIGHTS=0
CONVERT=0

for arg in "$@"; do
  case "$arg" in
    --download-weights) DOWNLOAD_WEIGHTS=1 ;;
    --convert) CONVERT=1 ;;
    -h|--help)
      cat <<HELP
Usage: $0 [--download-weights] [--convert]

  Creates uv/venv at: $VENV_DIR
  Installs torch/torchvision (cu128) + SCAIL requirements (flash_attn best-effort).
  Links SCAIL repo onto PYTHONPATH via .pth.
  Weights (~82 GiB zai-org/SCAIL-2) only with --download-weights.
  --convert runs convert.py → \$MODELS_DIR/SCAIL-2.safetensors after download.

NixOS: export LD_LIBRARY_PATH=/run/opengl-driver/lib:\${LD_LIBRARY_PATH:-}
HELP
      exit 0
      ;;
  esac
done

echo "==> ai-media editvideo / SCAIL-2 env setup"
echo "    venv:   $VENV_DIR"
echo "    models: $MODELS_DIR"
echo "    repo:   $SCAIL_REPO"
echo "    torch:  $TORCH_INDEX_URL"
echo "    Weights are NOT downloaded unless --download-weights."
echo ""

if [[ ! -d "$SCAIL_REPO" || ! -f "$SCAIL_REPO/generate.py" ]]; then
  echo "ERROR: SCAIL-2 repo not found at $SCAIL_REPO (need generate.py)." >&2
  echo "       Clone wan-scail2 branch and set AI_MEDIA_SCAIL_REPO." >&2
  exit 2
fi

mkdir -p "$(dirname "$VENV_DIR")" "$MODELS_DIR"

if command -v uv >/dev/null 2>&1; then
  if [[ ! -d "$VENV_DIR" ]]; then
    uv venv "$VENV_DIR" --python "${AI_MEDIA_PYTHON:-3.11}" || uv venv "$VENV_DIR" --python 3.12 || uv venv "$VENV_DIR"
  fi
else
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi
fi

PY="$VENV_DIR/bin/python"
if command -v uv >/dev/null 2>&1; then
  PIP=(uv pip install --python "$PY")
else
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  "$PY" -m ensurepip --upgrade >/dev/null 2>&1 || true
  PIP=("$PY" -m pip install)
fi

echo "==> Installing base tooling"
"${PIP[@]}" -U pip wheel packaging huggingface_hub

echo "==> Installing torch/torchvision (cu128 preferred)"
"${PIP[@]}" torch torchvision --index-url "$TORCH_INDEX_URL" || \
  "${PIP[@]}" torch torchvision

REQ="$SCAIL_REPO/requirements.txt"
if [[ -f "$REQ" ]]; then
  echo "==> Installing SCAIL requirements (flash_attn is best-effort)"
  grep -vi '^flash_attn' "$REQ" | grep -v '^#' | grep -v '^[[:space:]]*$' > /tmp/scail-req-nofa.txt || true
  "${PIP[@]}" -r /tmp/scail-req-nofa.txt || true
  "${PIP[@]}" einops || true
  if ! "$PY" -c 'import flash_attn' 2>/dev/null; then
    echo "    trying flash_attn (may fail on NixOS — continue without if needed)"
    "${PIP[@]}" flash_attn --no-build-isolation || \
      echo "WARN: flash_attn install failed; SCAIL may still run depending on code paths" >&2
  fi
fi

# Link repo for `import wan`
SITE="$VENV_DIR/lib/python*/site-packages"
# shellcheck disable=SC2086
for sp in $SITE; do
  if [[ -d "$sp" ]]; then
    echo "$SCAIL_REPO" > "$sp/ai_media_scail.pth"
    echo "    wrote $sp/ai_media_scail.pth → $SCAIL_REPO"
  fi
done

# Editable install of ai-media if we are inside the monorepo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ -f "$REPO_ROOT/pyproject.toml" ]]; then
  "${PIP[@]}" -e "$REPO_ROOT" || true
fi

if [[ "$DOWNLOAD_WEIGHTS" -eq 1 ]]; then
  echo ""
  echo "==> Downloading zai-org/SCAIL-2 (~82 GiB). This is intentional and large."
  echo "    HF user tip: token at ~/.cache/huggingface/token (login as 128bytes8 if needed)."
  mkdir -p "$MODELS_DIR"
  if command -v hf >/dev/null 2>&1; then
    hf download zai-org/SCAIL-2 --local-dir "$MODELS_DIR/hf-SCAIL-2"
  else
    python - <<PY
from huggingface_hub import snapshot_download
print("snapshot_download zai-org/SCAIL-2 → $MODELS_DIR/hf-SCAIL-2")
snapshot_download("zai-org/SCAIL-2", local_dir="$MODELS_DIR/hf-SCAIL-2")
print("done")
PY
  fi
  CONVERT=1
fi

if [[ "$CONVERT" -eq 1 ]]; then
  CKPT="$MODELS_DIR/hf-SCAIL-2"
  if [[ ! -f "$CKPT/Wan2.1_VAE.pth" ]]; then
    # try find under HF hub cache
    echo "Looking for Wan2.1_VAE.pth under HF cache…"
    FOUND=$(find "${HF_HOME:-$HOME/.cache/huggingface}" -name 'Wan2.1_VAE.pth' 2>/dev/null | head -1 || true)
    if [[ -n "$FOUND" ]]; then
      CKPT="$(dirname "$FOUND")"
    fi
  fi
  if [[ ! -f "$CKPT/Wan2.1_VAE.pth" ]]; then
    echo "ERROR: cannot find SCAIL-2 ckpt dir for convert.py" >&2
    exit 2
  fi
  OUT="$MODELS_DIR/SCAIL-2.safetensors"
  echo "==> convert.py → $OUT"
  (cd "$SCAIL_REPO" && python convert.py --scail-dir "$CKPT" --save-path "$OUT")
fi

export PATH="$VENV_DIR/bin:$PATH"
# ensure `python` resolves to venv for convert/download helpers
hash -r 2>/dev/null || true

echo ""
echo "Activate: source $VENV_DIR/bin/activate"
echo "NixOS:    export LD_LIBRARY_PATH=/run/opengl-driver/lib:\${LD_LIBRARY_PATH:-}"
echo "Doctor:   editvideo doctor"
echo "Smoke:    editvideo smoke --example animation_001 --steps 20"
echo ""
echo "NOTE: SCAIL-1.3B config exists in code; official SCAIL-2 HF weights are 14B-only (~82 GiB)."
