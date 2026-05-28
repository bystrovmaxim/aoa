# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/plugin/__init__.py
"""
OcelPlugin — builds ``OcelEvent`` from ``OcelFrame`` rows on ``GlobalFinishEvent``.

See ``packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/README.md`` — **Export policy (v1)**.
"""

from aoa.action_machine.plugin.ocel.plugin.ocel_plugin import OCEL_FRAMES_KEY, OcelPlugin

__all__ = ["OCEL_FRAMES_KEY", "OcelPlugin"]
