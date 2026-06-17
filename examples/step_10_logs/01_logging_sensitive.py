"""
Scenario: advanced logging.

Demonstrates:
  1. {%var.name} — pass values into the log template
  2. {iif(...)} — conditional text; red() / green() color branches
  3. box.warning — level-based line color (yellow)
  4. box.critical — level-based line color (red)
  5. PrivateAttr + @sensitive property — {%params.api_token} prints a mask

Tutorial: ../../docs/index_draft.md  ·  topic: Logs as business events

Run:
    uv run python examples/step_10_logs/01_logging_sensitive.py
"""
import asyncio

from pydantic import Field, PrivateAttr

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger, sensitive
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class RootDomain(BaseDomain):
    name = "root"
    description = "Root domain"


class LoginParams(BaseParams):
    username: str = Field(description="Username")
    amount: float = Field(description="Transaction amount")

    # PrivateAttr is not in the Params schema; {%params._api_token} in a log template is forbidden.
    _api_token: str = PrivateAttr(default="")

    # Expose the secret only through a property; @sensitive masks it in logs (e.g. tok*****).
    # max_chars, char, max_percent — mask settings
    @property
    @sensitive(True, max_chars=3, char="*", max_percent=50)
    def api_token(self) -> str:
        return self._api_token

    def __init__(self, /, username: str, amount: float, api_token: str = "") -> None:
        super().__init__(username=username, amount=amount)
        self.__pydantic_private__["_api_token"] = api_token


class LoginResult(BaseResult):
    session_id: str = Field(description="Session ID")


@meta(description="Login", domain=RootDomain)
@check_roles(NoneRole)
class LoginAction(BaseAction[LoginParams, LoginResult]):

    @summary_aspect("Login")
    async def login_summary(self, params, state, box, connections):
        # 1. Variable substitution
        await box.info(
            Channel.business,
            "Login: user={%var.username}, amount={%var.amount}",
            username=params.username,
            amount=params.amount,
        )

        # 2. Conditional iif with colored branches in the console
        await box.info(
            Channel.business,
            "Info: {iif({%var.amount} > 1000; red('large transaction'); green('normal transaction'))}",
            amount=params.amount,
        )

        # 3. warning level — yellow by default
        await box.warning(
            Channel.business,
            "Warning: amount {%var.amount|red} requires review",
            amount=params.amount,
        )

        # 4. critical level — red by default
        await box.critical(
            Channel.business,
            "Critical: amount {%var.amount} requires review",
            amount=params.amount,
        )

        # 5. {%params.api_token} — masked property output
        await box.info(
            Channel.business,
            "Token: {%params.api_token}",
        )

        return LoginResult(session_id=f"sess-{params.username}-001")


async def main() -> None:
    print("Sample 03 logging sensitive\n")
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]))

    await machine.run(
        Context(),
        LoginAction(),
        params=LoginParams(username="alice", amount=500.0, api_token="tok-SUPER-SECRET-XYZ"),
    )

asyncio.run(main())
