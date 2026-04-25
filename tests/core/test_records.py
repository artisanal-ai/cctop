import json
from pathlib import Path

from cctop.core.models import SONNET_4
from cctop.core.records import (
    assistant_records,
    model_usage,
    notification_records,
    raw_records,
    raw_subagents_records,
    user_records,
)
from tests.core.conftest import assistant_rec, notification_rec, user_rec


def test_assistant_records_basic() -> None:
    records = [assistant_rec()]
    result = list(assistant_records(records))
    assert len(result) == 1
    r = result[0]
    assert r.msg_id == "msg_001"
    assert r.model == "claude-sonnet-4-20250514"
    assert r.usage.input_tokens == 1000
    assert r.usage.output_tokens == 500
    assert r.stop_reason == "end_turn"


def test_assistant_records_dedup() -> None:
    records = [
        assistant_rec(msg_id="m1", usage={"input_tokens": 100, "output_tokens": 50}),
        assistant_rec(msg_id="m1", usage={"input_tokens": 200, "output_tokens": 100}),
    ]
    result = list(assistant_records(records))
    assert len(result) == 1
    assert result[0].usage.input_tokens == 200


def test_assistant_records_tool_invocations() -> None:
    content = [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}]
    records = [assistant_rec(content=content)]
    result = list(assistant_records(records))
    assert len(result[0].tool_invocations) == 1
    assert result[0].tool_invocations[0].name == "Read"
    assert result[0].agent_invocations == []


def test_assistant_records_agent_invocations() -> None:
    content = [
        {"type": "tool_use", "id": "a1", "name": "Agent",
         "input": {"description": "explore", "subagent_type": "Explore"}},
    ]
    records = [assistant_rec(content=content)]
    result = list(assistant_records(records))
    assert len(result[0].agent_invocations) == 1
    assert result[0].agent_invocations[0].description == "explore"
    assert result[0].agent_invocations[0].subtype == "Explore"
    assert result[0].tool_invocations == []


def test_assistant_records_skips_non_assistant() -> None:
    records = [{"type": "user", "timestamp": "2025-03-15T10:00:00Z", "message": {}}]
    assert list(assistant_records(records)) == []


def test_assistant_records_cache_defaults() -> None:
    records = [assistant_rec()]
    result = list(assistant_records(records))
    assert result[0].usage.cache_creation_5m_tokens == 0
    assert result[0].usage.cache_creation_1h_tokens == 0
    assert result[0].usage.cache_read_tokens == 0


def test_assistant_records_with_cache_legacy() -> None:
    records = [assistant_rec(usage={
        "input_tokens": 100, "output_tokens": 50,
        "cache_creation_input_tokens": 200, "cache_read_input_tokens": 100,
    })]
    result = list(assistant_records(records))
    assert result[0].usage.cache_creation_5m_tokens == 200
    assert result[0].usage.cache_creation_1h_tokens == 0
    assert result[0].usage.cache_read_tokens == 100


def test_assistant_records_with_cache_breakdown() -> None:
    records = [assistant_rec(usage={
        "input_tokens": 100, "output_tokens": 50,
        "cache_creation_input_tokens": 300,
        "cache_creation": {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 200},
        "cache_read_input_tokens": 50,
    })]
    result = list(assistant_records(records))
    assert result[0].usage.cache_creation_5m_tokens == 100
    assert result[0].usage.cache_creation_1h_tokens == 200
    assert result[0].usage.cache_read_tokens == 50


def test_assistant_records_agent_id() -> None:
    records = [assistant_rec(agent_id="abc123")]
    result = list(assistant_records(records))
    assert result[0].id == "abc123"


def test_user_records_basic() -> None:
    content = [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]
    records = [user_rec(content=content)]
    result = list(user_records(records))
    assert len(result) == 1
    assert len(result[0].tool_results) == 1
    assert result[0].tool_results[0].invocation_id == "t1"
    assert result[0].tool_results[0].is_error is False


def test_user_records_with_agent_result() -> None:
    content = [{"type": "tool_result", "tool_use_id": "inv1", "content": "done"}]
    tur = {"agentId": "abc123", "status": "completed"}
    records = [user_rec(content=content, tool_use_result=tur)]
    result = list(user_records(records))
    assert len(result[0].agent_results) == 1
    assert result[0].agent_results[0].id == "abc123"
    assert result[0].agent_results[0].status == "completed"


def test_user_records_error_flag() -> None:
    content = [{"type": "tool_result", "tool_use_id": "t1", "is_error": True}]
    records = [user_rec(content=content)]
    result = list(user_records(records))
    assert result[0].tool_results[0].is_error is True


