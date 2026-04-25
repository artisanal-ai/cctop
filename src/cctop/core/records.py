import json
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from cctop.core.models import Model, ModelUsage, model
from cctop.core.usage import Usage

type Record = dict[str, Any]
type AgentRecords = tuple[str, float, list[Record], Record | None]


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    id: str
    timestamp: float
    name: str


@dataclass(frozen=True, slots=True)
class ToolResult:
    invocation_id: str
    is_error: bool


@dataclass(frozen=True, slots=True)
class AgentInvocation:
    id: str
    timestamp: float
    description: str | None = None
    subtype: str | None = None


@dataclass(frozen=True, slots=True)
class AgentResult:
    invocation_id: str
    id: str
    status: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantRecord:
    msg_id: str
    timestamp: float
    model: str | None
    stop_reason: str | None
    usage: Usage
    tool_invocations: list[ToolInvocation]
    agent_invocations: list[AgentInvocation]
    id: str | None = None


@dataclass(frozen=True, slots=True)
class UserRecord:
    timestamp: float
    tool_results: list[ToolResult]
    agent_results: list[AgentResult]


@dataclass(frozen=True, slots=True)
class QueueOperationRecord:
    task_id: str
    status: str
    result: str | None = None


def _parse_usage(u: dict[str, Any]) -> Usage:
    cache = u.get("cache_creation", {})
    cache_5m = cache.get("ephemeral_5m_input_tokens", 0)
    cache_1h = cache.get("ephemeral_1h_input_tokens", 0)
    if not cache:
        cache_5m = u.get("cache_creation_input_tokens", 0)
    return Usage(
        input_tokens=u["input_tokens"],
        output_tokens=u["output_tokens"],
        cache_creation_5m_tokens=cache_5m,
        cache_creation_1h_tokens=cache_1h,
        cache_read_tokens=u.get("cache_read_input_tokens", 0),
    )


def _assistant_record(rec: Record) -> AssistantRecord:
    msg = rec["message"]
    u = msg["usage"]
    ts = datetime.fromisoformat(rec["timestamp"]).timestamp()
    tools = [b for b in msg.get("content", []) if b.get("type") == "tool_use"]
    return AssistantRecord(
        msg_id=msg["id"],
        timestamp=ts,
        model=msg.get("model"),
        stop_reason=msg.get("stop_reason"),
        usage=_parse_usage(u),
        tool_invocations=[
            ToolInvocation(id=b["id"], name=b["name"], timestamp=ts)
            for b in tools if b["name"] != "Agent"
        ],
        agent_invocations=[
            AgentInvocation(
                id=b["id"],
                timestamp=ts,
                description=b.get("input", {}).get("description"),
                subtype=b.get("input", {}).get("subagent_type"),
            )
            for b in tools if b["name"] == "Agent"
        ],
        id=rec.get("agentId"),
    )


def _user_record(rec: Record) -> UserRecord:
    raw_tur = rec.get("toolUseResult")
    tur = raw_tur if isinstance(raw_tur, dict) else {}
    agent_id: str | None = tur.get("agentId")
    blocks = [
        b for b in rec["message"].get("content", [])
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    return UserRecord(
        timestamp=datetime.fromisoformat(rec["timestamp"]).timestamp(),
        tool_results=[
            ToolResult(invocation_id=b["tool_use_id"], is_error=bool(b.get("is_error")))
            for b in blocks
        ],
        agent_results=[
            AgentResult(
                invocation_id=b["tool_use_id"],
                id=agent_id,
                status=tur.get("status"),
            )
            for b in blocks
            if agent_id
        ],
    )


_TASK_ID_RE = re.compile(r"<task-id>(.*?)</task-id>")
_STATUS_RE = re.compile(r"<status>(.*?)</status>")
_RESULT_RE = re.compile(r"<result>(.*?)</result>", re.DOTALL)


def _queue_operation_record(rec: Record) -> QueueOperationRecord:
    content: str = rec["content"]
    tid = _TASK_ID_RE.search(content)
    st = _STATUS_RE.search(content)
    res = _RESULT_RE.search(content)
    assert tid and st
    return QueueOperationRecord(
        task_id=tid.group(1),
        status=st.group(1),
        result=res.group(1) if res else None,
    )


def assistant_records(records: list[Record]) -> Iterator[AssistantRecord]:
    by_id: dict[str, AssistantRecord] = {}
    for rec in records:
        if rec.get("type") == "assistant":
            r = _assistant_record(rec)
            by_id[r.msg_id] = r
    yield from by_id.values()


def user_records(records: list[Record]) -> Iterator[UserRecord]:
    for rec in records:
        if rec.get("type") == "user":
            yield _user_record(rec)


def notification_records(records: list[Record]) -> Iterator[QueueOperationRecord]:
    for rec in records:
        if rec.get("type") == "queue-operation" and "<task-id>" in rec.get("content", ""):
            yield _queue_operation_record(rec)


def model_usage(msgs: list[AssistantRecord], user: list[UserRecord]) -> ModelUsage:
    error_ids = frozenset(
        tr.invocation_id for r in user for tr in r.tool_results if tr.is_error
    )
    by_model: dict[Model, list[AssistantRecord]] = {}
    for r in msgs:
        if r.model and (m := model(r.model)):
            by_model.setdefault(m, []).append(r)
    return {
        m: sum((_full_usage(r, error_ids) for r in records), Usage())
        for m, records in by_model.items()
    }


def _full_usage(record: AssistantRecord, error_ids: frozenset[str]) -> Usage:
    calls = Counter(tu.name for tu in record.tool_invocations)
    errors = Counter(tu.name for tu in record.tool_invocations if tu.id in error_ids)
    return replace(
        record.usage,
        tools={name: Usage.Tool(calls=calls[name], errors=errors[name]) for name in calls},
    )


def raw_records(path: Path) -> list[Record]:
    with open(path) as f:
        return [json.loads(line) for line in f]


_IGNORED_AGENTS = frozenset({"aside_question"})
_AGENT_FILE_PREFIX = "agent-"


def raw_subagents_records(path: Path) -> list[AgentRecords]:
    subagent_dir = path.parent / path.stem / "subagents"
    if not subagent_dir.is_dir():
        return []
    return [
        (
            f.stem.removeprefix(_AGENT_FILE_PREFIX),
            f.stat().st_mtime,
            raw_records(f),
            json.loads(meta.read_text()) if meta.is_file() else None,
        )
        for f in sorted(subagent_dir.glob("agent-*.jsonl"))
        if not any(tag in f.stem for tag in _IGNORED_AGENTS)
        for meta in [f.with_suffix(".meta.json")]
    ]
