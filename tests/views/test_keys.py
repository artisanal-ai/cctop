from blessed.keyboard import Keystroke

from cctop.views.keys import Key, _map


def _seq(name: str) -> Keystroke:
    return Keystroke(ucs="\x00", code=1, name=name)


def _char(c: str) -> Keystroke:
    return Keystroke(ucs=c)


def test_map_arrow_up() -> None:
    assert _map(_seq("KEY_UP")) == Key.UP


def test_map_arrow_down() -> None:
    assert _map(_seq("KEY_DOWN")) == Key.DOWN


def test_map_arrow_left() -> None:
    assert _map(_seq("KEY_LEFT")) == Key.LEFT


def test_map_arrow_right() -> None:
    assert _map(_seq("KEY_RIGHT")) == Key.RIGHT


def test_map_enter_keycode() -> None:
    assert _map(_seq("KEY_ENTER")) == Key.ENTER


def test_map_enter_cr() -> None:
    assert _map(_char("\r")) == Key.ENTER


def test_map_enter_newline() -> None:
    assert _map(_char("\n")) == Key.ENTER


def test_map_quit() -> None:
    assert _map(_char("q")) == Key.QUIT


def test_map_quit_uppercase() -> None:
    assert _map(_char("Q")) == Key.QUIT


def test_map_tools() -> None:
    assert _map(_char("t")) == Key.TOOLS


def test_map_tools_uppercase() -> None:
    assert _map(_char("T")) == Key.TOOLS


def test_map_unknown_char() -> None:
    assert _map(_char("x")) is None


def test_map_unknown_sequence() -> None:
    assert _map(_seq("KEY_F1")) is None
