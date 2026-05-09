# packages/aoa-maxitor/src/aoa/maxitor/flet_shell/app.py
"""
Flet shell — six root domain buckets + custom model tree + WebView workspace.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Sidebar chrome: compact top toolbar (hide / search), fixed footer (avatar + filter +
settings — no promo button); only the interchange tree scrolls.
Every ``node_type`` not in the first five primaries is grouped under **Resources**.
Sections expand to show **diagram rows first**, then coordinator **elements** — no intermediate
``Views`` / ``Elements`` folders.
**Application**: interchange graph row, then nodes in that bucket.
**Domains**: ERD covering all bounded contexts first, then domain / other nodes (per-domain ``ERD`` inline under each domain row when expanded).
Other roots: coordinator nodes only.

Right: ``WebView(expand=True)`` or placeholder. Do not use ``set_javascript_mode()``
on macOS (flet-webview issue #13).

Run: ``python -m aoa.maxitor.flet_shell``.
"""

from __future__ import annotations

import asyncio
import http.server
import importlib
import os
import socketserver
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple, cast

import flet as ft
from flet.controls.control_event import Event
from flet.controls.types import PagePlatform

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.root.app_view.entities.node_entity import NodeEntity
from aoa.maxitor.samples.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)
from aoa.maxitor.visualizer.erd_visualizer import write_erd_html_from_coordinator
from aoa.maxitor.visualizer.graph_visualizer import generate_interchange_g6_html

# ── sidebar: flat explorer-style tree (no stacked cards / pill badges) ───────
_SIDEBAR_WIDTH = 228
_SIDEBAR_COLLAPSED_W = 34
_ELEMENTS_CAP = 100
_LEADING_SLOT_W = 14
# Indent for diagram + element rows directly under an expanded section root (no Views/Elements branch).
_IND_UNDER_ROOT = 20
_IND_UNDER_DOMAIN = _IND_UNDER_ROOT + 16
_AUTO_BROWSER_ENV = "MAXITOR_FLET_AUTO_BROWSER"

_CLR_BG = "#f3f6f7"
# No visible chrome lines in the sidebar chrome (matches reference rail).
_CLR_TEXT = "#24292e"
_CLR_MUTED = "#586069"
# Section-root labels (compact rail): smaller, lighter greys vs body lines.
_CLR_SECTION = "#6a737d"
_CLR_ICON = "#6a737d"
_ICON_TOOLBAR = 14
_ICON_TREE = 12
_ICON_COLLAPSE_STRIP = 14

_FS_BODY = 13.0
_FS_SECTION = 12.0

_http_lock = threading.Lock()
_httpd: socketserver.ThreadingTCPServer | None = None


def _log(tag: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}", flush=True)


def _should_open_browser_too() -> bool:
    v = os.environ.get(_AUTO_BROWSER_ENV, "").strip().lower()
    return v in ("1", "true", "yes")


def _start_preview_httpd(root: Path) -> str:
    global _httpd
    root_s = str(root.resolve())

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=root_s, **kwargs)

        def log_message(self, fmt: str, *args: Any) -> None:
            _log("HTTP", fmt % args)

    with _http_lock:
        if _httpd is not None:
            port = _httpd.server_address[1]
            return f"http://127.0.0.1:{port}/"

        class _PreviewServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        _httpd = _PreviewServer(("127.0.0.1", 0), _Handler)
        port = _httpd.server_address[1]
        threading.Thread(target=_httpd.serve_forever, daemon=True).start()
        _log("HTTP", f"Started on http://127.0.0.1:{port}/")
        return f"http://127.0.0.1:{port}/"


_coord_lock = threading.Lock()
_coord_cache: NodeGraphCoordinator | None = None


class _SidebarNodeView(NamedTuple):
    """Lightweight tree row derived from ``GetLeftMenuSidebarDataAction.Result.level2_nodes``."""

    node_id: str
    label: str
    node_type: str


