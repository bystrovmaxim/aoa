"""An operation without an access declaration never reaches a running service.

The undeclared action is defined in a separate interpreter on purpose: the graph
inspector walks every ``BaseAction`` subclass in the process, so merely defining
such a class poisons assembly for everything else in the same run. The script
carries its own control — the same action with a declaration — so a broken script
cannot pass for a working invariant.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[5]

_SCRIPT = textwrap.dedent(
    '''
    import asyncio
    import sys

    sys.path.insert(0, "packages/aoa-action-machine")

    from aoa.action_machine.context.context import Context
    from aoa.action_machine.context.user_info import UserInfo
    from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
    from aoa.action_machine.intents.check_roles import check_roles
    from aoa.action_machine.intents.meta.meta_decorator import meta
    from aoa.action_machine.model.base_action import BaseAction
    from aoa.action_machine.model.base_params import BaseParams
    from aoa.action_machine.model.base_result import BaseResult
    from aoa.action_machine.model.base_state import BaseState
    from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
    from aoa.action_machine.runtime.tools_box import ToolsBox
    from tests.support.domain_model.domains import SystemDomain
    from tests.support.domain_model.roles import AdminRole

    DECLARED = __DECLARED__


    @meta(description="declaration probe", domain=SystemDomain)
    class ProbeAction(BaseAction["ProbeAction.Params", "ProbeAction.Result"]):
        class Params(BaseParams):
            pass

        class Result(BaseResult):
            ok: bool = True

        @summary_aspect("S")
        async def run_it_summary(self, params, state, box, connections):
            print("RAN")
            return ProbeAction.Result()


    if DECLARED:
        ProbeAction = check_roles(AdminRole)(ProbeAction)

    try:
        machine = ActionProductMachine(cache_coordinator=None)
    except Exception as exc:
        print(f"RAISED_AT_CONSTRUCTION {type(exc).__name__}: {exc}")
    else:
        print("BUILT")
        caller = Context(user=UserInfo(user_id="u-1", roles=(AdminRole,))) if DECLARED else Context()
        try:
            asyncio.run(machine.run(caller, ProbeAction(), ProbeAction.Params()))
        except Exception as exc:
            print(f"RAISED {type(exc).__name__}: {exc}")
    '''
)


def _run(declared: bool) -> str:
    """Run the probe in a fresh interpreter and return everything it printed."""
    script = _SCRIPT.replace("__DECLARED__", repr(declared))
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture(scope="module")
def undeclared_run() -> str:
    """What the interpreter prints for an operation with no access declaration."""
    return _run(declared=False)


@pytest.fixture(scope="module")
def declared_run() -> str:
    """What the interpreter prints for the same operation, declared."""
    return _run(declared=True)


def test_an_operation_without_a_declaration_fails_assembly(undeclared_run: str) -> None:
    """Assembly refuses the operation, and the operation itself never runs."""
    assert "RAISED_AT_CONSTRUCTION MissingCheckRolesError" in undeclared_run
    assert "has no @check_roles declaration" in undeclared_run
    assert "RAN" not in undeclared_run


def test_the_failure_comes_before_any_call_is_served(undeclared_run: str) -> None:
    """The graph is assembled while the machine is built, so nothing is served first."""
    assert "BUILT" not in undeclared_run
    assert "RAISED_AT_CONSTRUCTION" in undeclared_run


def test_the_same_operation_with_a_declaration_is_served(declared_run: str) -> None:
    """The control: with a declaration the very same action assembles and runs."""
    assert "BUILT" in declared_run
    assert "RAN" in declared_run
    assert "MissingCheckRolesError" not in declared_run
