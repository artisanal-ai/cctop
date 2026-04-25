import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from cctop.core.agents import AgentStatus
from cctop.core.models import OPUS_4_6, SONNET_4_5
from cctop.core.session import Session, session, session_refs
from cctop.core.usage import Usage
from tests.conftest import TS_BASE, make_agent, make_ref
from tests.core.conftest import assistant_rec, user_rec


def test_ref_id(tmp_path: Path) -> None:
    ref = make_ref(tmp_path, name="abc12345-6789.jsonl")
    assert ref.id == "abc12345-6789"


def test_ref_short_id(tmp_path: Path) -> None:
    ref = make_ref(tmp_path, name="abc12345-6789.jsonl")
    assert ref.short_id == "abc12345"


@pytest.mark.parametrize(
    ("dir_name", "expected"),
    [("-Users-me-myproject", "myproject"), ("-home-user-app", "app"), ("simple", "simple")],
)
def test_ref_project(tmp_path: Path, dir_name: str, expected: str) -> None:
    ref = make_ref(tmp_path, project_dir=dir_name)
    assert ref.project == expected


def test_ref_mtime_existing(tmp_path: Path) -> None:
    ref = make_ref(tmp_path)
    assert ref.mtime > 0


def test_ref_mtime_missing() -> None:
    ref = Session.Ref(Path("/nonexistent/path/session.jsonl"))
    assert ref.mtime == 0.0


def test_session_usage(tmp_path: Path) -> None:
    u = Usage(input_tokens=1000, output_tokens=500)
    s = Session(ref=make_ref(tmp_path), model_usage={SONNET_4_5: u})
    assert s.usage.input_tokens == 1000


def test_session_cost(tmp_path: Path) -> None:
    u = Usage(input_tokens=1_000_000)
    s = Session(ref=make_ref(tmp_path), model_usage={OPUS_4_6: u})
    assert s.cost == pytest.approx(5.0)


def test_session_total_usage(tmp_path: Path) -> None:
    session_u = Usage(input_tokens=100)
    agent_u = Usage(input_tokens=200)
    a = make_agent(model_usage={SONNET_4_5: agent_u})
    s = Session(ref=make_ref(tmp_path), agents=[a], model_usage={SONNET_4_5: session_u})
    assert s.total_usage.input_tokens == 300


def test_session_total_cost(tmp_path: Path) -> None:
    agent_u = Usage(input_tokens=1_000_000)
    session_u = Usage(input_tokens=1_000_000)
    a = make_agent(model_usage={OPUS_4_6: agent_u})
    s = Session(ref=make_ref(tmp_path), agents=[a], model_usage={OPUS_4_6: session_u})
    assert s.total_cost == pytest.approx(10.0)


def test_session_status_override(tmp_path: Path) -> None:
    a = make_agent(model_usage={SONNET_4_5: Usage(input_tokens=100)})
    s = Session(ref=make_ref(tmp_path), agents=[a], statuses={"a1": AgentStatus.DONE})
    assert s.status(a) == AgentStatus.DONE


def test_session_status_fallback(tmp_path: Path) -> None:
    a = make_agent(model_usage={SONNET_4_5: Usage(input_tokens=100)})
    s = Session(ref=make_ref(tmp_path), agents=[a])
    assert s.status(a) == AgentStatus.RUNNING


def test_session_elapsed_seconds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: TS_BASE + 120.0)
    s = Session(ref=make_ref(tmp_path), first_ts=TS_BASE)
    assert s.elapsed_seconds == pytest.approx(120.0)


def test_session_wall_seconds(tmp_path: Path) -> None:
    s = Session(ref=make_ref(tmp_path), first_ts=1000.0, last_ts=1060.0)
    assert s.wall_seconds == pytest.approx(60.0)


def test_session_wall_seconds_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: TS_BASE + 60.0)
    s = Session(ref=make_ref(tmp_path), first_ts=TS_BASE)
    assert s.wall_seconds == pytest.approx(60.0)


def test_session_done_count(tmp_path: Path) -> None:
    agents = [make_agent("a1"), make_agent("a2"), make_agent("a3")]
    statuses = {"a1": AgentStatus.DONE, "a2": AgentStatus.FAILED, "a3": AgentStatus.RUNNING}
    s = Session(ref=make_ref(tmp_path), agents=agents, statuses=statuses)
    assert s.done_count == 2