def _import_domain_type(qualname: str) -> type[BaseDomain]:
    """Resolve a domain class from its interchange ``node_id`` (full module-qualified name)."""
    if "." not in qualname:
        msg = f"Invalid domain type qualname: {qualname!r}"
        raise ValueError(msg)
    mod_name, _, cls_name = qualname.rpartition(".")
    module = importlib.import_module(mod_name)
    t = getattr(module, cls_name)
    if not isinstance(t, type) or not issubclass(t, BaseDomain):
        msg = f"Not a BaseDomain subclass: {qualname!r}"
        raise TypeError(msg)
    return cast(type[BaseDomain], t)


def _interchange_coordinator() -> NodeGraphCoordinator:
    global _coord_cache
    with _coord_lock:
        if _coord_cache is None:
            _log("COORD", "Building coordinator…")
            import_sample_registration_modules()
            _coord_cache = build_registered_interchange_coordinator()
            _log("COORD", "Ready.")
        return _coord_cache


def _export_graph_html(path: Path) -> None:
    _log("EXPORT", f"graph → {path}")
    generate_interchange_g6_html(_interchange_coordinator(), path, title="Interchange graph")
    _log("EXPORT", f"done, {path.stat().st_size} bytes")


def _export_erd_html(path: Path, *, domain_cls: type[BaseDomain] | None = None) -> None:
    _log("EXPORT", f"erd → {path} domain_cls={domain_cls!r}")
    title = "Interchange ERD"
    if domain_cls is not None:
        title = f"ERD — {domain_cls.__name__}"
    write_erd_html_from_coordinator(
        _interchange_coordinator(),
        domain_cls=domain_cls,
        output_path=path,
        title=title,
    )
    _log("EXPORT", f"done, {path.stat().st_size} bytes")


def _ellipsis_only_tooltip(full: str, *, min_chars: int = 26) -> str | None:
    """Tooltip only when the label is likely truncated in the narrow rail (avoids native overlay on short lines)."""
    s = full.strip()
    return s if len(s) >= min_chars else None


def _tree_row(
    *,
    leading: ft.Control | None,
    title: str,
    subtitle: str | None,
    trailing: ft.Control | None,
    on_click: Callable[[Any], Any] | None,
    indent: int = 0,
    dense: bool = False,
    title_size: float = 13.0,
    title_weight: ft.FontWeight = ft.FontWeight.W_400,
    title_color: str = _CLR_TEXT,
    title_tooltip: str | None = None,
    title_max_lines: int = 1,
    radius: float = 4,
) -> ft.Container:
    pad_l = 8 + indent
    v_pad = 2 if dense else 4
    tip = title_tooltip or None
    title_ctl = ft.Text(
        title,
        size=title_size,
        color=title_color,
        weight=title_weight,
        max_lines=title_max_lines,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    if tip is not None:
        title_ctl.tooltip = tip
    row_inner = ft.Row(
        tight=True,
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=_LEADING_SLOT_W,
                alignment=ft.Alignment(-1, 0),
                content=leading,
            ),
            ft.Column(
                tight=True,
                spacing=0,
                expand=True,
                controls=[
                    title_ctl,
                    *([ft.Text(subtitle, size=_FS_SECTION, color=_CLR_MUTED)] if subtitle else []),
                ],
            ),
            trailing if trailing is not None else ft.Container(width=0),
        ],
    )
    clickable = on_click is not None
    return ft.Container(
        padding=ft.padding.only(left=pad_l, right=8, top=v_pad, bottom=v_pad),
        border_radius=radius,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ink=False,
        on_click=on_click if clickable else None,
        content=row_inner,
    )


def _leaf_lead() -> ft.Container:
    return ft.Container(
        width=_LEADING_SLOT_W,
        alignment=ft.Alignment(-1, 0),
        content=ft.Container(width=4, height=4, bgcolor=_CLR_ICON, border_radius=2),
    )




