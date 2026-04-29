import types
from contextlib import AbstractContextManager
from enum import StrEnum

from blessed import Terminal
from blessed.keyboard import Keystroke


class Key(StrEnum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ENTER = "enter"
    TOOLS = "t"
    QUIT = "q"


_KEY_NAMES: dict[str, Key] = {
    "KEY_UP": Key.UP,
    "KEY_DOWN": Key.DOWN,
    "KEY_LEFT": Key.LEFT,
    "KEY_RIGHT": Key.RIGHT,
    "KEY_ENTER": Key.ENTER,
}

_CHARS: dict[str, Key] = {
    "\r": Key.ENTER,
    "\n": Key.ENTER,
    "t": Key.TOOLS,
    "q": Key.QUIT,
}


def _map(ks: Keystroke) -> Key | None:
    if ks.is_sequence and ks.name in _KEY_NAMES:
        return _KEY_NAMES[ks.name]
    return _CHARS.get(ks.lower())


class KeyListener:
    _term: Terminal
    _cbreak: AbstractContextManager[None]

    def __enter__(self) -> "KeyListener":
        self._term = Terminal()
        self._cbreak = self._term.cbreak()
        self._cbreak.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        self._cbreak.__exit__(exc_type, exc_val, exc_tb)

    def read(self) -> Key | None:
        ks = self._term.inkey(timeout=0)
        return _map(ks) if ks else None
