# packages/aoa-maxitor/src/aoa/maxitor/flet_shell/app.py
"""
Flet shell — six root domain buckets + custom model tree + WebView workspace.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Sidebar header (Model + collapse) is fixed; only the tree scrolls. Collapse narrows the strip to a reopen chevron.
Every ``node_type`` not in the first five primaries is grouped under **Resources**.
Sections expand to show **diagram rows first**, then coordinator **elements** — no intermediate
``Views`` / ``Elements`` folders.
**Application**: interchange graph row, then nodes in that bucket.
**Domains**: ERD covering all bounded contexts first, then domain / other nodes (per-domain ``ERD`` inline under each ``DomainGraphNode`` when expanded).
Other roots: coordinator nodes only.

Right: ``WebView(expand=True)`` or placeholder. Do not use ``set_javascript_mode()``
on macOS (flet-webview issue #13).

Run: ``python -m aoa.maxitor.flet_shell``.
"""

from __future__ import annotations

import asyncio
import http.server
import os
import socketserver
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
import webbrowser
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import flet as ft
from flet.controls.control_event import Event
from flet.controls.types import PagePlatform

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
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
# Indent for diagram + element rows directly under an expanded section root (no Views/Elements branch).
_IND_UNDER_ROOT = 22
_IND_UNDER_DOMAIN = _IND_UNDER_ROOT + 13
_AUTO_BROWSER_ENV = "MAXITOR_FLET_AUTO_BROWSER"

_CLR_BG = "#f4f5f7"
_CLR_BORDER = "#e5e7eb"
_CLR_RULE = "#eceef2"
_CLR_TEXT = "#131318"
_CLR_MUTED = "#5f6368"
_CLR_DIM = "#8d9199"

# Primary graph node_type → root key (everything else → resources)
_PRIMARY_TO_ROOT: dict[str, str] = {
    "Application": "application",
    "Domain": "domains",
    "Role": "roles",
    "Action": "actions",
    "Entity": "entities",
    "Resource": "resources",
}
_ROOT_ORDER: tuple[str, ...] = (
    "application",
    "domains",
    "roles",
    "actions",
    "entities",
    "resources",
)
_ROOT_LABEL: dict[str, str] = {
    "application": "Application",
    "domains": "Domains",
    "roles": "Roles",
    "actions": "Actions",
    "entities": "Entities",
    "resources": "Resources",
}

_http_lock = threading.Lock()
_httpd: socketserver.ThreadingTCPServer | None = None


def _root_buckets(coordinator: NodeGraphCoordinator) -> list[tuple[str, str, list[BaseGraphNode[Any]]]]:
    """Always six buckets: primary types map to their root; all other types → resources."""
    buckets: defaultdict[str, list[BaseGraphNode[Any]]] = defaultdict(list)
    for node in coordinator.get_all_nodes():
        rk = _PRIMARY_TO_ROOT.get(node.node_type, "resources")
        buckets[rk].append(node)
    out: list[tuple[str, str, list[BaseGraphNode[Any]]]] = []
    for key in _ROOT_ORDER:
        nodes_i = buckets.get(key, [])
        out.append((key, _ROOT_LABEL[key], sorted(nodes_i, key=lambda n: (n.label.lower(), n.node_id))))
    return out


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


def _muted_meta(text: str, *, narrow: bool = False) -> ft.Text:
    return ft.Text(
        text,
        size=11 if not narrow else 10,
        color=_CLR_DIM,
        weight=ft.FontWeight.W_400,
        selectable=False,
    )


def _full_title_tooltip(full: str) -> str | None:
    """Return tooltip text when non-empty (full coordinator label while row text may ellipsis)."""
    s = full.strip()
    return s if s else None


def _tree_row(
    *,
    leading: ft.Control | None,
    title: str,
    subtitle: str | None,
    trailing: ft.Control | None,
    on_click: Callable[[Any], Any] | None,
    indent: int = 0,
    dense: bool = False,
    title_size: float = 12.5,
    title_weight: ft.FontWeight = ft.FontWeight.W_400,
    title_color: str = _CLR_TEXT,
    title_tooltip: str | None = None,
    title_max_lines: int = 1,
    radius: float = 4,
) -> ft.Container:
    pad_l = 8 + indent
    v_pad = 5 if dense else 7
    row_inner = ft.Row(
        tight=True,
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            leading if leading is not None else ft.Container(width=0),
            ft.Column(
                tight=True,
                spacing=0,
                expand=True,
                controls=[
                    ft.Text(
                        title,
                        size=title_size,
                        color=title_color,
                        weight=title_weight,
                        max_lines=title_max_lines,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    *([ft.Text(subtitle, size=11, color=_CLR_MUTED)] if subtitle else []),
                ],
            ),
            trailing if trailing is not None else ft.Container(width=0),
        ],
    )
    clickable = on_click is not None
    return ft.Container(
        padding=ft.padding.only(left=pad_l, right=6, top=v_pad, bottom=v_pad),
        border_radius=radius,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ink=clickable,
        on_click=on_click if clickable else None,
        tooltip=(title_tooltip or None),
        content=row_inner,
    )


