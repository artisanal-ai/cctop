import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from rich.text import Text

from cctop.core.session import Session
from cctop.views.keys import Key
from cctop.views.picker import SessionPicker
from cctop.views.protocols import Action
from tests.conftest import TS_BASE, fake_console, fake_key_listener, fake_live, make_ref


def _picker(sessions: list[Session.Ref] | None = None, **kw: Any) -> SessionPicker:
    return SessionPicker(
        sessions_finder=lambda: sessions or [],
        live_view_factory=fake_live,
        **kw,
    )


@pytest.mark.parametrize(
    ("delta", "expected"),
    [(30, "just now"), (300, "5m ago"), (7200, "2h ago"), (172800, "2d ago")],
)
def test_age_formatting(delta: int, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: TS_BASE + delta)
    assert _picker()._age(TS_BASE) == expected


def test_row_selected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: TS_BASE)
    ref = make_ref(tmp_path)
    row = _picker()._row(ref, selected=True)
    assert isinstance(row[1], Text)


def test_row_unselected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: TS_BASE)
    ref = make_ref(tmp_path)
    row = _picker()._row(ref, selected=False)
    assert isinstance(row[0], str)


@patch("time.sleep")
def test_display_on_quit(_sleep: object) -> None:
    picker = _picker(key_listener_factory=fake_key_listener([Key.QUIT]))
    action, ref = picker.display_on(fake_console())
    assert action == Action.QUIT
    assert ref is None


@patch("time.sleep")
def test_display_on_select(_sleep: object, tmp_path: Path) -> None:
    refs = [make_ref(tmp_path)]
    picker = _picker(refs, key_listener_factory=fake_key_listener([Key.ENTER]))
    action, ref = picker.display_on(fake_console())
    assert action == Action.SELECT
    assert ref == refs[0]


@patch("time.sleep")
def test_display_on_navigate(_sleep: object, tmp_path: Path) -> None:
    refs = [make_ref(tmp_path, name=f"s{i}.jsonl") for i in range(3)]
    picker = _picker(refs, key_listener_factory=fake_key_listener([Key.DOWN, Key.ENTER]))
    action, ref = picker.display_on(fake_console())
    assert action == Action.SELECT
    assert ref == refs[1]


@patch("time.sleep")
def test_display_on_scrolls_past_visible_window(_sleep: object, tmp_path: Path) -> None:
    refs = [make_ref(tmp_path, name=f"s{i:03}.jsonl") for i in range(50)]
    keys = [Key.DOWN] * 30 + [Key.ENTER]
    picker = _picker(refs, key_listener_factory=fake_key_listener(keys))
    action, ref = picker.display_on(fake_console(height=10))
    assert action == Action.SELECT
    assert ref == refs[30]


@patch("time.sleep")
def test_display_on_scrolls_back_up(_sleep: object, tmp_path: Path) -> None:
    refs = [make_ref(tmp_path, name=f"s{i:03}.jsonl") for i in range(50)]
    keys = [Key.DOWN] * 30 + [Key.UP] * 25 + [Key.ENTER]
    picker = _picker(refs, key_listener_factory=fake_key_listener(keys))
    action, ref = picker.display_on(fake_console(height=10))
    assert action == Action.SELECT
    assert ref == refs[5]
