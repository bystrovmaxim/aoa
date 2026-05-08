# src/action_machine/logging/domain_resolver.py
"""
Resolve action domain from ``@meta`` for logging ``var["domain"]``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Callers (factory, machine, plugins) use ``resolve_domain(action_cls)`` when
constructing ``ScopedLogger``. The logger does not read ``@meta`` itself.
``domain_label`` produces a short string for templates (``{%var.domain_name}``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    action class
        |
        v
    @meta(..., domain=DomainCls)
        |
        v
    resolve_domain(action_cls)
        |
        +--> DomainCls (validated BaseDomain subclass)
        |         |
        |         v
        |   ScopedLogger(domain=DomainCls)
        |         |
        |         v
        |   var["domain"] + var["domain_name"]
        |
        +--> None (no @meta/domain)

"""

from action_machine.domain.base_domain import BaseDomain


def resolve_domain(action_cls: type) -> type[BaseDomain] | None:
    """
    Resolve and validate ``domain`` from action ``@meta``.

    Returns the domain class or ``None`` if ``@meta`` is missing or domain
    absent. If ``@meta`` exists but domain is invalid, raises ``TypeError``.
    """
    meta = getattr(action_cls, "_meta_info", None)
    if meta is None:
        return None
    domain = meta.get("domain")
    if domain is None:
        return None
    if not isinstance(domain, type) or not issubclass(domain, BaseDomain):
        raise TypeError(
            f"@meta on {action_cls.__name__} has invalid domain: {domain!r}. "
            f"Expected a BaseDomain subclass."
        )
    return domain


def domain_label(domain: type[BaseDomain] | None) -> str | None:
    """Return display label for domain class; ``None`` stays ``None``."""
    if domain is None:
        return None
    return getattr(domain, "name", domain.__name__)
