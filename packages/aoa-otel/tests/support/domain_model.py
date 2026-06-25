# packages/aoa-otel/tests/support/domain_model.py
"""
Self-contained test-support domain model for aoa-otel tests.

Trimmed copy of the shared ActionMachine test scenario, reduced to only what the
otel tests exercise:

- ``PingAction`` — minimal runnable Action: no parameters, no dependencies or
  connections, a single summary aspect returning a fixed "pong" result.
  GuestRole. Belongs to ``SystemDomain``. Used by ``test_otel_emit_log.py``
  (class identity + ``PingAction.Params()`` to build a ``GlobalStartEvent``) and
  run end-to-end through ``ActionProductMachine`` by
  ``test_otel_integration_machine.py``.
- ``TestDomain`` — generic ``@meta(domain=...)`` marker used by the
  integration test's local actions.
- ``SystemDomain`` — ``PingAction``'s domain (its only scenario-internal
  dependency).

Everything is imported from the installed ``aoa.action_machine.*`` package and
copied faithfully from the original scenario sources
(``tests/action_machine/scenarios/domain_model/{ping_action,domains}.py``).
Names are preserved so only the import lines in the otel tests change.
"""

from pydantic import Field

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox


class SystemDomain(BaseDomain):
    """System domain — used for infrastructure actions (ping, health check)."""

    name = "system"
    description = "System domain for infrastructure operations"


class TestDomain(BaseDomain):
    """Generic domain for tests where the scenario does not care which domain is used."""

    name = "test"
    description = "Shared test domain for @meta"


@meta(description="Service health check", domain=SystemDomain)
@check_roles(GuestRole)
class PingAction(BaseAction["PingAction.Params", "PingAction.Result"]):
    """
    Minimal Action without parameters or dependencies.

    Summary-only aspect returning a fixed "pong" result. GuestRole.
    """

    class Params(BaseParams):
        """PingAction parameters — empty; no input required."""

        pass

    class Result(BaseResult):
        """PingAction result — pong message."""

        message: str = Field(description="Service response message")

    @summary_aspect("Build pong response")
    async def pong_summary(
        self,
        params: "PingAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "PingAction.Result":
        """Return a fixed Result with message 'pong'."""
        return PingAction.Result(message="pong")