def _element_rows(nodes: list[_SidebarNodeView]) -> list[ft.Control]:
    rows: list[ft.Control] = []
    cap = nodes[:_ELEMENTS_CAP]
    for n in cap:
        def _tap(e: Event[ft.Container], nid: str = n.node_id) -> None:
            _log("ELEM", f"select (stub) {nid!r}")

        rows.append(
            _tree_row(
                leading=_leaf_lead(),
                title=n.label,
                subtitle=None,
                trailing=None,
                on_click=_tap,
                indent=_IND_UNDER_ROOT,
                dense=True,
                title_size=_FS_BODY,
                title_weight=ft.FontWeight.W_400,
                title_tooltip=_ellipsis_only_tooltip(n.label),
            ),
        )
    rest = len(nodes) - len(cap)
    if rest > 0:
        rows.append(
            ft.Container(
                padding=ft.padding.only(left=_IND_UNDER_ROOT + 14, top=4, bottom=8),
                content=ft.Text(f"+{rest} more in this bucket", size=11, color=_CLR_MUTED),
            ),
        )
    if not rows:
        rows.append(
            ft.Container(
                padding=ft.padding.only(left=_IND_UNDER_ROOT + 14, top=2, bottom=8),
                content=ft.Text("No elements", size=11, color=_CLR_MUTED),
            ),
        )
    return rows


def _domain_element_rows(
    nodes: list[_SidebarNodeView],
    *,
    level3_diagrams: list[NodeEntity],
    domain_elem_open: dict[str, bool],
    toggle_domain_elem: Callable[[str, Any], None],
    on_diagram: Callable[[NodeEntity], None],
) -> list[ft.Control]:
    """Domain bucket: each domain row expands to level-3 diagram rows from ``NodeEntity`` data."""
    rows: list[ft.Control] = []
    cap = nodes[:_ELEMENTS_CAP]
    for n in cap:
        if n.node_type == "Domain":
            nid = n.node_id
            expanded = domain_elem_open.get(nid, False)

            def on_domain_row(ev: Any, node_id: str = nid) -> None:
                toggle_domain_elem(node_id, ev)

            rows.append(
                _tree_row(
                    leading=ft.Icon(
                        (ft.Icons.EXPAND_MORE_OUTLINED if expanded else ft.Icons.CHEVRON_RIGHT_OUTLINED),
                        size=_ICON_TREE,
                        color=_CLR_ICON,
                    ),
                    title=n.label,
                    subtitle=None,
                    trailing=None,
                    on_click=on_domain_row,
                    indent=_IND_UNDER_ROOT,
                    dense=True,
                    title_size=_FS_BODY,
                    title_weight=ft.FontWeight.W_400,
                    title_color=_CLR_TEXT,
                    title_tooltip=_ellipsis_only_tooltip(n.label),
                ),
            )
            if not expanded:
                continue
            for ent in sorted(
                (x for x in level3_diagrams if x.parent_id == nid),
                key=lambda x: (x.label.lower(), x.id),
            ):
                rows.append(
                    _views_row(
                        label=ent.label,
                        icon=_diagram_icon_for_type(ent.type),
                        on_invoke=lambda _ev, e=ent: on_diagram(e),
                        indent=_IND_UNDER_DOMAIN,
                    ),
                )
            continue

        rows.append(
            _tree_row(
                leading=_leaf_lead(),
                title=n.label,
                subtitle=None,
                trailing=None,
                on_click=None,
                indent=_IND_UNDER_ROOT,
                dense=True,
                title_size=_FS_BODY,
                title_weight=ft.FontWeight.W_400,
                title_tooltip=_ellipsis_only_tooltip(n.label),
            ),
        )
    rest = len(nodes) - len(cap)
    if rest > 0:
        rows.append(
            ft.Container(
                padding=ft.padding.only(left=_IND_UNDER_ROOT + 14, top=4, bottom=8),
                content=ft.Text(f"+{rest} more in this bucket", size=11, color=_CLR_MUTED),
            ),
        )
    if not rows:
        rows.append(
            ft.Container(
                padding=ft.padding.only(left=_IND_UNDER_ROOT + 14, top=2, bottom=8),
                content=ft.Text("No elements", size=11, color=_CLR_MUTED),
            ),
        )
    return rows


def _diagram_icon_for_type(diagram_type: str) -> Any:
    """Pick a Material icon for a diagram row ``NodeEntity.type``."""
    if diagram_type == "graph":
        return ft.Icons.HUB_OUTLINED
    return ft.Icons.ACCOUNT_TREE_OUTLINED


