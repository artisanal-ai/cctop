from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from rich.text import Text

from cctop.core.agents import Agent
from cctop.core.models import SONNET_4_5
from cctop.core.session import Session
from cctop.core.usage import Usage
from cctop.views.keys import Key
from cctop.views.monitor import SessionMonitor
from cctop.views.protocols import Action
from tests.conftest import fake_console, fake_key_listener, fake_live, make_agent, make_ref


def _monitor(tmp_path: Path | None = None, **kw: Any) -> SessionMonitor:
    ref = make_ref(tmp_path) if tmp_path else Session.Ref(Path("/tmp/test.jsonl"))
    return SessionMonitor(
        ref=ref,
        session_loader=lambda r: Session(ref=r),
        live_view_factory=fake_live,
        **kw,
    )


def _session(tmp_path: Path, **kw: Any) -> Session:
    return Session(ref=make_ref(tmp_path), **kw)


@pytest.mark.parametrize(
    ("n", "expected"),
    [(0, "—"), (42, "42"), (1500, "1.5k"), (999_999, "1000.0k"), (2_500_000, "2.50M")],
)
def test_tokens_formatting(n: int, expected: str) -> None:
    assert _monitor()._tokens(n) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "—"), (-1, "—"), (45, "45s"), (125, "2m05s")],
)
def test_duration_formatting(seconds: float, expected: str) -> None:
    assert _monitor()._duration(seconds) == expected


@pytest.mark.parametrize(
    ("usd", "expected"),
    [(0.001, "—"), (0.05, "$0.050"), (1.5, "$1.50"), (15.0, "$15.0")],
)
def test_cost_formatting(usd: float, expected: str) -> None:
    assert _monitor()._cost(usd) == expected


@pytest.mark.parametrize(
    ("calls", "errors", "expected_text"),
    [(0, 0, "—"), (10, 0, "100%"), (10, 1, "90%"), (10, 5, "50%")],
)
def test_success_rate(calls: int, errors: int, expected_text: str) -> None:
    result = _monitor()._success_rate(calls, errors)
    assert isinstance(result, Text)
    assert result.plain == expected_text


@pytest.mark.parametrize(
    ("agent_type", "desc", "expected"),
    [("Explore", "Search Files", "Explore (search files)"), ("Explore", None, "Explore"), (None, None, "agent")],
)
def test_agent_name(agent_type: str | None, desc: str | None, expected: str) -> None:
    a = Agent(id="a1", type=agent_type, description=desc)
    assert _monitor()._agent_name(a) == expected


def test_collect_rows_with_agents(tmp_path: Path) -> None:
    a = make_agent(model_usage={SONNET_4_5: Usage(input_tokens=100)})
    s = _session(tmp_path, agents=[a], model_usage={SONNET_4_5: Usage(input_tokens=200)})
    rows = _monitor(tmp_path)._collect_rows(s)
    assert len(rows) >= 5


def test_collect_rows_with_tools(tmp_path: Path) -> None:
    u = Usage(input_tokens=100, tools={"Read": Usage.Tool(calls=5)})
    a = make_agent(model_usage={SONNET_4_5: u})
    s = _session(tmp_path, agents=[a], model_usage={SONNET_4_5: Usage(input_tokens=50)})
    rows = _monitor(tmp_path, show_tools=True)._collect_rows(s)
    tool_rows = [r for r in rows if isinstance(r[0], Text) and "Read" in r[0].plain]
    assert len(tool_rows) == 1


def test_totals_row_length(tmp_path: Path) -> None:
    s = _session(tmp_path, model_usage={SONNET_4_5: Usage(input_tokens=100)})
    assert len(_monitor(tmp_path)._totals_row(s)) == 11


def test_session_row_length(tmp_path: Path) -> None:
    s = _session(tmp_path, model_usage={SONNET_4_5: Usage(input_tokens=100)})
    assert len(_monitor(tmp_path)._session_row(s)) == 11


def test_agent_row_length(tmp_path: Path) -> None:
    a = make_agent(model_usage={SONNET_4_5: Usage(input_tokens=100)})
    assert len(_monitor(tmp_path)._agent_row(a, "done")) == 11


def test_tool_row_length() -> None:
    assert len(_monitor()._tool_row("Read", Usage.Tool(calls=5, errors=1))) == 11


@patch("time.sleep")
def test_display_on_quit(_sleep: object, tmp_path: Path) -> None:
    m = _monitor(tmp_path, key_listener_factory=fake_key_listener([Key.QUIT]))
    action, s = m.display_on(fake_console())
    assert action == Action.QUIT
    assert isinstance(s, Session)


@patch("time.sleep")
def test_display_on_back(_sleep: object, tmp_path: Path) -> None:
    m = _monitor(tmp_path, key_listener_factory=fake_key_listener([Key.LEFT]))
    action, _ = m.display_on(fake_console())
    assert action == Action.BACK


@patch("time.sleep")
def test_display_on_toggle_tools(_sleep: object, tmp_path: Path) -> None:
    m = _monitor(tmp_path, key_listener_factory=fake_key_listener([Key.TOOLS, Key.QUIT]))
    m.display_on(fake_console())
    assert m.show_tools is True


@patch("time.sleep")
def test_display_on_scroll(_sleep: object, tmp_path: Path) -> None:
    m = _monitor(tmp_path, key_listener_factory=fake_key_listener([Key.DOWN, Key.DOWN, Key.QUIT]))
    m.display_on(fake_console())
    assert m.scroll >= 0
