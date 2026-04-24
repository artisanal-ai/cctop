from cctop.views.keys import Key, _parse


def test_parse_arrow_up() -> None:
    assert _parse(b"\x1b[A") == Key.UP


def test_parse_arrow_down() -> None:
    assert _parse(b"\x1b[B") == Key.DOWN


def test_parse_arrow_left() -> None:
    assert _parse(b"\x1b[D") == Key.LEFT


def test_parse_arrow_right() -> None:
    assert _parse(b"\x1b[C") == Key.RIGHT


def test_parse_enter_cr() -> None:
    assert _parse(b"\r") == Key.ENTER


def test_parse_enter_newline() -> None:
    assert _parse(b"\n") == Key.ENTER


def test_parse_quit() -> None:
    assert _parse(b"q") == Key.QUIT


def test_parse_quit_uppercase() -> None:
    assert _parse(b"Q") == Key.QUIT


def test_parse_tools() -> None:
    assert _parse(b"t") == Key.TOOLS


def test_parse_unknown() -> None:
    assert _parse(b"x") is None


def test_parse_empty() -> None:
    assert _parse(b"") is None


def test_parse_escape_takes_priority() -> None:
    assert _parse(b"\x1b[A" + b"q") == Key.UP
