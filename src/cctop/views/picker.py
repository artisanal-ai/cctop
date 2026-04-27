import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from rich.console import Console, Group
from rich.table import Column, Table
from rich.text import Text

from cctop.core import Session
from cctop.views.keys import Key, KeyListener
from cctop.views.protocols import Action, LiveViewFactory, Row, View
from cctop.views.style import _C_ACCENT, _C_DIM, _GUTTER

_KEYS: dict[Key, Action] = {
    Key.QUIT: Action.QUIT,
    Key.UP: Action.SCROLL_UP,
    Key.DOWN: Action.SCROLL_DOWN,
    Key.ENTER: Action.SELECT,
    Key.RIGHT: Action.SELECT,
}


@dataclass
class SessionPicker(View[Session.Ref | None]):
    sessions_finder: Callable[[], Iterable[Session.Ref]]
    live_view_factory: LiveViewFactory
    key_listener_factory: Callable[[], KeyListener] = KeyListener

    def display_on(self, console: Console) -> tuple[Action, Session.Ref | None]:
        sessions = list(self.sessions_finder())
        cursor = 0
        top = 0
        content = self._render(sessions, cursor, top, console.height)
        with self.key_listener_factory() as keys, self.live_view_factory(content, console) as live:
            while True:
                time.sleep(0.1)
                key = keys.read()
                action = _KEYS.get(key) if key else None
                match action:
                    case Action.QUIT:
                        return Action.QUIT, None
                    case Action.SELECT if sessions:
                        return Action.SELECT, sessions[cursor]
                    case Action.SCROLL_UP if sessions:
                        cursor = max(0, cursor - 1)
                    case Action.SCROLL_DOWN if sessions:
                        cursor = min(len(sessions) - 1, cursor + 1)
                top = _scroll_top(top, cursor, _visible(console.height))
                live.update(self._render(sessions, cursor, top, console.height))

    def _render(self, sessions: list[Session.Ref], cursor: int, top: int, term_height: int = 0) -> Group:
        visible = _visible(term_height) if term_height > 0 else len(sessions)
        window = sessions[top:top + visible]
        columns = (
            Column("", width=1, no_wrap=True),
            Column("PROJECT", no_wrap=True, ratio=1),
            Column("AGE", justify="right", width=10, no_wrap=True),
            Column("SESSION", width=36, no_wrap=True),
            Column("", width=1, no_wrap=True),
        )
        table = Table(
            *columns, show_header=True, header_style="bold",
            box=None, padding=(0, 1), expand=True, pad_edge=False,
        )
        rows = [self._row(s, top + i == cursor) for i, s in enumerate(window)]
        for row in rows:
            table.add_row(*row)

        title = (
            f"{_GUTTER}cctop — no sessions found" if not sessions
            else f"{_GUTTER}cctop — select a session  ({cursor + 1}/{len(sessions)})"
        )
        padding = max(1, term_height - 5 - len(rows)) if term_height > 0 else 1
        return Group(
            Text(""),
            Text(title, style="bold"),
            Text(""),
            table,
            *([Text("")] * padding),
            Text(f"{_GUTTER}↑/↓ navigate  enter/→ select  q quit", style=_C_DIM),
        )

    def _row(self, ref: Session.Ref, selected: bool) -> Row:
        marker = "›" if selected else ""  # noqa: RUF001
        age = self._age(ref.mtime)
        sid = ref.id
        if not selected:
            return marker, ref.project, age, sid, ""
        s = f"bold {_C_ACCENT}"
        return Text(marker, style=s), Text(ref.project, style=s), Text(age, style=s), Text(sid, style=s), ""

    def _age(self, mtime: float) -> str:
        delta = time.time() - mtime
        if delta < 60:
            return "just now"
        if delta < 3600:
            return f"{int(delta / 60)}m ago"
        if delta < 86400:
            return f"{int(delta / 3600)}h ago"
        return f"{int(delta / 86400)}d ago"


def _visible(term_height: int) -> int:
    return max(1, term_height - 6)


def _scroll_top(top: int, cursor: int, visible: int) -> int:
    if cursor < top:
        return cursor
    if cursor >= top + visible:
        return cursor - visible + 1
    return top