def _diagram_rows_for_root(
    root_key: str,
    diagrams: list[NodeEntity],
    *,
    indent: int,
    on_diagram: Callable[[NodeEntity], None],
) -> list[ft.Control]:
    """Render diagram ``NodeEntity`` rows whose ``parent_id`` matches the expanded root."""
    rows: list[ft.Control] = []
    for d in sorted(
        (x for x in diagrams if x.parent_id == root_key),
        key=lambda x: (x.label.lower(), x.id),
    ):
        rows.append(
            _views_row(
                label=d.label,
                icon=_diagram_icon_for_type(d.type),
                on_invoke=lambda _ev, ent=d: on_diagram(ent),
                indent=indent,
            ),
        )
    return rows


def _views_row(
    *,
    label: str,
    icon: Any,
    on_invoke: Callable[[Any], None],
    indent: int,
) -> ft.Container:
    return _tree_row(
        leading=ft.Icon(icon, size=_ICON_TREE, color=_CLR_ICON),
        title=label,
        subtitle=None,
        trailing=None,
        on_click=on_invoke,
        indent=indent,
        dense=True,
        title_size=_FS_BODY,
        title_weight=ft.FontWeight.W_400,
        title_color=_CLR_TEXT,
        title_tooltip=_ellipsis_only_tooltip(label),
    )


def _compact_toolbar_icon(
    icon: Any,
    *,
    tooltip: str,
    on_click: Callable[[Any], None],
) -> ft.IconButton:
    """Small padded icon-only control for sidebar toolbars."""
    return ft.IconButton(
        icon=icon,
        icon_size=_ICON_TOOLBAR,
        icon_color=_CLR_ICON,
        tooltip=tooltip,
        style=ft.ButtonStyle(padding=ft.padding.all(2)),
        on_click=on_click,
    )


def _sidebar_top_tools(*, on_hide_menu: Callable[[Any], None], on_search: Callable[[Any], None]) -> ft.Control:
    """Narrow toolbar: sidebar toggle + search (fixed, not scrolled); no divider line."""
    return ft.Container(
        padding=ft.padding.only(left=6, right=6, top=8, bottom=8),
        content=ft.Row(
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _compact_toolbar_icon(
                    ft.Icons.VIEW_SIDEBAR_OUTLINED,
                    tooltip="Hide sidebar",
                    on_click=on_hide_menu,
                ),
                _compact_toolbar_icon(ft.Icons.SEARCH_OUTLINED, tooltip="Search", on_click=on_search),
            ],
        ),
    )


def _sidebar_footer_stub(*, on_filter: Callable[[Any], None], on_settings: Callable[[Any], None]) -> ft.Control:
    """Bottom strip: initials, line-style actions, gear — fixed; no divider line above."""
    avatar = ft.Container(
        width=28,
        height=28,
        border_radius=14,
        bgcolor="#cbd5e0",
        alignment=ft.Alignment.CENTER,
        tooltip="Account (stub)",
        content=ft.Text(
            "MX",
            size=10,
            weight=ft.FontWeight.W_700,
            color=_CLR_TEXT,
            text_align=ft.TextAlign.CENTER,
            no_wrap=True,
        ),
    )
    return ft.Container(
        padding=ft.padding.only(left=8, right=8, top=12, bottom=12),
        content=ft.Row(
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[
                avatar,
                ft.Container(expand=True),
                _compact_toolbar_icon(
                    ft.Icons.SHORT_TEXT_OUTLINED,
                    tooltip="Filter",
                    on_click=on_filter,
                ),
                _compact_toolbar_icon(
                    ft.Icons.SETTINGS_OUTLINED,
                    tooltip="Settings",
                    on_click=on_settings,
                ),
            ],
        ),
    )


