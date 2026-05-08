# packages/aoa-maxitor/src/aoa/maxitor/visualizer/graph_visualizer/__main__.py
"""CLI demo: interchange G6 HTML (same coordinator build as ``erd_visualizer`` demos)."""

from __future__ import annotations

from aoa.maxitor.visualizer.graph_visualizer.visualizer import write_demo_interchange_axes_graph_html


def main() -> None:
    written = write_demo_interchange_axes_graph_html()
    print(f"Interchange axes graph HTML written to {written.resolve()}")


if __name__ == "__main__":
    main()