def test_user_records_no_tool_use_result() -> None:
    content = [{"type": "tool_result", "tool_use_id": "t1"}]
    records = [user_rec(content=content)]
    result = list(user_records(records))
    assert result[0].agent_results == []


def test_notification_records_basic() -> None:
    xml = "<task-notification><task-id>tid1</task-id><status>completed</status></task-notification>"
    records = [notification_rec(xml)]
    result = list(notification_records(records))
    assert len(result) == 1
    assert result[0].task_id == "tid1"
    assert result[0].status == "completed"
    assert result[0].result is None


def test_notification_records_with_result() -> None:
    xml = (
        "<task-notification><task-id>tid1</task-id>"
        "<status>completed</status><result>done well</result></task-notification>"
    )
    records = [notification_rec(xml)]
    result = list(notification_records(records))
    assert result[0].result == "done well"


def test_notification_records_skips_missing_tags() -> None:
    records = [notification_rec("no xml here")]
    assert list(notification_records(records)) == []


def test_model_usage_aggregation() -> None:
    msgs = list(assistant_records([
        assistant_rec(msg_id="m1", model="claude-sonnet-4-20250514"),
        assistant_rec(msg_id="m2", model="claude-sonnet-4-20250514"),
    ]))
    user = list(user_records([]))
    result = model_usage(msgs, user)
    assert SONNET_4 in result
    assert result[SONNET_4].input_tokens == 2000


def test_model_usage_tool_errors() -> None:
    content = [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}]
    msgs = list(assistant_records([assistant_rec(content=content)]))
    user_content = [{"type": "tool_result", "tool_use_id": "t1", "is_error": True}]
    user = list(user_records([user_rec(content=user_content)]))
    result = model_usage(msgs, user)
    usage = result[SONNET_4]
    assert usage.tools["Read"].calls == 1
    assert usage.tools["Read"].errors == 1


def test_model_usage_unknown_model_skipped() -> None:
    msgs = list(assistant_records([assistant_rec(model="gpt-4o")]))
    result = model_usage(msgs, [])
    assert result == {}


def test_raw_records(tmp_path: Path) -> None:
    f = tmp_path / "test.jsonl"
    f.write_text(json.dumps({"a": 1}) + "\n" + json.dumps({"b": 2}) + "\n")
    result = raw_records(f)
    assert len(result) == 2
    assert result[0] == {"a": 1}


def test_raw_subagents_records_no_dir(tmp_path: Path) -> None:
    f = tmp_path / "session.jsonl"
    f.write_text("")
    assert raw_subagents_records(f) == []


def test_raw_subagents_records(tmp_path: Path) -> None:
    session_file = tmp_path / "session.jsonl"
    session_file.write_text("")
    subdir = tmp_path / "session" / "subagents"
    subdir.mkdir(parents=True)
    jsonl = subdir / "agent-abc123.jsonl"
    jsonl.write_text(json.dumps(assistant_rec(agent_id="abc123")) + "\n")
    (subdir / "agent-abc123.meta.json").write_text(json.dumps({"agentType": "Explore", "description": "search"}))
    result = raw_subagents_records(session_file)
    assert len(result) == 1
    agent_id, dispatched_ts, records, meta_dict = result[0]
    assert agent_id == "abc123"
    assert dispatched_ts == jsonl.stat().st_mtime
    assert len(records) == 1
    assert meta_dict is not None
    assert meta_dict["agentType"] == "Explore"


def test_raw_subagents_records_no_msgs(tmp_path: Path) -> None:
    session_file = tmp_path / "session.jsonl"
    session_file.write_text("")
    subdir = tmp_path / "session" / "subagents"
    subdir.mkdir(parents=True)
    (subdir / "agent-fresh.jsonl").write_text("")
    (subdir / "agent-fresh.meta.json").write_text(json.dumps({"agentType": "Explore"}))
    result = raw_subagents_records(session_file)
    assert len(result) == 1
    agent_id, _dispatched_ts, records, meta_dict = result[0]
    assert agent_id == "fresh"
    assert records == []
    assert meta_dict == {"agentType": "Explore"}


def test_raw_subagents_records_ignores_aside(tmp_path: Path) -> None:
    session_file = tmp_path / "session.jsonl"
    session_file.write_text("")
    subdir = tmp_path / "session" / "subagents"
    subdir.mkdir(parents=True)
    (subdir / "agent-aside_question-abc.jsonl").write_text(json.dumps(assistant_rec()) + "\n")
    assert raw_subagents_records(session_file) == []