def _build_sidebar_tree(
    *,
    payload: list[tuple[str, str, list[_SidebarNodeView]]],
    level2_diagrams: list[NodeEntity],
    level3_diagrams: list[NodeEntity],
    root_open: dict[str, bool],
    domain_elem_open: dict[str, bool],
    toggle_root: Callable[[str, Event[ft.Container]], None],
    toggle_domain_elem: Callable[[str, Event[ft.Container]], None],
    on_diagram: Callable[[NodeEntity], None],
) -> list[ft.Control]:
    blocks: list[ft.Control] = []
    nroots = len(payload)
    for idx, (key, title, nodes) in enumerate(payload):
        ro = root_open.get(key, False)

        def on_root_click(ev: Any, kk: str = key) -> None:
            toggle_root(kk, ev)

        inner: list[ft.Control] = [
            _tree_row(
                leading=ft.Icon(
                    ft.Icons.EXPAND_MORE_OUTLINED if ro else ft.Icons.CHEVRON_RIGHT_OUTLINED,
                    size=_ICON_TREE,
                    color=_CLR_ICON,
                ),
                title=title,
                subtitle=None,
                trailing=None,
                on_click=on_root_click,
                indent=0,
                dense=False,
                title_size=_FS_SECTION,
                title_weight=ft.FontWeight.W_500,
                title_color=_CLR_SECTION,
                title_tooltip=_ellipsis_only_tooltip(title),
            ),
        ]

        if ro:
            inner.append(ft.Container(height=2))
            inner.extend(
                _diagram_rows_for_root(
                    key,
                    level2_diagrams,
                    indent=_IND_UNDER_ROOT,
                    on_diagram=on_diagram,
                ),
            )

            if key == "domains_root":
                inner.extend(
                    _domain_element_rows(
                        nodes,
                        level3_diagrams=level3_diagrams,
                        domain_elem_open=domain_elem_open,
                        toggle_domain_elem=toggle_domain_elem,
                        on_diagram=on_diagram,
                    ),
                )
            else:
                inner.extend(_element_rows(nodes))

        blocks.append(ft.Column(spacing=0, tight=True, controls=inner))
        if idx < nroots - 1:
            blocks.append(ft.Container(height=4))

    return blocks


def _placeholder_workspace() -> ft.Container:
    return ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=[
                ft.Icon(ft.Icons.TOUCH_APP_OUTLINED, size=32, color=_CLR_ICON),
                ft.Text(
                    "Open the interchange graph under Application or an ERD under Domains.",
                    size=14,
                    color=_CLR_MUTED,
                    weight=ft.FontWeight.W_400,
                ),
            ],
        ),
    )


