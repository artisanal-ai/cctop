import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text

from cctop.core import Agent, Session
from cctop.core.usage import Usage
from cctop.views.keys import Key, KeyListener
from cctop.views.protocols import Action, LiveViewFactory, Row, View
from cctop.views.style import _C_DIM, _C_ERR, _C_OK, _C_RUNNING, _C_WARN

_KEYS: dict[Key, Action] = {
    Key.QUIT: Action.QUIT,
    Key.LEFT: Action.BACK,
    Key.TOOLS: Action.TOGGLE_TOOLS,
    Key.UP: Action.SCROLL_UP,
    Key.DOWN: Action.SCROLL_DOWN,
}


class _StatusInfo(NamedTuple):
    icon: str
    label: str
    pulse: tuple[str, str | None]


_STATUS: dict[str, _StatusInfo] = {
    "done":         _StatusInfo("✓", "done",         (_C_OK, None)),
    "running":      _StatusInfo("●", "running",      (f"bold {_C_RUNNING}", f"dim {_C_RUNNING}")),
    "rate_limited": _StatusInfo("✗", "rate limited", (_C_WARN, None)),
    "failed":       _StatusInfo("✗", "failed",       (_C_ERR, None)),
    "dispatched":   _StatusInfo("◌", "dispatched",   (_C_DIM, None)),
    "inactive":     _StatusInfo("○", "inactive",     (_C_DIM, None)),
}


