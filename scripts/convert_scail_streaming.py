#!/usr/bin/env python3
"""Convert SCAIL-2 FSDP .pt → safetensors with low RAM (no full-file mmap / no swap).

PyTorch 2.6+ + ~32GB hosts cannot torch.load the ~62GiB zip (CommitLimit / weights_only).
This streams each zip storage, remaps keys via SCAIL convert.get_new_mappings, and
writes a single safetensors file without holding all weights in RSS.
"""
from __future__ import annotations

import argparse
import gc
import io
import json
import os
import pickle
import struct
import sys
import time
import zipfile
from pathlib import Path

import torch

DTYPE_TO_SAFETENSORS = {
    torch.float32: "F32",
    torch.float16: "F16",
    torch.bfloat16: "BF16",
    torch.float64: "F64",
    torch.int64: "I64",
    torch.int32: "I32",
    torch.int16: "I16",
    torch.int8: "I8",
    torch.uint8: "U8",
    torch.bool: "BOOL",
}


def _load_module_meta(pt_path: Path, zip_prefix: str):
    zf = zipfile.ZipFile(pt_path)
    pkl = zf.read(f"{zip_prefix}/data.pkl")

    class MetaUnpickler(pickle.Unpickler):
        def persistent_load(self, saved_id):
            assert saved_id[0] == "storage", saved_id
            storage_type, key, location, numel = saved_id[1:]
            if storage_type is torch.UntypedStorage or storage_type is torch.ByteStorage:
                storage = torch.UntypedStorage(numel)
                typed = torch.storage.TypedStorage(
                    wrap_storage=storage, dtype=torch.uint8, _internal=True
                )
            else:
                dtype = storage_type.dtype
                nbytes = numel * torch.empty((), dtype=dtype).element_size()
                storage = torch.UntypedStorage(nbytes)
                typed = torch.storage.TypedStorage(
                    wrap_storage=storage, dtype=dtype, _internal=True
                )
            storage._scail_zip_key = str(key)  # type: ignore[attr-defined]
            return typed

    obj = MetaUnpickler(io.BytesIO(pkl)).load()
    if not isinstance(obj, dict) or "module" not in obj:
        raise SystemExit(f"unexpected checkpoint top-level: {type(obj)}")
    return zf, obj["module"]


def _tensor_from_zip(
    zf: zipfile.ZipFile, zip_prefix: str, storage_key: str, dtype: torch.dtype, shape: torch.Size
) -> torch.Tensor:
    raw = zf.read(f"{zip_prefix}/data/{storage_key}")
    expected = int(torch.tensor(shape).prod().item()) * torch.empty((), dtype=dtype).element_size()
    if len(raw) < expected:
        raise RuntimeError(
            f"storage {storage_key}: got {len(raw)} bytes, need {expected} for {shape} {dtype}"
        )
    # frombuffer needs writable / aligned buffer; use bytearray copy of needed slice only
    buf = bytearray(raw[:expected])
    t = torch.frombuffer(buf, dtype=dtype)
    return t.reshape(shape)


def _build_header(entries: list[tuple[str, str, list[int], int]]) -> tuple[bytes, dict]:
    """entries: (name, st_dtype, shape, nbytes) in write order."""
    header: dict = {}
    offset = 0
    for name, st_dtype, shape, nbytes in entries:
        header[name] = {
            "dtype": st_dtype,
            "shape": shape,
            "data_offsets": [offset, offset + nbytes],
        }
        offset += nbytes
    encoded = json.dumps(header, separators=(",", ":")).encode("utf-8")
    # pad JSON to 8-byte alignment of (8 + len)
    pad = (8 - (len(encoded) % 8)) % 8
    encoded = encoded + (b" " * pad)
    return encoded, header


