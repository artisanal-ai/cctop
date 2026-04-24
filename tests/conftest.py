from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from cctop.core.agents import Agent
from cctop.core.models import SONNET_4_5, ModelUsage
from cctop.core.session import Session
from cctop.core.usage import Usage
from cctop.views.keys import Key

TS_BASE = 1_700_000_000.0


def make_agent(agent_id: str = "a1", **overrides: Any) -> Agent:
    return Agent(id=agent_id, **overrides)


def make_ref(tmp_path: Path, name: str = "abc12345.jsonl", project_dir: str = "-test-project") -> Session.Ref:
    d = tmp_path / project_dir
    d.mkdir(parents=True, exist_ok=True)
    f = d / name
    f.write_text("")
    return Session.Ref(f)


@pytest.fixture()
def sample_usage() -> Usage:
    return Usage(
        input_tokens=1000, output_tokens=500,
        cache_creation_5m_tokens=150, cache_creation_1h_tokens=50, cache_read_tokens=100,
        tools={
            "Read": Usage.Tool(calls=5, errors=0),
            "Write": Usage.Tool(calls=3, errors=1),
        },
    )


@pytest.fixture()
def sample_model_usage(sample_usage: Usage) -> ModelUsage:
    return {SONNET_4_5: sample_usage}


def fake_key_listener(keys: list[Key | None]) -> type:
    class _FakeListener:
        def __init__(self) -> None:
            self._keys = iter(keys)

        def __enter__(self) -> "_FakeListener":
            return self

        def __exit__(self, *_: object) -> None:
            pass

        def read(self) -> Key | None:
            return next(self._keys, None)

    return _FakeListener


@contextmanager
def fake_live(content: Any, console: Any) -> Generator[MagicMock]:
    yield MagicMock()


def fake_console(height: int = 50) -> Console:
    c: Console = MagicMock(spec=Console)
    c.height = height
    return c