@dataclass
class SessionMonitor(View[Session]):
    ref: Session.Ref
    session_loader: Callable[[Session.Ref], Session]
    live_view_factory: LiveViewFactory
    key_listener_factory: Callable[[], KeyListener] = KeyListener
    refresh: float = 2.0
    show_tools: bool = False
    scroll: int = 0

    def display_on(self, console: Console) -> tuple[Action, Session]:
        session = self.session_loader(self.ref)
        now = time.time()
        next_reload = now + self.refresh
        next_pulse = now + 0.5

        content, _ = self._render(session, console.height)
        with self.key_listener_factory() as keys, self.live_view_factory(content, console) as live:
            while True:
                time.sleep(0.1)
                dirty = False

                key = keys.read()
                action = _KEYS.get(key) if key else None
                match action:
                    case Action.QUIT | Action.BACK:
                        return action, session
                    case Action.TOGGLE_TOOLS:
                        self.show_tools = not self.show_tools
                        self.scroll = 0
                        dirty = True
                    case Action.SCROLL_UP:
                        self.scroll = max(0, self.scroll - 1)
                        dirty = True
                    case Action.SCROLL_DOWN:
                        self.scroll += 1
                        dirty = True

                if time.time() >= next_reload:
                    session = self.session_loader(self.ref)
                    next_reload = time.time() + self.refresh
                    dirty = True

                if time.time() >= next_pulse and session.active:
                    next_pulse = time.time() + 0.5
                    dirty = True

                if dirty:
                    content, self.scroll = self._render(session, console.height)
                    live.update(content)

    def _render(self, session: Session, term_height: int = 0) -> tuple[Group, int]:
        fixed_overhead = 5
        gutter = "   "
        title = f"cctop — {session.ref.project}  ({session.ref.short_id})"

        all_rows = self._collect_rows(session)
        total = len(all_rows)
        max_visible = max(term_height - fixed_overhead - 1, 5) if term_height > 0 else total
        max_scroll = max(0, total - max_visible)
        clamped = min(self.scroll, max_scroll)
        scrollable = total > max_visible

        visible = all_rows[clamped:clamped + max_visible] if scrollable else all_rows
        table = self._build_table(visible)

        keys_parts: list[str] = ["← sessions"]
        if scrollable:
            keys_parts.append("↑/↓ scroll")
        keys_parts.extend(["t tools", "q quit"])
        keys_text = "  ".join(keys_parts)
        if scrollable:
            keys_text += f"  ({clamped + 1}–{min(clamped + max_visible, total)}/{total})"  # noqa: RUF001

        footer = Table(show_header=False, box=None, padding=(0, 1), expand=True, pad_edge=False)
        footer.add_column(ratio=1)
        footer.add_column(justify="right", ratio=1)
        footer.add_column(width=1, no_wrap=True)
        footer.add_row(Text(f"{gutter}{keys_text}", style=_C_DIM), self._status_legend(), "")

        padding = max(1, term_height - fixed_overhead - len(visible)) if term_height > 0 else 1

        return Group(
            Text(""), Text(f"{gutter}{title}", style="bold"),
            Text(""), table,
            *([Text("")] * padding), footer,
        ), clamped

    _COLUMN_COUNT = 13

    def _collect_rows(self, session: Session) -> list[Row]:
        sep_cell = Text("╌" * 120, style=_C_DIM, overflow="crop")
        sep: Row = ("", *((sep_cell,) * (self._COLUMN_COUNT - 2)), "")
        rows: list[Row] = []
        if session.agents or session.usage.total_tokens:
            rows.append(self._totals_row(session))
            rows.append(sep)
            rows.append(self._session_row(session))
            if session.agents:
                rows.append(sep)
        for a in session.agents:
            rows.append(self._agent_row(a, session.status(a)))
            if self.show_tools and a.usage.tools:
                for name, tu in sorted(
                    a.usage.tools.items(),
                    key=lambda t: t[1].calls,
                    reverse=True,
                ):
                    rows.append(self._tool_row(name, tu))
        return rows

    def _build_table(self, rows: list[Row]) -> Table:
        table = Table(
            show_header=True, header_style="bold",
            box=None, padding=(0, 1), expand=True, pad_edge=False,
        )
        table.add_column("",        width=1, no_wrap=True)
        table.add_column("AGENT",   no_wrap=True, ratio=1)
        table.add_column("STATUS",  justify="center", width=6, no_wrap=True)
        table.add_column("TIME",    justify="right", width=8, no_wrap=True)
        table.add_column("IN",      justify="right", width=7, no_wrap=True)
        table.add_column("OUT",     justify="right", width=7, no_wrap=True)
        table.add_column("CACHE_W", justify="right", width=7, no_wrap=True)
        table.add_column("CACHE_R", justify="right", width=7, no_wrap=True)
        table.add_column("TOTAL",   justify="right", width=7, no_wrap=True)
        table.add_column("COST",    justify="right", width=8, no_wrap=True)
        table.add_column("TOOLS",   justify="right", width=5, no_wrap=True)
        table.add_column("OK%",     justify="right", width=4, no_wrap=True)
        table.add_column("",        width=1, no_wrap=True)
        for row in rows:
            table.add_row(*row)
        return table

    def _totals_row(self, session: Session) -> Row:
        tu = session.total_usage
        tc = tu.tool_calls
        te = tu.tool_errors
        elapsed = session.elapsed_seconds if session.active else session.wall_seconds
        total = len(session.agents) + 1
        done = session.done_count + (0 if session.active else 1)
        return (
            "",
            Text("", style="bold"),
            Text(f"{done}/{total}", style="bold"),
            Text(self._duration(elapsed), style="bold"),
            Text(self._tokens(tu.input_tokens), style="bold"),
            Text(self._tokens(tu.output_tokens), style="bold"),
            Text(self._tokens(tu.cache_creation_tokens), style="bold"),
            Text(self._tokens(tu.cache_read_tokens), style="bold"),
            Text(self._tokens(tu.total_tokens), style="bold"),
            Text(self._cost(session.total_cost), style=f"bold {_C_WARN}"),
            Text(str(tc), style="bold"),
            self._success_rate(tc, te),
            "",
        )

    def _pulse_style(self, s: _StatusInfo) -> str:
        sty, blink_sty = s.pulse
        return blink_sty if blink_sty and int(time.time() * 2) % 2 else sty

    def _session_row(self, session: Session) -> Row:
        s = _STATUS["running" if session.active else "inactive"]
        sty = s.pulse[0]
        return (
            "",
            Text(f"claude ({session.ref.project})", style=sty),
            Text(s.icon, style=self._pulse_style(s)),
            self._duration(session.elapsed_seconds if session.active else session.wall_seconds),
            self._tokens(session.usage.input_tokens),
            self._tokens(session.usage.output_tokens),
            self._tokens(session.usage.cache_creation_tokens),
            self._tokens(session.usage.cache_read_tokens),
            Text(self._tokens(session.usage.total_tokens), style="bold"),
            self._cost(session.cost),
            str(session.usage.tool_calls) if session.usage.tool_calls else "—",
            self._success_rate(session.usage.tool_calls, session.usage.tool_errors),
            "",
        )

    def _agent_row(self, a: Agent, status: str) -> Row:
        s = _STATUS.get(status, _StatusInfo("?", "unknown", ("", None)))
        sty = s.pulse[0]
        tc = a.usage.tool_calls
        tools_cell: str | Text = (
            Text(str(tc), style=f"bold {_C_RUNNING}")
            if status == "running" and tc
            else str(tc) if tc else "—"
        )
        return (
            "",
            Text(self._agent_name(a), style=sty),
            Text(s.icon, style=self._pulse_style(s)),
            Text(
                self._duration(a.elapsed_seconds if status == "running" else a.wall_seconds),
                style=_C_DIM if status == "dispatched" else "",
            ),
            self._tokens(a.usage.input_tokens),
            self._tokens(a.usage.output_tokens),
            self._tokens(a.usage.cache_creation_tokens),
            self._tokens(a.usage.cache_read_tokens),
            Text(self._tokens(a.usage.total_tokens), style="bold" if status != "dispatched" else _C_DIM),
            self._cost(a.cost),
            tools_cell,
            self._success_rate(tc, a.usage.tool_errors),
            "",
        )

    def _tool_row(self, name: str, t: Usage.Tool) -> Row:
        return (
            "",
            Text(f"  {name}", style=_C_DIM), "", "",
            "", "", "", "", "",
            "",
            Text(str(t.calls), style=_C_DIM),
            self._success_rate(t.calls, t.errors),
            "",
        )



    def _success_rate(self, calls: int, errors: int) -> Text:
        if calls == 0:
            return Text("—", style=_C_DIM)
        pct = (calls - errors) / calls * 100
        style = _C_OK if pct >= 95 else _C_WARN if pct >= 80 else _C_ERR
        return Text(f"{pct:.0f}%", style=style)

    def _status_legend(self) -> Text:
        return Text.assemble(
            *(pair for s in _STATUS.values() for pair in ((s.icon, s.pulse[0]), (f" {s.label}  ", _C_DIM))),
            justify="right",
        )

    def _agent_name(self, a: Agent) -> str:
        t = a.type or "agent"
        return f"{t} ({a.description.lower()})" if a.description else t

    def _tokens(self, n: int) -> str:
        if n == 0:
            return "—"
        if n < 1_000:
            return str(n)
        if n < 1_000_000:
            return f"{n / 1_000:.1f}k"
        return f"{n / 1_000_000:.2f}M"

    def _duration(self, seconds: float) -> str:
        if seconds <= 0:
            return "—"
        m, s = divmod(int(seconds), 60)
        return f"{m}m{s:02d}s" if m else f"{s}s"

    def _cost(self, usd: float) -> str:
        if usd < 0.005:
            return "—"
        if usd < 0.10:
            return f"${usd:.3f}"
        if usd < 10:
            return f"${usd:.2f}"
        return f"${usd:.1f}"
