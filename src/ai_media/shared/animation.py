"""Bouncy Live animation that starts/stops cleanly BEFORE image render."""

from __future__ import annotations

import itertools
import threading
import time
from collections.abc import Iterator

from rich.console import Console, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

_BOUNCE = ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"]
_DOTS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class BounceAnimation:
    """
    Rich Live spinner. Call start() before long work; stop() BEFORE any
    terminal graphics / image bytes so the Live region does not corrupt output.
    """

    def __init__(
        self,
        message: str = "Working",
        *,
        console: Console | None = None,
        enabled: bool = True,
        fps: float = 12.0,
    ) -> None:
        self.message = message
        self.console = console or Console()
        self.enabled = enabled and self.console.is_terminal
        self.fps = fps
        self._live: Live | None = None
        self._frames: Iterator[str] = itertools.cycle(_DOTS)
        self._lock = threading.Lock()
        self._running = False

    def _render(self) -> RenderableType:
        frame = next(self._frames)
        text = Text.assemble(
            (frame, "bold magenta"),
            ("  ", ""),
            (self.message, "cyan"),
            ("  ", ""),
            (next(itertools.cycle(_BOUNCE)), "dim"),
        )
        return Panel(text, border_style="magenta", expand=False)

    def start(self, message: str | None = None) -> BounceAnimation:
        if message:
            self.message = message
        if not self.enabled or self._running:
            return self
        with self._lock:
            self._live = Live(
                self._render(),
                console=self.console,
                refresh_per_second=self.fps,
                transient=True,
            )
            self._live.start()
            self._running = True

            def _tick() -> None:
                while self._running and self._live is not None:
                    try:
                        self._live.update(self._render())
                    except Exception:
                        break
                    time.sleep(1.0 / self.fps)

            t = threading.Thread(target=_tick, name="ai-media-bounce", daemon=True)
            t.start()
        return self

    def update(self, message: str) -> None:
        self.message = message

    def stop(self) -> None:
        """Stop Live cleanly — call this before TerminalImageRenderer.render()."""
        with self._lock:
            self._running = False
            if self._live is not None:
                try:
                    self._live.stop()
                except Exception:
                    pass
                self._live = None

    def __enter__(self) -> BounceAnimation:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()
