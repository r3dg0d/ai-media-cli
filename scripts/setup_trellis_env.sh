#!/usr/bin/env bash
# NixOS TRELLIS.2 env. Weights only with --download-weights.
set -euo pipefail
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/ai-media"
ENV="$DATA/envs/trellis"
REPO="${TRELLIS2_REPO:-$HOME/Projects/TRELLIS.2}"
CUDA_HOME="${CUDA_HOME:-}"
mkdir -p "$DATA/logs" "$DATA/envs"
echo "[trellis] env=$ENV repo=$REPO"

if [[ ! -d "$REPO/.git" ]]; then
  git clone --depth 1 -b main https://github.com/microsoft/TRELLIS.2.git "$REPO"
  git -C "$REPO" submodule update --init --recursive
fi
if [[ ! -x "$ENV/bin/python" ]]; then
  uv venv "$ENV" --python "${AI_MEDIA_PYTHON:-python3.11}"
fi

export LD_LIBRARY_PATH="/run/opengl-driver/lib:/nix/store/604gsr59rj7dzd0nrhp143rpvf7gyiaz-gcc-15.3.0-lib/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_LIBCUDA_PATH=/run/opengl-driver/lib
export UV_LINK_MODE=copy
export ATTN_BACKEND="${ATTN_BACKEND:-xformers}"

uv pip install --python "$ENV/bin/python" torch torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python "$ENV/bin/python" imageio imageio-ffmpeg tqdm easydict opencv-python-headless ninja trimesh transformers tensorboard pandas lpips zstandard kornia timm pillow 'git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8'
uv pip install --python "$ENV/bin/python" xformers --index-url https://download.pytorch.org/whl/cu128 || true
SITE="$("$ENV/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
echo "$REPO" > "$SITE/trellis2_repo.pth"

if [[ -z "$CUDA_HOME" ]]; then
  echo "[trellis] Set CUDA_HOME to nix cudatoolkit (nvcc). Example:"
  echo "  CUDA_HOME=\$(nix-build '<nixpkgs>' -A cudaPackages.cudatoolkit --no-out-link)"
  echo "  GCC13=\$(nix-build '<nixpkgs>' -A gcc13 --no-out-link)"
  echo "  export PATH=\$GCC13/bin:\$CUDA_HOME/bin:\$PATH CC=\$GCC13/bin/gcc CXX=\$GCC13/bin/g++ CUDAHOSTCXX=\$CXX TORCH_CUDA_ARCH_LIST=8.9"
  echo "  Then pip-install CuMesh FlexGEMM nvdiffrast o-voxel --no-build-isolation"
fi

if [[ "${1:-}" == "--download-weights" ]]; then
  echo "[trellis] Downloading microsoft/TRELLIS.2-4B …"
  "$ENV/bin/python" -c 'from huggingface_hub import snapshot_download; print(snapshot_download("microsoft/TRELLIS.2-4B"))'
fi

export TRELLIS2_REPO="$REPO"
"$ENV/bin/python" - <<'PY'
import os, sys
from pathlib import Path
os.environ.setdefault("ATTN_BACKEND", "xformers")
sys.path.insert(0, str(Path.home() / "Projects" / "TRELLIS.2"))
from trellis2.pipelines import Trellis2ImageTo3DPipeline
import o_voxel
print("pipeline+o_voxel OK")
PY
