from typing import Any


def assistant_rec(
    msg_id: str = "msg_001",
    model: str = "claude-sonnet-4-20250514",
    ts: str = "2025-03-15T10:00:00Z",
    content: list[dict[str, Any]] | None = None,
    usage: dict[str, int] | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "id": msg_id,
            "model": model,
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 1000, "output_tokens": 500, **(usage or {})},
            "content": content or [{"type": "text", "text": "hello"}],
        },
    }
    if agent_id:
        rec["agentId"] = agent_id
    return rec


def user_rec(
    ts: str = "2025-03-15T10:01:00Z",
    content: list[dict[str, Any]] | None = None,
    tool_use_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "type": "user",
        "timestamp": ts,
        "message": {"content": content or []},
    }
    if tool_use_result is not None:
        rec["toolUseResult"] = tool_use_result
    return rec


def notification_rec(content: str) -> dict[str, Any]:
    return {"type": "queue-operation", "operation": "enqueue", "content": content}
