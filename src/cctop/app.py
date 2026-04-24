from contextlib import AbstractContextManager
from functools import partial
from importlib.metadata import version as _package_version
from typing import Annotated

import typer
from rich.console import Console, ConsoleRenderable
from rich.live import Live

from cctop.core.session import session, session_refs
from cctop.views.monitor import SessionMonitor
from cctop.views.picker import SessionPicker
from cctop.views.protocols import Action

app = typer.Typer(add_completion=False)


def _show_version(value: bool) -> None:
    if value:
        typer.echo(_package_version("cctop"))
        raise typer.Exit()


@app.command()
def main(
    refresh: Annotated[float, typer.Option(help="Data reload interval in seconds")] = 2.0,
    fps: Annotated[int, typer.Option(help="View render frames per second")] = 10,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_show_version, is_eager=True, help="Show version and exit"),
    ] = False,
) -> None:
    def live_view(content: ConsoleRenderable, console: Console) -> AbstractContextManager[Live]:
        return Live(content, console=console, refresh_per_second=fps, screen=True)
    session_monitor = partial(
        SessionMonitor, session_loader=session, live_view_factory=live_view, refresh=refresh,
    )
    session_picker = SessionPicker(sessions_finder=session_refs, live_view_factory=live_view)
    console = Console()
    while True:
        picker_action, session_ref = session_picker.display_on(console)
        match picker_action:
            case Action.QUIT:
                raise typer.Exit()
            case Action.SELECT if session_ref:
                monitor_action, _ = session_monitor(ref=session_ref).display_on(console)
                match monitor_action:
                    case Action.QUIT:
                        raise typer.Exit()
