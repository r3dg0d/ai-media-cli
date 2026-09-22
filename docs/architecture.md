# Architecture

```
CLI entry points (pyproject scripts)
  text2img / img2img → ai_media.qwen.*
  3dai               → ai_media.threedai.*
  editvideo          → ai_media.editvideo.*
  ai-media doctor    → ai_media.shared.diagnostics

shared/
  terminal_graphics  Kitty → chafa → ANSI → none
  media_preview      preview / open (TTY-safe)
  config             XDG ~/.config/ai-media/config.toml
  ui + animation     Rich panels; stop Live before pixels
  gpu/memory/hardware/monitoring
  jobs               XDG cache job dirs + state.json
  signals            Ctrl+C clean shutdown
```

Model backends are pluggable and raise explicit install errors until GPU envs exist.
