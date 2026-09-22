# Terminal graphics

`TerminalImageRenderer.detect()` chooses:

1. **kitty** — if `KITTY_WINDOW_ID`, `TERM`/`TERM_PROGRAM` hints (Kitty/Ghostty/WezTerm)
2. **chafa** — if `chafa` on `PATH`
3. **ansi** — Unicode/Pillow size summary (TTY only path still avoids escape spam on pipes)
4. **none** — non-TTY stdout (unit tests, CI)

Kitty transmit: PNG (`f=100`), direct (`t` default), base64 chunks of 4096 with `m=1/0`.
Call `BounceAnimation.stop()` **before** `render()`.
