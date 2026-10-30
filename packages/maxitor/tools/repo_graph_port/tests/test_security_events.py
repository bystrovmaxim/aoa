# packages/maxitor/tools/repo_graph_port/tests/test_security_events.py
"""A wrong key and a wrong webhook signature are security warnings; a block is critical; none names a key, a hash or a signature."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from maxitor.repo_graph_port.actions.report_security_event_action import (
    ReportSecurityEventAction,
    ReportSecurityEventParams,
    SecurityEventKind,
)
from maxitor.repo_graph_port.server import create_app

from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.logging import Channel
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.level import Level
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from tests.test_github import send, world  # noqa: F401 — ``world`` is the fixture the webhook test uses
from tests.test_keys import config_file, issue

BASE = "/api/v1/history"
#: How the console logger colours a warning and a critical line.
WARNING_COLOUR, CRITICAL_COLOUR = "\033[38;2;255;204;0m", "\033[38;2;255;34;34m"


class Recorder(BaseLogger):
    """Every line written, with its level and channels."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[tuple[Level, Channel, str]] = []

    async def write(self, scope: Any, message: str, var: dict[str, Any], ctx: Any, state: Any, params: Any, indent: int) -> None:
        """Keep the line."""
        _ = (scope, ctx, state, params, indent)
        self.lines.append((var["level"].mask, var["channels"].mask, message))


def lines_saying(output: str, text: str) -> list[str]:
    """The lines of ``output`` that contain ``text``."""
    return [line for line in output.splitlines() if text in line]


@pytest.mark.parametrize(
    ("kind", "level", "said"),
    [
        ("wrong_key", Level.warning, "Wrong key for history orders from 10.0.0.9"),
        ("bad_signature", Level.warning, "Webhook with a wrong signature from 10.0.0.9"),
        ("blocked", Level.critical, "Blocked 10.0.0.9 for a minute: 11 wrong keys"),
    ],
)
def test_each_event_is_written_on_the_security_channel_at_its_level(kind: SecurityEventKind, level: Level, said: str) -> None:
    """The action writes one line on ``security``, at ``warning`` or ``critical``."""
    recorder = Recorder()
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator(), log_coordinator=LogCoordinator(loggers=[recorder]))
    params = ReportSecurityEventParams(kind=kind, client="10.0.0.9", history="orders", count=11)
    asyncio.run(machine.run(Context(), ReportSecurityEventAction(), params))
    events = [line for line in recorder.lines if said in line[2]]
    assert len(events) == 1
    assert events[0][0] == level and Channel.security in events[0][1]


def test_each_wrong_key_is_a_warning_and_the_block_is_critical(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Eleven wrong keys from one client: eleven warnings naming ``orders`` and the client, then one critical block naming the count."""
    path = config_file(tmp_path)
    key = issue(path, capsys, "orders", "anna")
    client = TestClient(create_app(path, tmp_path / "cache"))
    wrong = "not-" + key
    for _ in range(11):
        client.get(f"{BASE}/orders", headers={"X-Maxitor-History-Key": wrong})
    out = capsys.readouterr()
    said = out.out + out.err
    warnings = lines_saying(said, "Wrong key for history orders from testclient")
    blocks = lines_saying(said, "Blocked testclient for a minute: 11 wrong keys")
    assert len(warnings) == 11 and all(WARNING_COLOUR in line for line in warnings)
    assert len(blocks) == 1 and CRITICAL_COLOUR in blocks[0]
    for secret in (wrong, key, hashlib.sha256(wrong.encode()).hexdigest(), hashlib.sha256(key.encode()).hexdigest()):
        assert secret not in said


def test_a_right_key_and_no_key_report_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A valid key and a request with no key leave no security line."""
    path = config_file(tmp_path)
    key = issue(path, capsys, "orders", "anna")
    client = TestClient(create_app(path, tmp_path / "cache"))
    client.get(f"{BASE}/orders", headers={"X-Maxitor-History-Key": key})
    client.get(f"{BASE}/orders")
    out = capsys.readouterr()
    said = out.out + out.err
    assert lines_saying(said, "Wrong key") == [] and lines_saying(said, "Blocked") == []


def test_a_wrong_webhook_signature_is_a_warning(world: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:  # noqa: F811
    """A webhook signed with another secret: one warning naming the client, never the signature."""
    capsys.readouterr()
    answer = send(world, {"ref": "refs/heads/main", "before": "0" * 40, "after": "1" * 40, "repository": {"full_name": "owner/service"}}, secret="wrong")
    assert answer.status_code == 401
    out = capsys.readouterr()
    lines = lines_saying(out.out + out.err, "Webhook with a wrong signature from testclient")
    assert len(lines) == 1 and WARNING_COLOUR in lines[0]
    assert "sha256=" not in out.out + out.err
