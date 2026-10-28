# packages/maxitor/src/maxitor/viewer/model/rooms/pages.py
"""
Pages and their settings — what a room may share, and how a page is named.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A room shares the settings of every page — the filters and the layout mode of an ERD,
a use-case diagram, a lifecycle (spec 028, FR-030). A page is named by a canonical
key built from the address the client already uses: ``view`` and its parameters, in
a fixed order. This module knows the keys a service's left panel offers, the
settings each kind of page has, and the values each setting accepts; the room
actions use it to refuse a page that does not exist or a value that does not fit.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    sidebar rows ──page_keys()──► {"view=full-graph", "view=domain-erd&domain=…", …}
    page key + setting + value ──setting_error()──► None | why it is refused
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import parse_qsl, urlencode

#: The order of the address parameters in a page key (``client/src/lib/urlState.ts``).
_KEY_ORDER = ("view", "domain", "node", "host")


def page_key(view: str, **params: str) -> str:
    """The canonical key of a page: ``view`` and its parameters in the fixed order."""
    values = {"view": view, **params}
    return urlencode([(name, values[name]) for name in _KEY_ORDER if values.get(name)])


def view_of(key: str) -> str:
    """The ``view`` a page key names, or an empty string."""
    return dict(parse_qsl(key)).get("view", "")


def page_keys(sidebar: Any) -> set[str]:
    """Every page the left panel of a service offers, as canonical keys."""
    rows: Iterable[Any] = [*getattr(sidebar, "level2_diagrams", []), *getattr(sidebar, "level3_diagrams", [])]
    keys: set[str] = set()
    for row in rows:
        kind = str(getattr(row, "type", ""))
        parent = getattr(row, "parent_id", None)
        if kind == "graph":
            keys.add(page_key("full-graph"))
        elif kind == "erd_all":
            keys.add(page_key("domain-erd"))
        elif kind == "erd_domain" and parent:
            keys.add(page_key("domain-erd", domain=str(parent)))
        elif kind == "use_case_domain" and parent:
            keys.add(page_key("use-case", domain=str(parent)))
        elif kind == "lifecycle_state_diagram" and parent:
            keys.add(page_key("lifecycle-fsm", node=str(getattr(row, "id", "")), host=str(parent)))
    return keys


def _one_of(*allowed: str) -> Callable[[Any], bool]:
    """A check that accepts exactly one of ``allowed``."""
    return lambda value: value in allowed


def _strings(value: Any) -> bool:
    """A list of strings, the form a set of enabled names travels in."""
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _boolean(value: Any) -> bool:
    """A JSON boolean."""
    return isinstance(value, bool)


#: The settings of each kind of page and the check of each one's value (data-model.md "PageSettings").
SETTINGS: dict[str, dict[str, Callable[[Any], bool]]] = {
    "domain-erd": {
        "layout": _one_of("gv-dot-lr", "gv-dot-tb", "gv-neato", "gv-fdp", "gv-circo"),
        "domains": _strings,
        "disabled_entities": _strings,
        "disabled_kinds": _strings,
        "one_hop": _boolean,
    },
    "use-case": {
        "layout": _one_of("dot_lr", "dot_tb", "neato", "fdp"),
        "domains": _strings,
        "boundary": _boolean,
    },
    "lifecycle-fsm": {
        "rankdir": _one_of("LR", "TB"),
    },
    "full-graph": {},
}


def setting_error(page: str, name: str, value: Any) -> str | None:
    """Why ``name = value`` cannot be set on ``page``, or ``None`` when it can."""
    settings = SETTINGS.get(view_of(page))
    if settings is None:
        return f"unknown page {page!r}"
    check = settings.get(name)
    if check is None:
        return f"{view_of(page)} has no setting {name!r}"
    if not check(value):
        return f"{value!r} is not a value of {name!r}"
    return None


def name_error(name: str) -> str | None:
    """Why ``name`` cannot be a participant's name, or ``None``: 1–40 characters after trimming."""
    trimmed = name.strip()
    if not 1 <= len(trimmed) <= 40:
        return "a name is 1 to 40 characters"
    return None