def test_session_alive_recent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref = make_ref(tmp_path)
    mtime = ref.mtime
    monkeypatch.setattr(time, "time", lambda: mtime + 10.0)
    s = Session(ref=ref)
    assert s.alive is True


def test_session_alive_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref = make_ref(tmp_path)
    mtime = ref.mtime
    monkeypatch.setattr(time, "time", lambda: mtime + 60.0)
    s = Session(ref=ref)
    assert s.alive is False


def test_session_active_with_running_agent(tmp_path: Path) -> None:
    a = make_agent(model_usage={SONNET_4_5: Usage(input_tokens=100)})
    s = Session(ref=make_ref(tmp_path), agents=[a])
    assert s.active is True


def test_session_refs(tmp_path: Path) -> None:
    proj = tmp_path / "project"
    proj.mkdir()
    older = proj / "older.jsonl"
    newer = proj / "newer.jsonl"
    older.write_text("")
    newer.write_text("")
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))
    refs = list(session_refs(tmp_path))
    assert len(refs) == 2
    assert refs[0].id == "newer"
    assert refs[1].id == "older"


def test_session_refs_empty(tmp_path: Path) -> None:
    assert list(session_refs(tmp_path)) == []


def test_session_factory(tmp_path: Path) -> None:
    proj = tmp_path / "-test-project"
    proj.mkdir()
    session_file = proj / "abc12345.jsonl"
    parent = assistant_rec(
        msg_id="pm1", model="claude-opus-4-20250514",
        usage={"input_tokens": 2000, "output_tokens": 1000},
        content=[{"type": "tool_use", "id": "inv1", "name": "Agent",
                  "input": {"description": "explore", "subagent_type": "Explore"}}],
    )
    agent_result: dict[str, Any] = user_rec(
        ts="2025-03-15T10:02:00Z",
        content=[{"type": "tool_result", "tool_use_id": "inv1",
                  "content": [{"type": "text", "text": "done"}]}],
        tool_use_result={"agentId": "abc123", "status": "completed"},
    )
    session_file.write_text(json.dumps(parent) + "\n" + json.dumps(agent_result) + "\n")

    subdir = proj / "abc12345" / "subagents"
    subdir.mkdir(parents=True)
    subagent = assistant_rec(
        msg_id="am1", ts="2025-03-15T10:01:00Z", agent_id="abc123",
        usage={"input_tokens": 500, "output_tokens": 200},
    )
    (subdir / "agent-abc123.jsonl").write_text(json.dumps(subagent) + "\n")
    (subdir / "agent-abc123.meta.json").write_text(json.dumps({"agentType": "Explore", "description": "explore"}))

    ref = Session.Ref(session_file)
    s = session(ref)
    assert s.ref == ref
    assert len(s.agents) == 1
    assert s.agents[0].id == "abc123"
    assert s.agents[0].type == "Explore"
    assert s.usage.input_tokens == 2000
    assert s.statuses.get("abc123") == AgentStatus.DONE


def test_session_agents_sorted_newest_first(tmp_path: Path) -> None:
    proj = tmp_path / "-test-project"
    proj.mkdir()
    session_file = proj / "abc12345.jsonl"
    session_file.write_text("")
    subdir = proj / "abc12345" / "subagents"
    subdir.mkdir(parents=True)

    earlier = assistant_rec(msg_id="m_a", ts="2025-03-15T10:01:00Z", agent_id="aaa")
    later = assistant_rec(msg_id="m_z", ts="2025-03-15T10:05:00Z", agent_id="zzz")
    (subdir / "agent-aaa.jsonl").write_text(json.dumps(earlier) + "\n")
    (subdir / "agent-zzz.jsonl").write_text(json.dumps(later) + "\n")

    s = session(Session.Ref(session_file))
    assert [a.id for a in s.agents] == ["zzz", "aaa"]


def test_session_dispatched_agent_no_msgs(tmp_path: Path) -> None:
    proj = tmp_path / "-test-project"
    proj.mkdir()
    session_file = proj / "abc12345.jsonl"
    session_file.write_text("")
    subdir = proj / "abc12345" / "subagents"
    subdir.mkdir(parents=True)
    (subdir / "agent-fresh.jsonl").write_text("")
    (subdir / "agent-fresh.meta.json").write_text(json.dumps({"agentType": "Explore"}))

    s = session(Session.Ref(session_file))
    assert len(s.agents) == 1
    assert s.agents[0].id == "fresh"
    assert s.agents[0].type == "Explore"
    assert s.agents[0].internal_status == AgentStatus.DISPATCHED
