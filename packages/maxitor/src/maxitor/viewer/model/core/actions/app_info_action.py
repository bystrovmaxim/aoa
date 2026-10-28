# packages/maxitor/src/maxitor/viewer/model/core/actions/app_info_action.py
"""
AppInfoAction — which Maxitor is running: its version and the client build it serves.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The left panel shows the running version (spec 028, FR-101), and a tab compares its
own build with the one the server serves (FR-090). Both come from here: the version
of the installed ``maxitor`` package, never written by hand, and the build id the
client's build left in ``build.json``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/meta/app-info ──► AppInfoAction
                                  ├─ importlib.metadata.version("maxitor")
                                  └─ connections["StaticBundle"].build()
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import cast

from maxitor.viewer.model.core.core_domain import CoreDomain
from maxitor.viewer.model.core.resources.static_bundle_resource import (
    STATIC_BUNDLE_CONNECTION_KEY,
    StaticBundleResource,
)
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, BaseState, ParamsStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox


class AppInfoResult(BaseResult):
    """The running Maxitor: package version and client build."""

    version: str = Field(description="Version of the installed maxitor package.")
    build: str = Field(description="Id of the client build Maxitor serves; empty without a built client.")


@meta(description="Report the running Maxitor version and client build", domain=CoreDomain)
@check_roles(GuestRole)
@connection(StaticBundleResource, key=STATIC_BUNDLE_CONNECTION_KEY, description="The installed client bundle")
class AppInfoAction(BaseAction[ParamsStub, AppInfoResult]):
    """
    AI-CORE-BEGIN
    ROLE: Answer which Maxitor is running — the package version and the client build it serves.
    CONTRACT: ``version`` is the installed ``maxitor`` version (``"0+unknown"`` when not installed);
    ``build`` is the static bundle's build id or ``""``.
    INVARIANTS: Reads only.
    AI-CORE-END
    """

    @summary_aspect("Read the package version and the bundle's build id")
    async def app_info_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> AppInfoResult:
        """Return the installed version and the served build."""
        try:
            installed = version("maxitor")
        except PackageNotFoundError:
            installed = "0+unknown"
        bundle = cast(StaticBundleResource, connections[STATIC_BUNDLE_CONNECTION_KEY])
        return AppInfoResult(version=installed, build=bundle.build())
