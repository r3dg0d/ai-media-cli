# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- NixOS wrappers: Qwen CLIs install as `text2img-qwen` / `img2img-qwen` so they
  do not shadow system `llada-cli` `text2img` / `img2img`.
- Added `scripts/install_qwen_wrappers.sh` (+ optional `ai-media` umbrella).
- README / STATUS document PATH truth and Nix packaging blockers.

## [0.1.0] - 2026-09-22

### Added

- Monorepo foundation: shared infrastructure, CLI entry points, docs, CI.
- Shared: terminal graphics (Kitty/chafa/ANSI), media preview, XDG config,
  Rich UI + bounce animation, GPU/memory/hardware monitoring, signals, jobs.
- `text2img` / `img2img` CLI shells with full flag surface (Qwen-Image-2.1 stubs).
- `3dai` and `editvideo` CLI skeletons with fail-closed gates and XDG job dirs.
- TRELLIS reconstruction/export stubs.
- Unit tests for non-TTY graphics, preview prompts, config, and `--help`.