async def main(page: ft.Page, sidebar_data: Any) -> None:
    _log("APP", f"platform={page.platform!r} flet={ft.__version__!r} py={sys.version.split()[0]}")

    page.title = "Maxitor"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(use_material3=True, color_scheme_seed="#5c6370")

    if page.web:
        page.add(ft.Text("Desktop only: python -m aoa.maxitor.flet_shell", selectable=True))
        return

    if page.platform is not None and page.platform not in (
        PagePlatform.MACOS,
        PagePlatform.IOS,
        PagePlatform.ANDROID,
    ):
        page.add(ft.Text(f"flet-webview not supported on {page.platform!r}", selectable=True))
        return

    try:
        from flet_webview import WebView

        _log("APP", "flet_webview OK")
    except ImportError:
        page.add(ft.Text("Install aoa-maxitor[flet]", selectable=True))
        return

    last_browser_url: list[str | None] = [None]
    current_wv: list[Any] = [None]

    by_parent: dict[str, list[_SidebarNodeView]] = {}
    for n in sidebar_data.level2_nodes:
        pk = n.parent_id or ""
        by_parent.setdefault(pk, []).append(_SidebarNodeView(n.id, n.label, n.type))
    root_payload: list[tuple[str, str, list[_SidebarNodeView]]] = [
        (
            l1.id,
            l1.label,
            sorted(by_parent.get(l1.id, []), key=lambda r: (r.label.lower(), r.node_id)),
        )
        for l1 in sidebar_data.level1_nodes
    ]

    root_open: dict[str, bool] = {n.id: False for n in sidebar_data.level1_nodes}
    domain_elem_open: dict[str, bool] = {}

    def on_web_resource_error(e: ft.ControlEvent) -> None:
        _log("WV", f"ERROR: {e.data}")

    def on_page_started(e: ft.ControlEvent) -> None:
        _log("WV", f"STARTED: {e.data}")

    def on_page_ended(e: ft.ControlEvent) -> None:
        _log("WV", f"ENDED: {e.data}")

    def on_progress(e: ft.ControlEvent) -> None:
        _log("WV", f"PROGRESS: {e.data}%")

    def _make_webview(url: str) -> WebView:
        _log("WV", f"Creating WebView(url={url!r})")
        return WebView(
            url=url,
            expand=True,
            on_web_resource_error=on_web_resource_error,
            on_page_started=on_page_started,
            on_page_ended=on_page_ended,
            on_progress=on_progress,
        )

    main_row_ref: list[ft.Row | None] = [None]
    # Scrollable tree only; top/footer chrome are fixed siblings in sidebar_panel_ref.
    sidebar_column_ref: list[ft.Column | None] = [None]
    sidebar_panel_ref: list[ft.Column | None] = [None]
    sidebar_outer_ref: list[ft.Container | None] = [None]
    sidebar_collapsed: list[bool] = [False]

    tree_scroll_column = ft.Column(
        spacing=0,
        tight=True,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[],
    )
    sidebar_column_ref[0] = tree_scroll_column

    sidebar_panel = ft.Column(expand=True, spacing=0, tight=True, controls=[])
    sidebar_panel_ref[0] = sidebar_panel

    sidebar_container = ft.Container(
        width=_SIDEBAR_WIDTH,
        bgcolor=_CLR_BG,
        padding=6,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=sidebar_panel,
    )
    sidebar_outer_ref[0] = sidebar_container

    def toggle_sidebar_panel(_: Any) -> None:
        sidebar_collapsed[0] = not sidebar_collapsed[0]
        apply_sidebar_shell()
        page.update()

    def sidebar_search_stub(_: Any) -> None:
        _log("UI", "Search (stub)")

    def sidebar_filter_stub(_: Any) -> None:
        _log("UI", "Filter (stub)")

    def sidebar_settings_stub(_: Any) -> None:
        _log("UI", "Settings (stub)")

    def apply_sidebar_shell() -> None:
        panel = sidebar_panel_ref[0]
        outer = sidebar_outer_ref[0]
        if panel is None or outer is None:
            return
        collapsed = sidebar_collapsed[0]
        outer.width = _SIDEBAR_COLLAPSED_W if collapsed else _SIDEBAR_WIDTH
        outer.padding = ft.padding.all(3) if collapsed else ft.padding.all(6)
        panel.controls.clear()
        if collapsed:
            panel.controls.append(
                ft.Container(
                    expand=True,
                    padding=ft.padding.only(top=4),
                    alignment=ft.Alignment(0, -1),
                    content=ft.IconButton(
                        icon=ft.Icons.CHEVRON_RIGHT_OUTLINED,
                        icon_size=_ICON_COLLAPSE_STRIP,
                        icon_color=_CLR_ICON,
                        tooltip="Expand sidebar",
                        style=ft.ButtonStyle(padding=ft.padding.all(2)),
                        on_click=toggle_sidebar_panel,
                    ),
                ),
            )
        else:
            panel.controls.append(
                _sidebar_top_tools(on_hide_menu=toggle_sidebar_panel, on_search=sidebar_search_stub),
            )
            panel.controls.append(ft.Container(expand=True, content=tree_scroll_column))
            panel.controls.append(_sidebar_footer_stub(on_filter=sidebar_filter_stub, on_settings=sidebar_settings_stub))

    apply_sidebar_shell()

    async def _replace_webview(url: str, file_path: Path | None = None) -> None:
        row = main_row_ref[0]
        if row is None:
            return
        wv = _make_webview(url)
        current_wv[0] = wv
        row.controls[1] = wv
        page.update()
        await asyncio.sleep(0.3)

        if file_path is not None:
            _log("WV", f"load_file({file_path})")
            try:
                await wv.load_file(str(file_path.resolve()))
                _log("WV", "load_file OK")
            except Exception as exc:
                _log("WV", f"load_file FAILED: {exc}\n{traceback.format_exc()}")
                page.update()

        if _should_open_browser_too() and last_browser_url[0]:
            webbrowser.open(last_browser_url[0])

    async def _show_placeholder() -> None:
        row = main_row_ref[0]
        if row is None:
            return
        current_wv[0] = None
        row.controls[1] = _placeholder_workspace()
        page.update()
        await asyncio.sleep(0.05)

    async def open_viewer(view_kind: str, domain_cls: type[BaseDomain] | None = None) -> None:
        _log("ACTION", f"open_viewer {view_kind!r} domain_cls={domain_cls!r}")
        page.update()
        await _show_placeholder()

        slug = view_kind
        if view_kind == "erd_domain" and domain_cls is not None:
            slug = f"erd_domain_{domain_cls.__name__}"
        tmp = Path(tempfile.gettempdir()) / f"aoa_maxitor_flet_{slug}_{time.time_ns()}.html"

        if view_kind == "erd_domain" and domain_cls is None:
            _log("EXPORT", "erd_domain: missing domain_cls — abort")
            page.update()
            return

        def run_export() -> None:
            if view_kind == "graph":
                _export_graph_html(tmp)
            elif view_kind == "erd_all":
                _export_erd_html(tmp, domain_cls=None)
            elif view_kind == "erd_domain":
                assert domain_cls is not None
                _export_erd_html(tmp, domain_cls=domain_cls)
            else:
                _log("EXPORT", f"unknown view_kind {view_kind!r}")

        try:
            await asyncio.to_thread(run_export)
        except Exception as exc:
            _log("EXPORT", f"failed: {exc}")
            page.update()
            return

        try:
            base = _start_preview_httpd(tmp.parent)
            last_browser_url[0] = f"{base}{urllib.parse.quote(tmp.name)}?t={time.time_ns()}"
        except Exception as exc:
            _log("HTTP", f"server failed (non-fatal): {exc}")
            last_browser_url[0] = tmp.as_uri()

        page.update()
        await _replace_webview("about:blank", file_path=tmp)
        page.update()

    def on_diagram(d: NodeEntity) -> None:
        if d.type == "graph":
            page.run_task(open_viewer, "graph")
        elif d.type == "erd_all":
            page.run_task(open_viewer, "erd_all")
        elif d.type == "erd_domain":
            pid = d.parent_id
            if not pid:
                _log("ACTION", "erd_domain row without parent_id")
                return
            page.run_task(open_viewer, "erd_domain", _import_domain_type(pid))
        else:
            _log("ACTION", f"unhandled diagram node type {d.type!r}")

    def refresh_sidebar() -> None:
        col = sidebar_column_ref[0]
        if col is None:
            return

        def tr(k: str, e: Event[ft.Container]) -> None:
            root_open[k] = not root_open.get(k, False)
            refresh_sidebar()

        def tde(node_id: str, e: Event[ft.Container]) -> None:
            domain_elem_open[node_id] = not domain_elem_open.get(node_id, False)
            refresh_sidebar()

        col.controls.clear()
        if not root_payload:
            col.controls.append(ft.Text("Empty coordinator", color=_CLR_MUTED, size=12))
        else:
            col.controls.extend(
                _build_sidebar_tree(
                    payload=root_payload,
                    level2_diagrams=sidebar_data.level2_diagrams,
                    level3_diagrams=sidebar_data.level3_diagrams,
                    root_open=root_open,
                    domain_elem_open=domain_elem_open,
                    toggle_root=tr,
                    toggle_domain_elem=tde,
                    on_diagram=on_diagram,
                ),
            )
        page.update()

    main_row = ft.Row(
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            sidebar_container,
            _placeholder_workspace(),
        ],
    )
    main_row_ref[0] = main_row
    page.add(ft.Column(spacing=0, expand=True, controls=[main_row]))

    refresh_sidebar()
    await _show_placeholder()
    _log("APP", "Ready.")
