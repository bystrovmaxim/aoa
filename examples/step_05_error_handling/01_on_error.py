"""
@on_error: catch an aspect exception and return a Result.

Tutorial: ../../docs/index_draft.md  ·  topic: Explicit error handling

Run:
    uv run python examples/step_05_error_handling/01_on_error.py
"""
import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class RootDomain(BaseDomain):
    name = "root"
    description = "Root domain"


class LoginParams(BaseParams):
    username: str = Field(description="Username")


class LoginResult(BaseResult):
    username: str = Field(description="Username")
    status: str = Field(description="Status")


@meta(description="Login", domain=RootDomain)
@check_roles(GuestRole)
class LoginAction(BaseAction[LoginParams, LoginResult]):

    @summary_aspect("Validate credentials")
    async def login_summary(self, params, state, box, connections):
        if params.username == "bad":
            raise ValueError("invalid credentials")
        return LoginResult(username=params.username, status="ok")

    @on_error(ValueError, description="Invalid credentials")
    async def validation_error_on_error(self, params, state, box, connections, error):
        await box.info(Channel.business, "on_error: {%var.msg}", msg=str(error))
        return LoginResult(username=params.username, status="login_failed")


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()])
    )
    print("Sample 05 on error\n")
    result = await machine.run(
        Context(),
        LoginAction(),
        params=LoginParams(username="bad"),
    )
    print("\n" + f"Result: username={result.username}, status={result.status}")


asyncio.run(main())
