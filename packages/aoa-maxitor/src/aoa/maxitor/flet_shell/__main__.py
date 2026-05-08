# packages/aoa-maxitor/src/aoa/maxitor/flet_shell/__main__.py
"""CLI entry for ``python -m aoa.maxitor.flet_shell`` and the ``maxitor-flet`` script."""

from __future__ import annotations


def run() -> None:
    """Start the Flet desktop shell (requires ``aoa-maxitor[flet]``)."""
    import flet as ft
    from aoa.maxitor.flet_shell.app import main
    ft.run(main)


if __name__ == "__main__":
    run()
