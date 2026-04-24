import time
from dataclasses import dataclass, field
from enum import StrEnum

from cctop.core.models import ModelUsage
from cctop.core.records import Record, assistant_records, model_usage, tool_error_ids, user_records
from cctop.core.usage import Usage


class AgentStatus(StrEnum):
    DONE = "done"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    RUNNING = "running"
    DISPATCHED = "dispatched"


@dataclass(frozen=True, slots=True)
class Agent:
    id: str
    type: str | None = None
    description: str | None = None
    first_ts: float = 0.0
    last_ts: float = 0.0
    model_usage: ModelUsage = field(default_factory=dict)

    @property
    def usage(self) -> Usage:
        return sum(self.model_usage.values(), Usage())

    @property
    def cost(self) -> float:
        return sum(m.cost(u) for m, u in self.model_usage.items())

    @property
    def wall_seconds(self) -> float:
        if self.first_ts and self.last_ts:
            return max(0.0, self.last_ts - self.first_ts)
        return 0.0

    @property
    def elapsed_seconds(self) -> float:
        if self.first_ts:
            return max(0.0, time.time() - self.first_ts)
        return 0.0

    @property
    def internal_status(self) -> AgentStatus:
        return AgentStatus.RUNNING if self.usage.total_tokens > 0 else AgentStatus.DISPATCHED


def agent(agent_id: str, dispatched_ts: float, records: list[Record], meta: Record | None) -> Agent:
    user = list(user_records(records))
    msgs = list(assistant_records(records, tool_error_ids(user)))
    m = meta or {}
    timestamps = [r.timestamp for r in msgs if r.timestamp]

    return Agent(
        id=next((r.id for r in msgs if r.id), agent_id),
        type=m.get("agentType") or None,
        description=m.get("description") or None,
        first_ts=min(timestamps, default=dispatched_ts),
        last_ts=max(timestamps, default=dispatched_ts),
        model_usage=model_usage(msgs),
    )

