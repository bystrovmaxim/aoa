"""Probe 2: a summary returning a dict is handed back as the operation's answer."""
import asyncio

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, ParamsStub, ResultStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ProbeDomain(BaseDomain):
    name = "probe"
    description = "Baseline probe domain"


@meta(description="Summary returns a dict instead of its Result", domain=ProbeDomain)
@check_roles(GuestRole)
class JunkAction(BaseAction[ParamsStub, ResultStub]):

    @summary_aspect("Return a dict, not a Result")
    async def junk_summary(self, params, state, box, connections):
        return {"not": "a result"}


async def main() -> None:
    answer = await ActionProductMachine().run(Context(), JunkAction(), ParamsStub())
    print("answer type :", type(answer).__name__)
    print("answer value:", answer)
    print("is ResultStub:", isinstance(answer, ResultStub))


asyncio.run(main())
