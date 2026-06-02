import json
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cctop.core.quota import Bucket, Quota, cached, quota

_FIVE_HOUR_TS = "2026-02-06T22:00:00+00:00"
_SEVEN_DAY_TS = "2026-02-12T20:00:00+00:00"

_SAMPLE_RESPONSE: dict[str, Any] = {
    "five_hour": {"utilization": 35.0, "resets_at": _FIVE_HOUR_TS},
    "seven_day": {"utilization": 14.0, "resets_at": _SEVEN_DAY_TS},
}


def _creds(token: str = "secret-token") -> str:
    return json.dumps({"claudeAiOauth": {"accessToken": token}})


def _urlopen_mock(payload: dict[str, Any]) -> MagicMock:
    response = MagicMock()
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    response.read = MagicMock(return_value=json.dumps(payload).encode())
    return response


@patch.dict("os.environ", {"CLAUDE_CODE_OAUTH_TOKEN": "env-token"})
@patch("urllib.request.urlopen")
def test_quota_uses_env_token(urlopen: MagicMock) -> None:
    urlopen.return_value = _urlopen_mock(_SAMPLE_RESPONSE)
    q = quota()
    assert isinstance(q, Quota)
    assert q.five_hour == Bucket(35.0, datetime.fromisoformat(_FIVE_HOUR_TS))
    assert q.seven_day == Bucket(14.0, datetime.fromisoformat(_SEVEN_DAY_TS))
    req = urlopen.call_args.args[0]
    assert req.headers["Authorization"] == "Bearer env-token"
    assert req.headers["Anthropic-beta"] == "oauth-2025-04-20"


@patch.dict("os.environ", {"CLAUDE_CODE_OAUTH_TOKEN": "env-token"})
@patch("urllib.request.urlopen")
def test_quota_handles_null_resets_at(urlopen: MagicMock) -> None:
    payload = {
        "five_hour": {"utilization": 0.0, "resets_at": None},
        "seven_day": {"utilization": 14.0, "resets_at": _SEVEN_DAY_TS},
    }
    urlopen.return_value = _urlopen_mock(payload)
    q = quota()
    assert q is not None
    assert q.five_hour == Bucket(0.0, None)
    assert q.seven_day == Bucket(14.0, datetime.fromisoformat(_SEVEN_DAY_TS))


@patch.dict("os.environ", {}, clear=True)
@patch("platform.system", return_value="Darwin")
@patch("subprocess.run")
@patch("urllib.request.urlopen")
def test_quota_uses_keychain_on_macos(urlopen: MagicMock, run: MagicMock, _system: MagicMock) -> None:
    run.return_value = MagicMock(returncode=0, stdout=_creds("kc-token"))
    urlopen.return_value = _urlopen_mock(_SAMPLE_RESPONSE)
    assert isinstance(quota(), Quota)
    assert urlopen.call_args.args[0].headers["Authorization"] == "Bearer kc-token"


@patch.dict("os.environ", {}, clear=True)
@patch("platform.system", return_value="Darwin")
@patch("subprocess.run")
def test_quota_returns_none_when_keychain_missing(run: MagicMock, _system: MagicMock) -> None:
    run.return_value = MagicMock(returncode=44, stdout="")
    assert quota() is None


@patch.dict("os.environ", {}, clear=True)
@patch("platform.system", return_value="Linux")
@patch("urllib.request.urlopen")
def test_quota_uses_credentials_file(urlopen: MagicMock, _system: MagicMock, tmp_path: Path) -> None:
    creds = tmp_path / ".credentials.json"
    creds.write_text(_creds("file-token"))
    urlopen.return_value = _urlopen_mock(_SAMPLE_RESPONSE)
    with patch("cctop.core.quota._CREDS_PATH", creds):
        assert isinstance(quota(), Quota)
    assert urlopen.call_args.args[0].headers["Authorization"] == "Bearer file-token"


@patch.dict("os.environ", {}, clear=True)
@patch("platform.system", return_value="Linux")
def test_quota_returns_none_when_creds_file_missing(_system: MagicMock, tmp_path: Path) -> None:
    with patch("cctop.core.quota._CREDS_PATH", tmp_path / "does-not-exist.json"):
        assert quota() is None


@patch.dict("os.environ", {"CLAUDE_CODE_OAUTH_TOKEN": "t"})
@patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline"))
def test_quota_returns_none_on_network_error(_urlopen: MagicMock) -> None:
    assert quota() is None


@patch.dict("os.environ", {"CLAUDE_CODE_OAUTH_TOKEN": "t"})
@patch("urllib.request.urlopen")
def test_quota_returns_none_on_invalid_json(urlopen: MagicMock) -> None:
    response = MagicMock()
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    response.read = MagicMock(return_value=b"<html>not json</html>")
    urlopen.return_value = response
    assert quota() is None


def test_cached_calls_fetch_once_within_ttl() -> None:
    q = Quota(Bucket(10.0, datetime.fromisoformat(_FIVE_HOUR_TS)), Bucket(5.0, datetime.fromisoformat(_SEVEN_DAY_TS)))
    calls: list[int] = []

    def fetch() -> Quota | None:
        calls.append(1)
        return q

    loader = cached(fetch, ttl=60.0)
    assert loader() is q
    assert loader() is q
    assert loader() is q
    assert len(calls) == 1


def test_cached_refetches_after_ttl_expires() -> None:
    results = iter([
        Quota(Bucket(10.0, datetime.fromisoformat(_FIVE_HOUR_TS)), Bucket(5.0, datetime.fromisoformat(_SEVEN_DAY_TS))),
        Quota(Bucket(20.0, datetime.fromisoformat(_FIVE_HOUR_TS)), Bucket(7.0, datetime.fromisoformat(_SEVEN_DAY_TS))),
    ])
    loader = cached(lambda: next(results), ttl=60.0)
    with patch("cctop.core.quota.time.time", side_effect=[0.0, 30.0, 90.0]):
        first = loader()
        within_ttl = loader()
        after_rollover = loader()
    assert first is within_ttl
    assert first is not after_rollover
    assert first is not None and after_rollover is not None
    assert first.five_hour.utilization == 10.0
    assert after_rollover.five_hour.utilization == 20.0


def test_cached_rejects_non_positive_ttl() -> None:
    with pytest.raises(AssertionError):
        cached(lambda: None, ttl=0.0)
