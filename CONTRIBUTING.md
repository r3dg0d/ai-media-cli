# Contributing to ai-media-cli

Thanks for helping build local-first AI media tooling.

## Development setup

```bash
cd ai-media-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

GPU model weights are **not** required for unit tests. Optional backends need
their own setup scripts under `scripts/`.

## Guidelines

- Keep shared modules GPU-free and unit-testable.
- Prefer Rich for CLI UX; stop animations before image render.
- Never commit secrets, weights, or multi-GB artifacts.
- Fail closed for cloud/external calls in `3dai` / `editvideo`.
- Match existing style: type hints, pathlib, argparse CLIs.

## Pull requests

1. Branch from `main`.
2. Add/adjust tests.
3. Update `CHANGELOG.md` and `STATUS.md` when behavior changes.
4. Ensure `pytest` and `ruff check` pass.