def _leaf_lead() -> ft.Container:
    return ft.Container(
        width=16,
        alignment=ft.Alignment(-1, 0),
        content=ft.Container(width=3, height=3, bgcolor=_CLR_DIM, border_radius=2),
    )




def _element_rows(nodes: list[BaseGraphNode[Any]]) -> list[ft.Control]:
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
                title_size=12,
                title_weight=ft.FontWeight.W_400,
                title_tooltip=_full_title_tooltip(n.label),
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
    nodes: list[BaseGraphNode[Any]],
    *,
    domain_elem_open: dict[str, bool],
    toggle_domain_elem: Callable[[str, Any], None],
    erd_for_domain: Callable[[type[BaseDomain]], Callable[[Any], None]],
) -> list[ft.Control]:
    """Domain bucket: each :class:`DomainGraphNode` expands to an ERD row (no nested Views folder)."""
    rows: list[ft.Control] = []
    cap = nodes[:_ELEMENTS_CAP]
    for n in cap:
        if isinstance(n, DomainGraphNode):
            dc = cast(type[BaseDomain], n.node_obj)
            nid = n.node_id
            expanded = domain_elem_open.get(nid, False)

            def on_domain_row(ev: Any, node_id: str = nid) -> None:
                toggle_domain_elem(node_id, ev)

            rows.append(
                _tree_row(
                    leading=ft.Icon(
                        ft.Icons.EXPAND_MORE if expanded else ft.Icons.CHEVRON_RIGHT,
                        size=14,
                        color=_CLR_DIM,
                    ),
                    title=n.label,
                    subtitle=None,
                    trailing=None,
                    on_click=on_domain_row,
                    indent=_IND_UNDER_ROOT,
                    dense=True,
                    title_size=12,
                    title_weight=ft.FontWeight.W_400,
                    title_color=_CLR_TEXT,
                    title_tooltip=_full_title_tooltip(n.label),
                ),
            )
            if not expanded:
                continue
            rows.append(ft.Container(height=2))
            rows.append(
                _views_row(
                    label="ERD",
                    icon=ft.Icons.ACCOUNT_TREE_OUTLINED,
                    on_invoke=erd_for_domain(dc),
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
                title_size=12,
                title_weight=ft.FontWeight.W_400,
                title_tooltip=_full_title_tooltip(n.label),
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


def _views_row(
    *,
    label: str,
    icon: Any,
    on_invoke: Callable[[Any], None],
    indent: int,
) -> ft.Container:
    return _tree_row(
        leading=ft.Icon(icon, size=14, color=_CLR_MUTED),
        title=label,
        subtitle=None,
        trailing=None,
        on_click=on_invoke,
        indent=indent,
        dense=True,
        title_size=12,
        title_weight=ft.FontWeight.W_400,
        title_color=_CLR_TEXT,
        title_tooltip=_full_title_tooltip(label),
    )


def _sidebar_header_bar(*, on_collapse: Callable[[Any], None]) -> ft.Control:
    """Fixed toolbar: title + collapse (scrollable tree lives below in a separate column)."""
    return ft.Container(
        padding=ft.padding.only(left=2, right=0, bottom=10, top=2),
        content=ft.Column(
            spacing=10,
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            "Model",
                            size=13,
                            weight=ft.FontWeight.W_500,
                            color=_CLR_TEXT,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CHEVRON_LEFT,
                            icon_size=18,
                            icon_color=_CLR_DIM,
                            tooltip="Collapse panel",
                            style=ft.ButtonStyle(padding=ft.padding.all(4)),
                            on_click=on_collapse,
                        ),
                    ],
                ),
                ft.Container(height=1, bgcolor=_CLR_RULE),
            ],
        ),
    )


