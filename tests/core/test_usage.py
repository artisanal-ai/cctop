import pytest

from cctop.core.usage import Usage


@pytest.mark.parametrize(("cw5", "cw1", "cr", "expected"), [(100, 100, 100, 300), (0, 0, 0, 0), (500, 0, 0, 500)])
def test_usage_cache_tokens(cw5: int, cw1: int, cr: int, expected: int) -> None:
    u = Usage(cache_creation_5m_tokens=cw5, cache_creation_1h_tokens=cw1, cache_read_tokens=cr)
    assert u.cache_tokens == expected


@pytest.mark.parametrize(
    ("inp", "out", "cw5", "cw1", "cr", "expected"),
    [(100, 50, 20, 10, 20, 200), (0, 0, 0, 0, 0, 0), (1000, 0, 0, 0, 0, 1000)],
)
def test_usage_total_tokens(inp: int, out: int, cw5: int, cw1: int, cr: int, expected: int) -> None:
    u = Usage(
        input_tokens=inp, output_tokens=out,
        cache_creation_5m_tokens=cw5, cache_creation_1h_tokens=cw1, cache_read_tokens=cr,
    )
    assert u.total_tokens == expected


def test_usage_cache_creation_tokens() -> None:
    u = Usage(cache_creation_5m_tokens=150, cache_creation_1h_tokens=50)
    assert u.cache_creation_tokens == 200


@pytest.mark.parametrize(
    ("tools", "expected"),
    [({}, 0), ({"R": Usage.Tool(calls=5), "W": Usage.Tool(calls=3)}, 8)],
)
def test_usage_tool_calls(tools: dict[str, Usage.Tool], expected: int) -> None:
    assert Usage(tools=tools).tool_calls == expected


@pytest.mark.parametrize(
    ("tools", "expected"),
    [({}, 0), ({"R": Usage.Tool(errors=1), "W": Usage.Tool(errors=2)}, 3)],
)
def test_usage_tool_errors(tools: dict[str, Usage.Tool], expected: int) -> None:
    assert Usage(tools=tools).tool_errors == expected


def test_usage_add() -> None:
    a = Usage(input_tokens=100, output_tokens=50, cache_creation_5m_tokens=10, cache_creation_1h_tokens=5,
              tools={"R": Usage.Tool(calls=2, errors=1)})
    b = Usage(input_tokens=200, output_tokens=100, cache_creation_5m_tokens=20, cache_creation_1h_tokens=15,
              tools={"R": Usage.Tool(calls=3, errors=0), "W": Usage.Tool(calls=1)})
    result = a + b
    assert result.input_tokens == 300
    assert result.output_tokens == 150
    assert result.cache_creation_5m_tokens == 30
    assert result.cache_creation_1h_tokens == 20
    assert result.tools["R"] == Usage.Tool(calls=5, errors=1)
    assert result.tools["W"] == Usage.Tool(calls=1, errors=0)


def test_tool_add() -> None:
    assert Usage.Tool(calls=2, errors=1) + Usage.Tool(calls=3, errors=2) == Usage.Tool(calls=5, errors=3)


def test_core_reexports() -> None:
    from cctop.core import Agent, Session
    from cctop.core import Usage as CoreUsage
    assert CoreUsage is Usage
    assert Agent is not None
    assert Session is not None
