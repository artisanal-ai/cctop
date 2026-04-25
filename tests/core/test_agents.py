import time
from typing import Any

import pytest

from cctop.core.agents import Agent, AgentStatus, agent
from cctop.core.models import OPUS_4_6, SONNET_4_5
from cctop.core.usage import Usage
from tests.conftest import TS_BASE
from tests.core.conftest import assistant_rec


def test_agent_usage_aggregation() -> None:
    u1 = Usage(input_tokens=100, output_tokens=50)
    u2 = Usage(input_tokens=200, output_tokens=100)
    a = Agent(id="a1", model_usage={OPUS_4_6: u1, SONNET_4_5: u2})
    assert a.usage.input_tokens == 300
    assert a.usage.output_tokens == 150


def test_agent_cost() -> None:
    u = Usage(input_tokens=1_000_000)
    a = Agent(id="a1", model_usage={OPUS_4_6: u})
    assert a.cost == pytest.approx(5.0)


@pytest.mark.parametrize(
    ("first", "last", "expected"),
    [(1000.0, 1060.0, 60.0), (0.0, 1060.0, 0.0), (0.0, 0.0, 0.0)],
)
def test_agent_wall_seconds(first: float, last: float, expected: float) -> None:
    assert Agent(id="a1", first_ts=first, last_ts=last).wall_seconds == pytest.approx(expected)


def test_agent_elapsed_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: TS_BASE + 60.0)
    a = Agent(id="a1", first_ts=TS_BASE)
    assert a.elapsed_seconds == pytest.approx(60.0)


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [(100, AgentStatus.RUNNING), (0, AgentStatus.DISPATCHED)],
)
def test_agent_internal_status(tokens: int, expected: AgentStatus) -> None:
    a = Agent(id="a1", model_usage={SONNET_4_5: Usage(input_tokens=tokens)} if tokens else {})
    assert a.internal_status == expected


def test_agent_factory() -> None:
    records = [assistant_rec(msg_id="m1", agent_id="abc123", usage={"input_tokens": 500, "output_tokens": 200})]
    meta: dict[str, Any] = {"agentType": "Explore", "description": "search files"}
    a = agent("abc123", TS_BASE, records, meta)
    assert a.id == "abc123"
    assert a.type == "Explore"
    assert a.description == "search files"
    assert a.usage.input_tokens == 500


def test_agent_factory_no_meta() -> None:
    records = [assistant_rec(msg_id="m1", agent_id="abc123", usage={"input_tokens": 500, "output_tokens": 200})]
    a = agent("abc123", TS_BASE, records, None)
    assert a.id == "abc123"
    assert a.type is None
    assert a.description is None


def test_agent_factory_no_msgs() -> None:
    meta: dict[str, Any] = {"agentType": "Explore", "description": "search files"}
    a = agent("abc123", TS_BASE, [], meta)
    assert a.id == "abc123"
    assert a.type == "Explore"
    assert a.description == "search files"
    assert a.first_ts == TS_BASE
    assert a.last_ts == TS_BASE
    assert a.usage.total_tokens == 0
    assert a.internal_status == AgentStatus.DISPATCHED


def test_agent_factory_no_msgs_no_meta() -> None:
    a = agent("abc123", TS_BASE, [], None)
    assert a.id == "abc123"
    assert a.type is None
    assert a.first_ts == TS_BASE
    assert a.internal_status == AgentStatus.DISPATCHED
