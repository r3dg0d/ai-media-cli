"""Rich-based consistent UX panels for ai-media CLIs."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_console: Console | None = None


def get_console(*, quiet: bool = False) -> Console:
    global _console
    if _console is None or quiet:
        return Console(stderr=False, quiet=quiet)
    return _console


def set_console(console: Console) -> None:
    global _console
    _console = console


def banner(title: str, subtitle: str | None = None, *, console: Console | None = None) -> None:
    c = console or get_console()
    body = Text(title, style="bold cyan")
    if subtitle:
        body.append("\n")
        body.append(subtitle, style="dim")
    c.print(Panel(body, border_style="cyan", expand=False))


def info_panel(title: str, data: dict[str, Any], *, console: Console | None = None) -> None:
    c = console or get_console()
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("key", style="bold")
    table.add_column("val")
    for k, v in data.items():
        table.add_row(str(k), str(v))
    c.print(Panel(table, title=title, border_style="blue", expand=False))


def success(msg: str, *, console: Console | None = None) -> None:
    (console or get_console()).print(f"[green]✔[/green] {msg}")


def warn(msg: str, *, console: Console | None = None) -> None:
    (console or get_console()).print(f"[yellow]![/yellow] {msg}")


def error(msg: str, *, console: Console | None = None) -> None:
    (console or get_console()).print(f"[red]✖[/red] {msg}")


def status_line(msg: str, *, console: Console | None = None) -> None:
    (console or get_console()).print(f"[cyan]…[/cyan] {msg}")
