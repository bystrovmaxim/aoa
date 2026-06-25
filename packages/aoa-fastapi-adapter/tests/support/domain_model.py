# packages/aoa-fastapi-adapter/tests/support/domain_model.py
"""
Domain model fixtures for the FastAPI adapter test suite.

════════════════════════════════════════════════════════════════════════════════
PURPOSE
════════════════════════════════════════════════════════════════════════════════

Self-contained copy of the scenario domain model the FastAPI adapter tests rely
on. Bundles the business domains, the minimal ``SampleEntity`` used for
``BaseEntity.schema()`` wire projections, and the two smoke-test actions:

- ``PingAction``  — no-parameter action returning a fixed ``"pong"`` message
  (drives the no-param / POST-empty-body endpoint strategies). GuestRole,
  SystemDomain.
- ``SimpleAction`` — single required ``name`` parameter, returns a greeting
  (drives the GET/DELETE query-parameter strategy). GuestRole, OrdersDomain.

All imports resolve against the installed ``aoa.action_machine.*`` package; this
module has no dependency on the repository-level ``tests`` package.
"""

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

# ════════════════════════════════════════════════════════════════════════════
# DOMAINS
# ════════════════════════════════════════════════════════════════════════════


class OrdersDomain(BaseDomain):
    """Orders domain — used for actions related to order processing."""

    name = "orders"
    description = "Domain for processing customer orders"


class SystemDomain(BaseDomain):
    """System domain — used for infrastructure actions (ping, health check)."""

    name = "system"
    description = "System domain for infrastructure operations"


class TestDomain(BaseDomain):
    """Generic domain for tests where the scenario does not care which domain is used."""

    name = "test"
    description = "Shared test domain for @meta"


# ════════════════════════════════════════════════════════════════════════════
# ENTITIES
# ════════════════════════════════════════════════════════════════════════════


@meta(description="Simple test entity", domain=TestDomain)
@entity(description="Simple test entity", domain=TestDomain)
class SampleEntity(BaseEntity):
    """Minimal entity for basic tests. No relations or lifecycle."""

    id: str = Field(description="Identifier")
    name: str = Field(description="Name")
    value: int = Field(description="Value", ge=0)


# ════════════════════════════════════════════════════════════════════════════
# ACTIONS
# ════════════════════════════════════════════════════════════════════════════


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


@meta(description="Simple Action with a single aspect", domain=OrdersDomain)
@check_roles(GuestRole)
class SimpleAction(BaseAction["SimpleAction.Params", "SimpleAction.Result"]):
    """
    Action with one regular aspect and one checker.

    Pipeline:
    1. validate_name (regular) — writes validated_name to state.
       Checker: result_string("validated_name", required=True, min_length=1).
    2. build_greeting (summary) — greeting from state.
    """

    class Params(BaseParams):
        """SimpleAction parameters — name to validate."""

        name: str = Field(
            description="Name to process",
            min_length=1,
            examples=["Alice"],
        )

    class Result(BaseResult):
        """SimpleAction result — greeting message."""

        greeting: str = Field(description="Greeting message")

    @regular_aspect("Validate name")
    @result_string("validated_name", required=True, min_length=1)
    async def validate_name_aspect(
        self,
        params: "SimpleAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict:
        """
        Validate and normalize the name from params.

        Writes validated_name — trimmed name. result_string checks
        non-empty string with length >= 1.

        Returns:
            dict with key validated_name.
        """
        return {"validated_name": params.name.strip()}

    @summary_aspect("Build greeting")
    async def build_greeting_summary(
        self,
        params: "SimpleAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "SimpleAction.Result":
        """
        Build greeting from validated_name in state.

        Returns:
            SimpleAction.Result with greeting = "Hello, {name}!".
        """
        name = state["validated_name"]
        return SimpleAction.Result(greeting=f"Hello, {name}!")
