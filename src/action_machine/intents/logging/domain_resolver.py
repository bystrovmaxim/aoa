# src/action_machine/intents/logging/domain_resolver.py
"""
Resolve action domain from ``@meta`` for logging ``var["domain"]``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Callers (factory, machine, plugins) use ``resolve_domain(action_cls)`` when
constructing ``ScopedLogger``. The logger does not read ``@meta`` itself.
``domain_label`` produces a short string for templates (``{%var.domain_name}``).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Return type is ``type[BaseDomain] | None``. ``None`` if metadata or domain
  key is missing.
- If ``@meta`` exists and ``domain`` is present but invalid → ``TypeError``.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``action_cls._meta_info["domain"]`` → validated subclass of ``BaseDomain`` →
stored on ``ScopedLogger`` → copied into ``var["domain"]`` and
``var["domain_name"]`` on each emit.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

``domain_label(OrdersDomain)`` → typically ``"orders"`` from class ``name``,
else ``__name__``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

``TypeError`` when domain is not a ``BaseDomain`` subclass type.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Bridge from @meta domain to logging var fields.
CONTRACT: resolve_domain(cls) -> type[BaseDomain] | None; domain_label for display.
INVARIANTS: invalid domain with meta present raises; None is allowed for tests/no meta.
FLOW: construction sites pass domain into ScopedLogger; coordinator type-checks var.
FAILURES: TypeError on bad domain configuration.
EXTENSION POINTS: none; domain source is @meta only.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.domain.base_domain import BaseDomain


def resolve_domain(action_cls: type) -> type[BaseDomain] | None:
    """
    Read domain from ``@meta`` on the action class.

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
    """``OrdersDomain`` → ``orders``; ``None`` → ``None``; else ``__name__``."""
    if domain is None:
        return None
    return getattr(domain, "name", domain.__name__)