def _build_sidebar_tree(
    *,
    payload: list[tuple[str, str, list[BaseGraphNode[Any]]]],
    root_open: dict[str, bool],
    domain_elem_open: dict[str, bool],
    toggle_root: Callable[[str, Event[ft.Container]], None],
    toggle_domain_elem: Callable[[str, Event[ft.Container]], None],
    graph_cb: Callable[[Any], None],
    erd_all_cb: Callable[[Any], None],
    erd_for_domain: Callable[[type[BaseDomain]], Callable[[Any], None]],
) -> list[ft.Control]:
    blocks: list[ft.Control] = []
    nroots = len(payload)
    for idx, (key, title, nodes) in enumerate(payload):
        nitems = len(nodes)
        ro = root_open.get(key, False)

        def on_root_click(ev: Any, kk: str = key) -> None:
            toggle_root(kk, ev)

        inner: list[ft.Control] = [
            _tree_row(
                leading=ft.Icon(
                    ft.Icons.EXPAND_MORE if ro else ft.Icons.CHEVRON_RIGHT,
                    size=14,
                    color=_CLR_DIM,
                ),
                title=title,
                subtitle=None,
                trailing=_muted_meta(str(nitems)),
                on_click=on_root_click,
                indent=4,
                dense=False,
                title_size=12,
                title_weight=ft.FontWeight.W_500,
                title_color=_CLR_TEXT,
                title_tooltip=_full_title_tooltip(title),
            ),
        ]

        if ro:
            inner.append(ft.Container(height=4))

            if key == "application":
                inner.append(
                    _views_row(
                        label="Interchange graph",
                        icon=ft.Icons.HUB_OUTLINED,
                        on_invoke=graph_cb,
                        indent=_IND_UNDER_ROOT,
                    ),
                )

            elif key == "domains":
                inner.append(
                    _views_row(
                        label="ERD — all domains",
                        icon=ft.Icons.ACCOUNT_TREE_OUTLINED,
                        on_invoke=erd_all_cb,
                        indent=_IND_UNDER_ROOT,
                    ),
                )

            if key == "domains":
                inner.extend(
                    _domain_element_rows(
                        nodes,
                        domain_elem_open=domain_elem_open,
                        toggle_domain_elem=toggle_domain_elem,
                        erd_for_domain=erd_for_domain,
                    ),
                )
            else:
                inner.extend(_element_rows(nodes))

        blocks.append(ft.Column(spacing=0, tight=True, controls=inner))
        if idx < nroots - 1:
            blocks.append(ft.Container(height=10))

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
                ft.Icon(ft.Icons.TOUCH_APP_OUTLINED, size=40, color=_CLR_MUTED),
                ft.Text(
                    "Open the interchange graph under Application or an ERD under Domains.",
                    size=14,
                    color=_CLR_MUTED,
                    weight=ft.FontWeight.W_400,
                ),
            ],
        ),
    )


async def main(page: ft.Page) -> None:
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
    coordinator = await asyncio.to_thread(_interchange_coordinator)
    root_payload = await asyncio.to_thread(_root_buckets, coordinator)

    root_open: dict[str, bool] = dict.fromkeys(_ROOT_ORDER, False)
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
    # Scrollable tree only (heading + collapse chrome sit in sidebar_panel_ref, not scrolled).
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
        border=ft.border.only(right=ft.BorderSide(1, _CLR_BORDER)),
        padding=7,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=sidebar_panel,
    )
    sidebar_outer_ref[0] = sidebar_container

    def toggle_sidebar_panel(_: Any) -> None:
        sidebar_collapsed[0] = not sidebar_collapsed[0]
        apply_sidebar_shell()
        page.update()

    def apply_sidebar_shell() -> None:
        panel = sidebar_panel_ref[0]
        outer = sidebar_outer_ref[0]
        if panel is None or outer is None:
            return
        collapsed = sidebar_collapsed[0]
        outer.width = _SIDEBAR_COLLAPSED_W if collapsed else _SIDEBAR_WIDTH
        outer.padding = ft.padding.all(3) if collapsed else ft.padding.all(7)
        panel.controls.clear()
        if collapsed:
            panel.controls.append(
                ft.Container(
                    expand=True,
                    padding=ft.padding.only(top=4),
                    alignment=ft.Alignment(0, -1),
                    content=ft.IconButton(
                        icon=ft.Icons.CHEVRON_RIGHT,
                        icon_size=20,
                        icon_color=_CLR_DIM,
                        tooltip="Expand model panel",
                        style=ft.ButtonStyle(padding=ft.padding.all(2)),
                        on_click=toggle_sidebar_panel,
                    ),
                ),
            )
        else:
            panel.controls.append(_sidebar_header_bar(on_collapse=toggle_sidebar_panel))
            panel.controls.append(ft.Container(expand=True, content=tree_scroll_column))

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

    def graph_cb(_: Any) -> None:
        page.run_task(open_viewer, "graph")

    def erd_all_cb(_: Any) -> None:
        page.run_task(open_viewer, "erd_all")

    def erd_factory(dc: type[BaseDomain]) -> Callable[[Any], None]:
        """Build a click handler that opens a single-domain ERD for ``dc``."""

        def _invoke(_: Any) -> None:
            page.run_task(open_viewer, "erd_domain", dc)

        return _invoke

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
                    root_open=root_open,
                    domain_elem_open=domain_elem_open,
                    toggle_root=tr,
                    toggle_domain_elem=tde,
                    graph_cb=graph_cb,
                    erd_all_cb=erd_all_cb,
                    erd_for_domain=erd_factory,
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
