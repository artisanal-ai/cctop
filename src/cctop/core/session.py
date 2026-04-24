import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from cctop.core.agents import Agent, AgentStatus, agent
from cctop.core.models import ModelUsage
from cctop.core.records import (
    QueueOperationRecord,
    UserRecord,
    assistant_records,
    model_usage,
    notification_records,
    raw_records,
    raw_subagents_records,
    tool_error_ids,
    user_records,
)
from cctop.core.usage import Usage

_DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass(frozen=True, slots=True)
class Session:

    @dataclass(frozen=True, slots=True)
    class Ref:
        path: Path

        @property
        def mtime(self) -> float:
            return self.path.stat().st_mtime if self.path.exists() else 0.0

        @property
        def id(self) -> str:
            return self.path.stem

        @property
        def short_id(self) -> str:
            return self.path.stem[:8]

        @property
        def project(self) -> str:
            return Path(self.path.parent.name.lstrip("-").replace("-", "/")).name

    ref: Ref
    agents: list[Agent] = field(default_factory=list)
    statuses: dict[str, AgentStatus] = field(default_factory=dict)
    first_ts: float = 0.0
    last_ts: float = 0.0
    model_usage: ModelUsage = field(default_factory=dict)

    def status(self, agent: Agent) -> AgentStatus:
        return self.statuses.get(agent.id, agent.internal_status)

    @property
    def usage(self) -> Usage:
        return sum(self.model_usage.values(), Usage())

    @property
    def cost(self) -> float:
        return sum(m.cost(u) for m, u in self.model_usage.items())

    @property
    def total_usage(self) -> Usage:
        return sum((a.usage for a in self.agents), Usage()) + self.usage

    @property
    def total_cost(self) -> float:
        return sum(a.cost for a in self.agents) + self.cost

    @property
    def elapsed_seconds(self) -> float:
        if self.first_ts:
            return max(0.0, time.time() - self.first_ts)
        return 0.0

    @property
    def wall_seconds(self) -> float:
        if self.first_ts and self.last_ts:
            return max(0.0, self.last_ts - self.first_ts)
        return self.elapsed_seconds

    @property
    def done_count(self) -> int:
        return sum(1 for a in self.agents if self.status(a) in _DONE_STATUSES)

    @property
    def alive(self) -> bool:
        if self.ref.mtime:
            return (time.time() - self.ref.mtime) < 30
        return False

    @property
    def active(self) -> bool:
        return any(self.status(a) in _ACTIVE_STATUSES for a in self.agents) or self.alive



_DONE_STATUSES = frozenset({AgentStatus.DONE, AgentStatus.FAILED, AgentStatus.RATE_LIMITED})
_ACTIVE_STATUSES = frozenset({AgentStatus.RUNNING, AgentStatus.DISPATCHED})


def session_refs(projects_dir: Path = _DEFAULT_PROJECTS_DIR) -> Iterator[Session.Ref]:
    if projects_dir.is_dir():
        yield from sorted(
            (
                Session.Ref(f)
                for d in projects_dir.iterdir() if d.is_dir()
                for f in d.glob("*.jsonl")
            ),
            key=lambda s: s.mtime,
            reverse=True,
        )


def session(ref: Session.Ref) -> Session:
    parent_records, subagents = raw_records(ref.path), raw_subagents_records(ref.path)
    user = list(user_records(parent_records))
    msgs = list(assistant_records(parent_records, tool_error_ids(user)))
    notifications = list(notification_records(parent_records))

    agents = sorted((agent(*sa) for sa in subagents), key=lambda a: a.first_ts, reverse=True)

    return Session(
        ref=ref,
        agents=agents,
        statuses=_user_statuses(user) | _notification_statuses(notifications),
        first_ts=msgs[0].timestamp if msgs else 0.0,
        last_ts=msgs[-1].timestamp if msgs else 0.0,
        model_usage=model_usage(msgs),
    )


def _user_statuses(user: list[UserRecord]) -> dict[str, AgentStatus]:
    return {
        ar.id: AgentStatus.DONE
        for r in user for ar in r.agent_results
        if ar.status == "completed"
    }


def _notification_statuses(notifications: list[QueueOperationRecord]) -> dict[str, AgentStatus]:
    statuses: dict[str, AgentStatus] = {}
    for n in notifications:
        if n.status == "killed":
            statuses[n.task_id] = AgentStatus.FAILED
        elif n.status == "completed" and n.result and "rate limited" in n.result.lower():
            statuses[n.task_id] = AgentStatus.RATE_LIMITED
        elif n.status == "completed":
            statuses[n.task_id] = AgentStatus.DONE
    return statuses
