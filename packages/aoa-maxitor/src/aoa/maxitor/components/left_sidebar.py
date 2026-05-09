# packages/aoa-maxitor/src/aoa/maxitor/components/left_sidebar.py
"""
LeftSidebar — reusable Flet navigation component for the Maxitor shell.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Own sidebar chrome and tree rendering so :mod:`aoa.maxitor.app` can focus on
workspace orchestration and viewer actions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple

import flet as ft
from flet.controls.control_event import Event

from aoa.maxitor.model.app_view.entities.node_entity import NodeEntity

_SIDEBAR_WIDTH = 228
_ELEMENTS_CAP = 100
_LEADING_SLOT_W = 14
_IND_UNDER_ROOT = 20
_IND_UNDER_DOMAIN = _IND_UNDER_ROOT + 16

_CLR_BG = "#f3f6f7"
_CLR_TEXT = "#24292e"
_CLR_MUTED = "#586069"
_CLR_SECTION = "#6a737d"
_CLR_ICON = "#6a737d"
_ICON_TREE = 12

_FS_BODY = 13.0
_FS_SECTION = 12.0


class _SidebarNodeView(NamedTuple):
    """Lightweight tree row derived from ``GetLeftMenuSidebarDataAction.Result.level2_nodes``."""

    node_id: str
    label: str
    node_type: str


class LeftSidebar:
    """
    AI-CORE-BEGIN
    ROLE: Render and refresh the Maxitor left navigation sidebar as a reusable Flet component.
    CONTRACT: Accepts sidebar_data with level1_nodes, level2_nodes, level2_diagrams, and level3_diagrams; diagram selections are emitted through on_diagram.
    INVARIANTS: The public root control is stable after construction; refresh mutates child controls and leaves workspace concerns to the caller.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        sidebar_data: Any,
        on_diagram: Callable[[NodeEntity], None],
        request_update: Callable[[], None],
    ) -> None:
        self._sidebar_data = sidebar_data
        self._on_diagram = on_diagram
        self._request_update = request_update

        self._root_open: dict[str, bool] = {n.id: False for n in sidebar_data.level1_nodes}
        self._domain_elem_open: dict[str, bool] = {}

        by_parent: dict[str, list[_SidebarNodeView]] = {}
        for n in sidebar_data.level2_nodes:
            pk = n.parent_id or ""
            by_parent.setdefault(pk, []).append(_SidebarNodeView(n.id, n.label, n.type))
        self._root_payload: list[tuple[str, str, list[_SidebarNodeView]]] = [
            (
                l1.id,
                l1.label,
                sorted(by_parent.get(l1.id, []), key=lambda r: (r.label.lower(), r.node_id)),
            )
            for l1 in sidebar_data.level1_nodes
        ]

        self._tree_scroll_column = ft.Column(
            spacing=0,
            tight=True,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[],
        )
        self._panel = ft.Column(expand=True, spacing=0, tight=True, controls=[])
        self.control = ft.Container(
            width=_SIDEBAR_WIDTH,
            bgcolor=_CLR_BG,
            padding=6,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=self._panel,
        )
        self._panel.controls.append(ft.Container(expand=True, content=self._tree_scroll_column))
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the scrollable tree for the current expanded state."""
        self._tree_scroll_column.controls.clear()
        if not self._root_payload:
            self._tree_scroll_column.controls.append(ft.Text("Empty coordinator", color=_CLR_MUTED, size=12))
        else:
            self._tree_scroll_column.controls.extend(self._build_tree())
        self._request_update()

    def _toggle_root(self, key: str, _: Event[ft.Container]) -> None:
        self._root_open[key] = not self._root_open.get(key, False)
        self.refresh()

    def _toggle_domain_elem(self, node_id: str, _: Event[ft.Container]) -> None:
        self._domain_elem_open[node_id] = not self._domain_elem_open.get(node_id, False)
        self.refresh()

    def _build_tree(self) -> list[ft.Control]:
        blocks: list[ft.Control] = []
        nroots = len(self._root_payload)
        for idx, (key, title, nodes) in enumerate(self._root_payload):
            ro = self._root_open.get(key, False)

            def on_root_click(ev: Any, kk: str = key) -> None:
                self._toggle_root(kk, ev)

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
                        self._sidebar_data.level2_diagrams,
                        indent=_IND_UNDER_ROOT,
                        on_diagram=self._on_diagram,
                    ),
                )

                if key == "domains_root":
                    inner.extend(
                        _domain_element_rows(
                            nodes,
                            level3_diagrams=self._sidebar_data.level3_diagrams,
                            domain_elem_open=self._domain_elem_open,
                            toggle_domain_elem=self._toggle_domain_elem,
                            on_diagram=self._on_diagram,
                        ),
                    )
                else:
                    inner.extend(_element_rows(nodes))

            blocks.append(ft.Column(spacing=0, tight=True, controls=inner))
            if idx < nroots - 1:
                blocks.append(ft.Container(height=4))

        return blocks


def _ellipsis_only_tooltip(full: str, *, min_chars: int = 26) -> str | None:
    """Tooltip only when the label is likely truncated in the narrow rail."""
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
    title_ctl = ft.Text(
        title,
        size=title_size,
        color=title_color,
        weight=title_weight,
        max_lines=title_max_lines,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    if title_tooltip is not None:
        title_ctl.tooltip = title_tooltip
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
    return ft.Container(
        padding=ft.padding.only(left=pad_l, right=8, top=v_pad, bottom=v_pad),
        border_radius=radius,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ink=False,
        on_click=on_click if on_click is not None else None,
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


def _domain_element_rows(
    nodes: list[_SidebarNodeView],
    *,
    level3_diagrams: list[NodeEntity],
    domain_elem_open: dict[str, bool],
    toggle_domain_elem: Callable[[str, Any], None],
    on_diagram: Callable[[NodeEntity], None],
) -> list[ft.Control]:
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

