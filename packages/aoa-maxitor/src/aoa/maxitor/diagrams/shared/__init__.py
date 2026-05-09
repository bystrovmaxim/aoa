# packages/aoa-maxitor/src/aoa/maxitor/diagrams/shared/__init__.py

"""
Shared interchange viewer assets (injected CSS for graph + ERD HTML shells).
"""

from __future__ import annotations

from aoa.maxitor.diagrams.shared.chrome import read_detail_panel_js, read_interchange_chrome_css

__all__ = ["read_detail_panel_js", "read_interchange_chrome_css"]
