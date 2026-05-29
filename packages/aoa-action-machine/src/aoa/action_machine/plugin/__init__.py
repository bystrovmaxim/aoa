# packages/aoa-action-machine/src/aoa/action_machine/plugin/__init__.py
"""Plugin runtime (``plugin.core``) and optional built-in modules (e.g. ``plugin.ocel``).

Import ``Plugin`` from :mod:`aoa.action_machine.plugin.core`, not from this package,
so ``plugin.ocel`` and other subpackages can load without pulling in ``plugin.core``.
"""
