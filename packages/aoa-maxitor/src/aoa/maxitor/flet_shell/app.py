# packages/aoa-maxitor/src/aoa/maxitor/flet_shell/app.py
"""
Flet shell — six root domain buckets + custom model tree + WebView workspace.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Only the interchange tree scrolls inside the fixed-width sidebar rail.
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
from pathlib import Path
from typing import Any, cast

import flet as ft
from flet.controls.types import PagePlatform

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator
from aoa.maxitor.diagrams.erd_visualizer import write_erd_html_from_coordinator
from aoa.maxitor.diagrams.graph_visualizer import generate_interchange_g6_html
from aoa.maxitor.flet_shell.components import LeftSidebar
from aoa.maxitor.model.app_view.entities.node_entity import NodeEntity
from aoa.maxitor.samples.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)

_AUTO_BROWSER_ENV = "MAXITOR_FLET_AUTO_BROWSER"

_CLR_MUTED = "#586069"
_CLR_ICON = "#6a737d"

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

    left_sidebar = LeftSidebar(
        sidebar_data=sidebar_data,
        on_diagram=on_diagram,
        request_update=page.update,
    )

    main_row = ft.Row(
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            left_sidebar.control,
            _placeholder_workspace(),
        ],
    )
    main_row_ref[0] = main_row
    page.add(ft.Column(spacing=0, expand=True, controls=[main_row]))

    await _show_placeholder()
    _log("APP", "Ready.")
