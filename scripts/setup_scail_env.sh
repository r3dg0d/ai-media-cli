#!/usr/bin/env bash
# SCAIL-2 env scaffold. Does NOT download Wan/SCAIL weights unless --download-weights.
set -euo pipefail
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/ai-media"
ENV="$DATA/envs/scail"
REPO="${SCAIL2_REPO:-$HOME/Projects/SCAIL-2}"
mkdir -p "$DATA/logs" "$DATA/envs"
echo "[scail] env=$ENV repo=$REPO"
if [[ ! -d "$REPO/.git" ]]; then
  git clone --depth 1 -b wan-scail2 https://github.com/zai-org/SCAIL-2.git "$REPO"
fi
if [[ ! -x "$ENV/bin/python" ]]; then
  uv venv "$ENV" --python "${AI_MEDIA_PYTHON:-python3.11}"
fi
export LD_LIBRARY_PATH="/run/opengl-driver/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export UV_LINK_MODE=copy
uv pip install --python "$ENV/bin/python" torch torchvision --index-url https://download.pytorch.org/whl/cu128
# Remaining deps follow upstream README when you are ready for video weights.
SITE="$("$ENV/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
echo "$REPO" > "$SITE/scail2_repo.pth"
echo "[scail] Repo linked. Install remaining deps per $REPO/README.md"
echo "[scail] Weights are large — only pass --download-weights intentionally."
if [[ "${1:-}" == "--download-weights" ]]; then
  echo "[scail] Follow upstream generate.py / HF card for checkpoint paths (not auto-pulled here)."
fi
