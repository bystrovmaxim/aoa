# src/maxitor/visualizer/erd_visualizer/__main__.py
"""
Write :file:`erd.html` for the **store** bounded context using the production interchange graph.

Loads the same sample registration modules as ``maxitor.samples.node_build``, builds
an interchange :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`
(``create_node_graph_coordinator()`` first; on sample-only DAG cycles falls back to
:class:`~graph.debug_node_graph_coordinator.DebugNodeGraphCoordinator` like the interchange
HTML exporter),
projects entities for :class:`~maxitor.samples.store.domain.StoreDomain`,
and emits X6 HTML.
"""

from __future__ import annotations

import importlib
from pathlib import Path


def _ensure_src_on_path() -> None:
    """When this file is run as a script, ``src/`` is not on ``sys.path``; add it once."""
    import sys

    src_root = Path(__file__).resolve().parents[3]
    s = str(src_root)
    if s not in sys.path:
        sys.path.insert(0, s)


def _import_sample_registration_modules() -> None:
    """Ensure entity/action graph contributions from ``maxitor.samples`` are registered."""
    from maxitor.samples.build import _MODULES

    for name in _MODULES:
        importlib.import_module(name)


def _load_erd_html_exports():
    """Import package exports (supports ``python path/to/__main__.py`` invocation)."""
    if __package__:
        from .erd_html import DEFAULT_ERD_HTML_PATH, write_erd_html_from_coordinator

        return DEFAULT_ERD_HTML_PATH, write_erd_html_from_coordinator
    _ensure_src_on_path()
    from maxitor.visualizer.erd_visualizer.erd_html import (
        DEFAULT_ERD_HTML_PATH,
        write_erd_html_from_coordinator,
    )

    return DEFAULT_ERD_HTML_PATH, write_erd_html_from_coordinator


def main() -> None:
    default_out, write_from_coord = _load_erd_html_exports()
    _import_sample_registration_modules()
    from graph.create_node_graph_coordinator import (
        all_axis_graph_node_inspectors,
        create_node_graph_coordinator,
    )
    from graph.debug_node_graph_coordinator import DebugNodeGraphCoordinator
    from graph.exceptions import InvalidGraphError
    from maxitor.samples.store.domain import StoreDomain

    try:
        coordinator = create_node_graph_coordinator()
    except InvalidGraphError:
        coordinator = DebugNodeGraphCoordinator()
        coordinator.build(all_axis_graph_node_inspectors())
    path = write_from_coord(
        coordinator,
        StoreDomain,
        output_path=default_out,
        title="ERD · store (interchange)",
    )
    print(f"Written {path.resolve()}")


if __name__ == "__main__":
    main()
