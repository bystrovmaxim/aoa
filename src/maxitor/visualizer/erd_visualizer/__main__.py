# src/maxitor/visualizer/erd_visualizer/__main__.py
"""
Write :file:`erd.html` for the **store** bounded context using the interchange graph.

Loads sample registration (:func:`maxitor.samples.interchange_demo_coordinator.import_sample_registration_modules`),
builds coordinator via :func:`maxitor.samples.interchange_demo_coordinator.build_registered_interchange_coordinator`
(same DAG-or-debug logic as :mod:`maxitor.visualizer.graph_visualizer` demos),
projects entities for :class:`~maxitor.samples.store.domain.StoreDomain`,
and emits X6 HTML.
"""

from __future__ import annotations

from pathlib import Path


def _ensure_src_on_path() -> None:
    """When this file is run as a script, ``src/`` is not on ``sys.path``; add it once."""
    import sys

    src_root = Path(__file__).resolve().parents[3]
    s = str(src_root)
    if s not in sys.path:
        sys.path.insert(0, s)


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
    from maxitor.samples.interchange_demo_coordinator import (
        build_registered_interchange_coordinator,
        import_sample_registration_modules,
    )
    from maxitor.samples.store.domain import StoreDomain

    import_sample_registration_modules()
    coordinator = build_registered_interchange_coordinator()
    path = write_from_coord(
        coordinator,
        StoreDomain,
        output_path=default_out,
        title="ERD · store (interchange)",
    )
    print(f"Written {path.resolve()}")


if __name__ == "__main__":
    main()