def convert(pt_file: Path, save_path: Path, scail_repo: Path) -> None:
    sys.path.insert(0, str(scail_repo))
    from convert import get_new_mappings  # noqa: WPS433

    # Detect zip prefix (single directory in archive)
    with zipfile.ZipFile(pt_file) as zprobe:
        names = zprobe.namelist()
    prefix = names[0].split("/")[0]
    print(f"zip prefix={prefix}", flush=True)

    print("loading tensor metadata (no weight bytes)…", flush=True)
    t0 = time.time()
    zf, module = _load_module_meta(pt_file, prefix)
    print(f"  {len(module)} tensors in {time.time() - t0:.1f}s", flush=True)

    # Plan remapped entries + remember source keys for data pass
    plan: list[tuple[str, str, list[int], int, str, torch.dtype, torch.Size]] = []
    # (out_name, st_dtype, shape, nbytes, src_key, dtype, shape)
    # For chunked mappings, multiple outs share one src load — group by src_key
    order_src: list[str] = []
    for src_key, meta in module.items():
        if not torch.is_tensor(meta):
            continue
        mapped = get_new_mappings(src_key, meta)
        order_src.append(src_key)
        for out_name, mv in mapped.items():
            st = DTYPE_TO_SAFETENSORS.get(mv.dtype)
            if st is None:
                raise SystemExit(f"unsupported dtype {mv.dtype} for {out_name}")
            nbytes = mv.numel() * mv.element_size()
            plan.append(
                (out_name, st, list(mv.shape), nbytes, src_key, mv.dtype, torch.Size(mv.shape))
            )

    # Detect duplicate out names
    seen = set()
    for out_name, *_ in plan:
        if out_name in seen:
            raise SystemExit(f"duplicate remapped key {out_name}")
        seen.add(out_name)

    header_entries = [(n, d, s, nb) for n, d, s, nb, *_ in plan]
    header_bytes, _ = _build_header(header_entries)
    total_data = sum(e[3] for e in plan)
    print(
        f"writing {save_path} ({len(plan)} tensors, {total_data / 1e9:.2f} GB data)…",
        flush=True,
    )

    save_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = save_path.with_suffix(save_path.suffix + ".partial")
    if tmp.exists():
        tmp.unlink()

    # Group plan indices by src_key preserving first-seen order
    from collections import OrderedDict

    by_src: OrderedDict[str, list[int]] = OrderedDict()
    for i, e in enumerate(plan):
        by_src.setdefault(e[4], []).append(i)

    with open(tmp, "wb") as out:
        out.write(struct.pack("<Q", len(header_bytes)))
        out.write(header_bytes)

        done = 0
        for src_key, idxs in by_src.items():
            meta = module[src_key]
            zip_key = getattr(meta.untyped_storage(), "_scail_zip_key", None)
            if zip_key is None:
                raise RuntimeError(f"missing zip key for {src_key}")
            nbytes = meta.untyped_storage().nbytes()
            raw = zf.read(f"{prefix}/data/{zip_key}")
            if len(raw) < nbytes:
                raise RuntimeError(f"{src_key}: storage {zip_key} got {len(raw)} < {nbytes}")
            buf = bytearray(raw[:nbytes])
            storage_tensor = torch.frombuffer(buf, dtype=torch.uint8)
            untyped = storage_tensor.untyped_storage()
            real = torch.empty(0, dtype=meta.dtype)
            real.set_(untyped, meta.storage_offset(), meta.shape, meta.stride())
            mapped = get_new_mappings(src_key, real)
            for i in idxs:
                out_name = plan[i][0]
                tensor = mapped[out_name]
                if not tensor.is_contiguous():
                    tensor = tensor.contiguous()
                raw = tensor.view(torch.uint8).numpy().tobytes()
                expected = plan[i][3]
                if len(raw) != expected:
                    raise RuntimeError(f"{out_name}: wrote {len(raw)} expected {expected}")
                out.write(raw)
                done += 1
            del real, mapped
            if done % 50 == 0 or done == len(plan):
                print(f"  {done}/{len(plan)} tensors", flush=True)
                gc.collect()

    zf.close()
    tmp.replace(save_path)
    print(f"Done → {save_path} ({save_path.stat().st_size / 1e9:.2f} GB)", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pt", type=Path, required=True, help="fsdp2_rank_0000_checkpoint.pt")
    p.add_argument("--save-path", type=Path, required=True)
    p.add_argument(
        "--scail-repo",
        type=Path,
        default=Path(os.environ.get("AI_MEDIA_SCAIL_REPO", Path.home() / "Projects/SCAIL-2")),
    )
    args = p.parse_args()
    convert(args.pt, args.save_path, args.scail_repo)


if __name__ == "__main__":
    main()
