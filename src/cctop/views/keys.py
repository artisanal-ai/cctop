import os
import sys
import termios
import types
from enum import StrEnum
from typing import Any

_READ_BUFFER_SIZE = 32

_ARROW_UP = b"\x1b[A"
_ARROW_DOWN = b"\x1b[B"
_ARROW_LEFT = b"\x1b[D"
_ARROW_RIGHT = b"\x1b[C"

_CARRIAGE_RETURN = b"\r"
_NEWLINE = b"\n"


class Key(StrEnum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ENTER = "enter"
    TOOLS = "t"
    QUIT = "q"


_ESCAPE_SEQUENCES: dict[bytes, Key] = {
    _ARROW_UP: Key.UP,
    _ARROW_DOWN: Key.DOWN,
    _ARROW_LEFT: Key.LEFT,
    _ARROW_RIGHT: Key.RIGHT,
}

_SINGLE_KEYS: dict[bytes, Key] = {
    b"t": Key.TOOLS, b"T": Key.TOOLS,
    b"q": Key.QUIT,  b"Q": Key.QUIT,
}


def _parse(data: bytes) -> Key | None:
    for sequence, key in _ESCAPE_SEQUENCES.items():
        if sequence in data:
            return key
    if _CARRIAGE_RETURN in data or _NEWLINE in data:
        return Key.ENTER
    for char, key in _SINGLE_KEYS.items():
        if char in data:
            return key
    return None


def _enable_raw_mode(fd: int) -> None:
    attrs = termios.tcgetattr(fd)
    attrs[3] &= ~(termios.ICANON | termios.ECHO)
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def _restore_mode(fd: int, original: list[Any]) -> None:
    termios.tcsetattr(fd, termios.TCSADRAIN, original)


class KeyListener:
    _fd: int
    _original_attrs: list[Any]

    def __enter__(self) -> "KeyListener":
        self._fd = sys.stdin.fileno()
        self._original_attrs = termios.tcgetattr(self._fd)
        _enable_raw_mode(self._fd)
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: types.TracebackType | None,
    ) -> None:
        _restore_mode(self._fd, self._original_attrs)

    def read(self) -> Key | None:
        data = os.read(self._fd, _READ_BUFFER_SIZE)
        return _parse(data) if data else None
