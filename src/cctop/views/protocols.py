from collections.abc import Callable
from contextlib import AbstractContextManager
from enum import StrEnum
from typing import Protocol

from rich.console import Console, ConsoleRenderable
from rich.live import Live
from rich.text import Text

type LiveViewFactory = Callable[[ConsoleRenderable, Console], AbstractContextManager[Live]]
type Row = tuple[str | Text, ...]


class View[T](Protocol):
    def display_on(self, console: Console) -> tuple["Action", T]: ...


class Action(StrEnum):
    QUIT = "quit"
    BACK = "back"
    TOGGLE_TOOLS = "toggle_tools"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    SELECT = "select"
