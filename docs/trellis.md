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


## Gated dependency: DINOv3

TRELLIS.2 image encoder loads `facebook/dinov3-vitl16-pretrain-lvd1689m` (gated on Hugging Face).

1. Accept access at https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m
2. `hf auth login` (or set `HF_TOKEN`)
3. Re-run `3dai run ./input.png --stages ingest reconstruct`

## Background removal (rembg)

Microsoft's `pipeline.json` pins gated `briaai/RMBG-2.0`. The ai-media TRELLIS backend
overrides rembg to ungated [`ZhengPeng7/BiRefNet`](https://huggingface.co/ZhengPeng7/BiRefNet)
so reconstruct works without Bria approval. Accept Meta DINOv3 access for the image
conditioner (`facebook/dinov3-*`). Optional: accept RMBG-2.0 if you want the upstream default.

## DINOv3 + transformers 5.x

`DinoV3FeatureExtractor` in upstream TRELLIS.2 expects `model.layer`. transformers 5.x
moved layers to `model.model.layer` and added `model.norm`. Apply
`patches/trellis2-dinov3-transformers5.patch` (already applied under `~/Projects/TRELLIS.2`).
