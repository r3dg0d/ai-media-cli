# editvideo

Local video job planner + optional SCAIL-2 generation.

```bash
./scripts/setup_scail_env.sh
editvideo doctor
editvideo run ./clip.mp4 -p "animate character"
editvideo jobs
```

Weights are **not** downloaded by default. See `THIRD_PARTY_NOTICES.md` (Apache-2.0 code).
Video open UX uses `xdg-open` / config `open_video_mode` (default: prompt on TTY).
