# packages/aoa-action-machine/src/aoa/action_machine/resources/connections.py
"""
Connections — the public name of the mapping the pipeline hands to a declaration.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An aspect declaration receives the runtime ``connections`` mapping, and until this
module that type had no name of its own: every application and every example restated
``dict[str, BaseResource]`` in its parameter list. ``Connections`` is that type under
one public name.

The alias is an ordinary assignment, not PEP 695 syntax. ``type Connections = ...``
would create a ``typing.TypeAliasType``, which has neither ``__origin__`` nor
``__args__``; the assembly check reads those two attributes
(``intents/aspects/aspect_signature.py``, ``intents/access_decide/access_decide_signature.py``),
so that form is refused where this one is accepted.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.resources import Connections

    async def assemble_summary(
        self, params: CreateOrderParams, state: BaseState, box: ToolsBox,
        connections: Connections,
    ) -> CreateOrderResult: ...

The long spelling ``dict[str, BaseResource]`` stays valid: the two names are the same
type.
"""

from aoa.action_machine.resources.base_resource import BaseResource

Connections = dict[str, BaseResource]
"""The mapping the pipeline hands to a declaration: connection key to ``BaseResource``."""
