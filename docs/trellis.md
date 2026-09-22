# TRELLIS.2

Image → textured 3D (O-Voxel → GLB) via `microsoft/TRELLIS.2-4B` (MIT).

## Setup on NixOS (zionsec)

```bash
./scripts/setup_trellis_env.sh

# CUDA extensions (once):
CUDA_HOME=$(nix-build '<nixpkgs>' -A cudaPackages.cudatoolkit --no-out-link)
GCC13=$(nix-build '<nixpkgs>' -A gcc13 --no-out-link)
export PATH=$GCC13/bin:$CUDA_HOME/bin:$PATH
export CC=$GCC13/bin/gcc CXX=$GCC13/bin/g++ CUDAHOSTCXX=$CXX
export TORCH_CUDA_ARCH_LIST=8.9 MAX_JOBS=4 ATTN_BACKEND=xformers
# then install CuMesh, FlexGEMM, nvdiffrast, o-voxel --no-build-isolation

./scripts/setup_trellis_env.sh --download-weights   # explicit; large
```

Env: `~/.local/share/ai-media/envs/trellis` · Repo: `~/Projects/TRELLIS.2`

## Usage

```bash
3dai doctor
3dai run ./input.png --stages ingest reconstruct
```

RTX 4090: start at 512³. Wrapper sets `ATTN_BACKEND=xformers`.
