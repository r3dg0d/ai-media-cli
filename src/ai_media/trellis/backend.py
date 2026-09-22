"""TRELLIS.2 backend — local image→3D via Trellis2ImageTo3DPipeline."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SETUP_HINT = "run scripts/setup_trellis_env.sh (needs CUDA toolkit / nvcc for o-voxel)"
DEFAULT_REPO = Path.home() / "Projects" / "TRELLIS.2"
DEFAULT_MODEL = "microsoft/TRELLIS.2-4B"


class TrellisNotInstalledError(RuntimeError):
    def __init__(self, detail: str = "") -> None:
        extra = f" ({detail})" if detail else ""
        super().__init__(f"TRELLIS backend not ready. {SETUP_HINT}{extra}")


def _ensure_repo_on_path() -> Path | None:
    repo = Path(os.environ.get("TRELLIS2_REPO", DEFAULT_REPO))
    if repo.is_dir():
        p = str(repo)
        if p not in sys.path:
            sys.path.insert(0, p)
        return repo
    return None


@dataclass
class TrellisBackend:
    model_id: str = DEFAULT_MODEL
    resolution: int = 512
    _pipe: Any = None

    def doctor(self) -> dict[str, Any]:
        repo = _ensure_repo_on_path()
        info: dict[str, Any] = {
            "model_id": self.model_id,
            "repo": str(repo) if repo else None,
            "resolution_default": self.resolution,
            "hint": SETUP_HINT,
        }
        try:
            import torch

            info["torch"] = True
            info["cuda"] = bool(torch.cuda.is_available())
            info["cuda_name"] = (
                torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
            )
        except ImportError:
            info["torch"] = False
            info["cuda"] = False
            info["status"] = "needs_setup"
            return info

        os.environ.setdefault("ATTN_BACKEND", "xformers")
        try:
            from trellis2.pipelines import Trellis2ImageTo3DPipeline  # noqa: F401

            info["pipeline_class"] = "Trellis2ImageTo3DPipeline"
        except Exception as e:
            info["pipeline_class"] = None
            info["import_error"] = f"{type(e).__name__}: {e}"
            info["status"] = "needs_setup"
            return info

        try:
            import o_voxel  # noqa: F401

            info["o_voxel"] = True
        except Exception as e:
            info["o_voxel"] = False
            info["o_voxel_error"] = f"{type(e).__name__}: {e}"

        info["status"] = "ready" if info.get("o_voxel") else "partial"
        return info

    def _ensure_pipeline(self) -> Any:
        if self._pipe is not None:
            return self._pipe
        _ensure_repo_on_path()
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
        os.environ.setdefault("ATTN_BACKEND", "xformers")
        try:
            from trellis2.pipelines import Trellis2ImageTo3DPipeline
        except Exception as e:
            raise TrellisNotInstalledError(str(e)) from e
        pipe = Trellis2ImageTo3DPipeline.from_pretrained(self.model_id)
        pipe.cuda()
        self._pipe = pipe
        return pipe

    def reconstruct(
        self,
        image: Path,
        *,
        output_dir: Path | None = None,
        seed: int | None = None,
        export_glb: bool = True,
        **kwargs: Any,
    ) -> Path:
        image = Path(image)
        if not image.is_file():
            raise FileNotFoundError(image)
        out_dir = Path(output_dir) if output_dir else image.parent / "trellis_out"
        out_dir.mkdir(parents=True, exist_ok=True)

        pipe = self._ensure_pipeline()
        from PIL import Image

        img = Image.open(image).convert("RGBA")
        run_kw: dict[str, Any] = {}
        if seed is not None:
            run_kw["seed"] = int(seed)
        if "resolution" in kwargs:
            run_kw["resolution"] = kwargs["resolution"]
        meshes = pipe.run(img, **run_kw)
        mesh = meshes[0]
        simplify = getattr(mesh, "simplify", None)
        if callable(simplify):
            try:
                mesh.simplify(16777216)
            except Exception:
                pass

        glb_path = out_dir / (image.stem + ".glb")
        if not export_glb:
            return out_dir
        try:
            import o_voxel

            glb = o_voxel.postprocess.to_glb(
                vertices=mesh.vertices,
                faces=mesh.faces,
                attr_volume=mesh.attrs,
                coords=mesh.coords,
                attr_layout=mesh.layout,
                voxel_size=mesh.voxel_size,
                aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
                decimation_target=int(kwargs.get("decimation_target", 500_000)),
                texture_size=int(kwargs.get("texture_size", 2048)),
                remesh=True,
                remesh_band=1,
                remesh_project=0,
                verbose=False,
            )
            glb.export(str(glb_path), extension_webp=True)
        except Exception as e:
            marker = out_dir / (image.stem + ".mesh.json")
            marker.write_text(
                __import__("json").dumps(
                    {"error": str(e), "note": "GLB export failed", "image": str(image)},
                    indent=2,
                )
                + "\n"
            )
            raise TrellisNotInstalledError(f"GLB export failed: {e}") from e
        return glb_path
