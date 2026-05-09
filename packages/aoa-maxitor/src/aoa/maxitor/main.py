# packages/aoa-maxitor/src/aoa/maxitor/main.py
"""CLI entry for ``python -m aoa.maxitor.main`` and the ``maxitor-flet`` script."""

from __future__ import annotations

import asyncio

import flet as ft


async def build_sidebar_data() -> object:
    """Load coordinator graph → NetworkX → ``GetLeftMenuSidebarDataAction`` result (``NodeEntity`` lists)."""
    from aoa.action_machine.context.context import Context
    from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
    from aoa.maxitor.model.app_view.actions.get_left_menu_sidebar_data_action import GetLeftMenuSidebarDataAction
    from aoa.maxitor.model.app_view.actions.load_graph_action import LoadGraphAction

    machine = ActionProductMachine()

    from aoa.maxitor.samples.interchange_demo_coordinator import (
        build_registered_interchange_coordinator,
        import_sample_registration_modules,
    )

    import_sample_registration_modules()
    graph = build_registered_interchange_coordinator()
    nx_result = await machine.run(
        Context(),
        LoadGraphAction(),
        LoadGraphAction.Params(graph=graph),
    )
    return await machine.run(
        Context(),
        GetLeftMenuSidebarDataAction(),
        GetLeftMenuSidebarDataAction.Params(nx_graph=nx_result.nx_graph),
    )


def run() -> None:
    """Start the Flet desktop shell (requires ``aoa-maxitor[flet]``)."""
    from aoa.maxitor.app import main

    sidebar_data = asyncio.run(build_sidebar_data())

    async def app(page: ft.Page) -> None:
        await main(page, sidebar_data)

    ft.run(app)


if __name__ == "__main__":
    run()
