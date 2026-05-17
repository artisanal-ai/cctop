import json
import os
import platform
import subprocess
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

_API_URL = "https://api.anthropic.com/api/oauth/usage"
_ENV_TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
_KEYCHAIN_SERVICE = "Claude Code-credentials"
_CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
_HTTP_TIMEOUT = 5.0


@dataclass(frozen=True, slots=True)
class Bucket:
    utilization: float
    resets_at: datetime


@dataclass(frozen=True, slots=True)
class Quota:
    five_hour: Bucket
    seven_day: Bucket


def _extract_token(blob: str) -> str | None:
    value = json.loads(blob).get("claudeAiOauth", {}).get("accessToken")
    return value if isinstance(value, str) else None


def _keychain_token() -> str | None:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", _KEYCHAIN_SERVICE, "-w"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return None
    return _extract_token(result.stdout)


def _file_token() -> str | None:
    if not _CREDS_PATH.is_file():
        return None
    return _extract_token(_CREDS_PATH.read_text(encoding="utf-8"))


def _token() -> str | None:
    if t := os.environ.get(_ENV_TOKEN):
        return t
    if platform.system() == "Darwin":
        return _keychain_token()
    return _file_token()


def _bucket(d: dict[str, Any]) -> Bucket:
    return Bucket(utilization=float(d["utilization"]), resets_at=datetime.fromisoformat(d["resets_at"]))


def _fetch(token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        _API_URL,
        headers={"Authorization": f"Bearer {token}", "Anthropic-beta": "oauth-2025-04-20"},
    )
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as r:
        data: dict[str, Any] = json.load(r)
        return data


def quota() -> Quota | None:
    if not (token := _token()):
        return None
    try:
        data = _fetch(token)
    except (OSError, json.JSONDecodeError):
        return None
    return Quota(five_hour=_bucket(data["five_hour"]), seven_day=_bucket(data["seven_day"]))


def cached(fetch: Callable[[], Quota | None], ttl: float = 60.0) -> Callable[[], Quota | None]:
    assert ttl > 0, "ttl must be positive"

    @lru_cache(maxsize=1)
    def by_bucket(_bucket: int) -> Quota | None:
        return fetch()

    return lambda: by_bucket(int(time.time() // ttl))
