# Terminal graphics

`TerminalImageRenderer.detect()` chooses:

1. **kitty** — Kitty / Ghostty / WezTerm (Kitty graphics protocol)
2. **chafa** — if `chafa` on `PATH`
3. **ansi** — Unicode/Pillow size summary
4. **none** — non-TTY stdout (unit tests, CI)

## Ghostty

Ghostty speaks the Kitty graphics protocol. Detection uses any of:

- `GHOSTTY_RESOURCES_DIR` / `GHOSTTY_BIN_DIR`
- `TERM_PROGRAM=ghostty` or `TERM=*ghostty*`
- `AI_MEDIA_GRAPHICS=kitty|ghostty` (force from scripts)

Kitty transmit: PNG (`f=100`), direct base64 chunks of 4096 with `m=1/0`.
Call `BounceAnimation.stop()` **before** `render()`.

## CLI

```bash
text2img "…" --graphics ghostty          # force Kitty protocol
text2img "…" --open                      # also open in imv
img2img "…" -i in.png --graphics kitty
```

## External viewer

`open_image` tries configured `image_viewer` (default `imv`), then `imv`, then `xdg-open`.
Default `open_image_mode` is `auto` (open on interactive TTY).
