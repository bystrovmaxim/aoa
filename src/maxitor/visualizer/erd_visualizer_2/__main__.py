# src/maxitor/visualizer/erd_visualizer_2/__main__.py
# mypy: ignore-errors
# pylint: disable=import-outside-toplevel
"""
CLI for standalone ERD HTML from the live sample coordinator graph.

Usage
-----
    python -m maxitor.visualizer.erd_visualizer_2
    python -m maxitor.visualizer.erd_visualizer_2 --domain all
    python -m maxitor.visualizer.erd_visualizer_2 -o /tmp/my_erd.html
"""

from __future__ import annotations

from pathlib import Path


def _ensure_src_on_path() -> None:
    """When this file is run as a script, add the local folder and src root to sys.path."""
    import sys

    package_dir = Path(__file__).resolve().parent
    candidates = (
        package_dir,
        package_dir.parents[2] if len(package_dir.parents) > 2 else None,
    )
    for candidate in candidates:
        if candidate is None:
            continue
        s = str(candidate)
        if s not in sys.path:
            sys.path.insert(0, s)


def _load_pkg():
    """Import package exports; supports package and direct directory execution."""
    if __package__:
        from .erd_html import DEFAULT_ERD_HTML_PATH, write_erd_html_from_coordinator

        return DEFAULT_ERD_HTML_PATH, write_erd_html_from_coordinator

    _ensure_src_on_path()
    try:
        from erd_html import DEFAULT_ERD_HTML_PATH, write_erd_html_from_coordinator
    except ImportError:
        from maxitor.visualizer.erd_visualizer_2.erd_html import (
            DEFAULT_ERD_HTML_PATH,
            write_erd_html_from_coordinator,
        )

    return DEFAULT_ERD_HTML_PATH, write_erd_html_from_coordinator


def main() -> None:
    import argparse

    default_out, write_from_coord = _load_pkg()

    ap = argparse.ArgumentParser(
        description=(
            "Write standalone ERD HTML with X6, Graphviz SVG, "
            "Cytoscape, Mermaid, and D2 renderers."
        )
    )
    ap.add_argument(
        "--domain",
        choices=("all", "store"),
        default="store",
        help=(
            'Domain selection from the live sample coordinator graph. '
            '"all" enables the domain picker in the UI.'
        ),
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=f"Output HTML path (default: {default_out}).",
    )
    args = ap.parse_args()
    out = args.output if args.output is not None else Path(default_out)

    from maxitor.samples.interchange_demo_coordinator import (
        build_registered_interchange_coordinator,
        import_sample_registration_modules,
    )
    from maxitor.samples.store.domain import StoreDomain

    import_sample_registration_modules()
    coordinator = build_registered_interchange_coordinator()

    domain_cls = None if args.domain == "all" else StoreDomain
    title = (
        "ERD · samples (interchange graph)"
        if args.domain == "all"
        else "ERD · store (interchange graph)"
    )

    path = write_from_coord(
        coordinator,
        domain_cls,
        output_path=out,
        title=title,
    )
    print(f"Written: {path.resolve()}")


if __name__ == "__main__":
    main()
