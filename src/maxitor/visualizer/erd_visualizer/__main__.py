# src/maxitor/visualizer/erd_visualizer/__main__.py
"""Generate :file:`erd.html` under ``archive/logs`` using the built-in demo diagram."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def _ensure_src_on_path() -> None:
    """When this file is run as a script, ``src/`` is not on ``sys.path``; add it once."""
    import sys

    src_root = Path(__file__).resolve().parents[3]
    s = str(src_root)
    if s not in sys.path:
        sys.path.insert(0, s)


def _import_entrypoints() -> tuple[
    Callable[[], Any],
    Callable[[Any], dict[str, list[dict[str, Any]]]],
    Path,
    Callable[..., Path],
]:
    if __package__:
        from .erd_graph_data import build_demo_erd_payload, erd_payload_to_g6_records
        from .erd_html import DEFAULT_ERD_HTML_PATH, write_erd_html
        return (
            build_demo_erd_payload,
            erd_payload_to_g6_records,
            DEFAULT_ERD_HTML_PATH,
            write_erd_html,
        )
    _ensure_src_on_path()
    from maxitor.visualizer.erd_visualizer.erd_graph_data import (
        build_demo_erd_payload,
        erd_payload_to_g6_records,
    )
    from maxitor.visualizer.erd_visualizer.erd_html import (
        DEFAULT_ERD_HTML_PATH,
        write_erd_html,
    )
    return (
        build_demo_erd_payload,
        erd_payload_to_g6_records,
        DEFAULT_ERD_HTML_PATH,
        write_erd_html,
    )


def main() -> None:
    build_demo, to_records, default_out, write_html = _import_entrypoints()
    demo = build_demo()
    records = to_records(demo)
    path = write_html(records, output_path=default_out, title="ERD · demo")
    print(f"Written {path.resolve()}")


if __name__ == "__main__":
    main()
