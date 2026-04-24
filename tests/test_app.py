from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cctop.app import app
from cctop.core.session import Session
from cctop.views.protocols import Action
from tests.conftest import make_ref

runner = CliRunner()


class _AppMocks:
    def __init__(self, console: MagicMock, picker_cls: MagicMock, monitor_cls: MagicMock) -> None:
        self.console = console
        self.picker_cls = picker_cls
        self.monitor_cls = monitor_cls


@pytest.fixture()
def app_mocks() -> Generator[_AppMocks]:
    with (
        patch("cctop.app.Console") as console,
        patch("cctop.app.SessionPicker") as picker_cls,
        patch("cctop.app.SessionMonitor") as monitor_cls,
    ):
        yield _AppMocks(console, picker_cls, monitor_cls)


def _mock_picker(action: Action, ref: Session.Ref | None = None) -> MagicMock:
    picker = MagicMock()
    picker.display_on.return_value = (action, ref)
    return picker


def _mock_monitor(action: Action) -> MagicMock:
    monitor = MagicMock()
    monitor.display_on.return_value = (action, MagicMock())
    return monitor


def test_main_quit_from_picker(app_mocks: _AppMocks) -> None:
    app_mocks.picker_cls.return_value = _mock_picker(Action.QUIT)
    result = runner.invoke(app)
    assert result.exit_code == 0


def test_main_quit_from_monitor(app_mocks: _AppMocks, tmp_path: Path) -> None:
    ref = make_ref(tmp_path)
    app_mocks.picker_cls.return_value = _mock_picker(Action.SELECT, ref)
    app_mocks.monitor_cls.return_value = _mock_monitor(Action.QUIT)
    result = runner.invoke(app)
    assert result.exit_code == 0


def test_main_back_from_monitor(app_mocks: _AppMocks, tmp_path: Path) -> None:
    ref = make_ref(tmp_path)
    picker_inst = MagicMock()
    picker_inst.display_on.side_effect = [
        (Action.SELECT, ref),
        (Action.QUIT, None),
    ]
    app_mocks.picker_cls.return_value = picker_inst
    app_mocks.monitor_cls.return_value = _mock_monitor(Action.BACK)
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert picker_inst.display_on.call_count == 2


def test_version_flag_prints_package_version() -> None:
    with patch("cctop.app._package_version", return_value="9.9.9"):
        result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "9.9.9" in result.stdout


def test_main_select_without_ref(app_mocks: _AppMocks) -> None:
    picker_inst = MagicMock()
    picker_inst.display_on.side_effect = [
        (Action.SELECT, None),
        (Action.QUIT, None),
    ]
    app_mocks.picker_cls.return_value = picker_inst
    result = runner.invoke(app)
    assert result.exit_code == 0
    app_mocks.monitor_cls.return_value.display_on.assert_not_called()
