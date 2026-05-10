# packages/aoa-maxitor/src/aoa/maxitor/model/app_view/actions/_erd_domain_import.py
"""
Interchange domain qualname → ``BaseDomain`` type resolution (shared by ERD actions).
"""

from __future__ import annotations

import importlib
from typing import Any, cast

from aoa.action_machine.domain.base_domain import BaseDomain


def import_domain_type_from_qualname(qualname: str) -> type[BaseDomain]:
    """Resolve a domain class from its interchange ``node_id`` (module-qualified name)."""
    if "." not in qualname:
        msg = f"Invalid domain type qualname: {qualname!r}"
        raise ValueError(msg)
    parts = qualname.split(".")
    for mod_len in range(len(parts) - 1, 0, -1):
        mod_name = ".".join(parts[:mod_len])
        attr_path = parts[mod_len:]
        try:
            module = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue
        obj: Any = module
        try:
            for attr in attr_path:
                obj = getattr(obj, attr)
        except AttributeError:
            continue
        if isinstance(obj, type) and issubclass(obj, BaseDomain):
            return cast(type[BaseDomain], obj)
    msg = f"Not a BaseDomain subclass or not importable: {qualname!r}"
    raise TypeError(msg)
