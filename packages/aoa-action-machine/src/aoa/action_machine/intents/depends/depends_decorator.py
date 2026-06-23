# packages/aoa-action-machine/src/aoa/action_machine/intents/depends/depends_decorator.py
"""
``@depends`` decorator — declare class-level dependency requirements.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Attach dependency declarations to a class. At runtime, the dependency list is
read from ``cls._depends_info``, converted into ``DependencyFactory``, and
exposed through ``ToolsBox``. Aspects then resolve dependencies via
``box.resolve(PaymentService)``. For **action** targets, pass
``mode=UseCase.include`` or ``mode=UseCase.extend`` (see package ``__init__``);
resources omit ``mode``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @depends(PaymentService, description="Payment service")
    @depends(SomeAction, mode=UseCase.include, description="Always run peer")
         │
         ▼  writes scratch on cls
    DependencyInfo(cls=PaymentService, description="Payment service")
         │
         ▼  ``DependsGraphEdge`` / interchange metadata read ``_depends_info``
    graph ``Action`` graph node lists dependency targets
         │
         ▼  DependencyFactory(deps); runtime uses ``cls._depends_info`` equivalently
         │
         ▼  ToolsBox.resolve(PaymentService)
    factory.resolve(PaymentService) -> PaymentService()

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from aoa.action_machine.intents.depends.use_case import VALID_USE_CASE_MODES
from aoa.action_machine.runtime.dependency_info import DependencyInfo


def _is_action_target(klass: type) -> bool:
    """True for concrete ``BaseAction`` subclasses (not ``BaseAction`` itself)."""
    from aoa.action_machine.model.base_action import BaseAction  # pylint: disable=import-outside-toplevel

    return klass is not BaseAction and issubclass(klass, BaseAction)


def _is_resource_target(klass: type) -> bool:
    """True for ``BaseResource`` subclasses."""
    from aoa.action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel

    return issubclass(klass, BaseResource)


def _validate_dependency_mode(klass: type, mode: str | None) -> str | None:
    """
    Validate ``mode`` for ``klass`` and return the value stored on ``DependencyInfo``.

    Raises:
        ValueError: ``BaseAction`` as target, illegal ``mode`` for target kind.
    """
    from aoa.action_machine.model.base_action import BaseAction  # pylint: disable=import-outside-toplevel

    if klass is BaseAction:
        msg = "@depends(BaseAction): use a concrete action subclass, not BaseAction itself."
        raise ValueError(msg)

    if _is_action_target(klass):
        if mode is None or mode not in VALID_USE_CASE_MODES:
            raise ValueError(
                f"@depends({klass.__name__}): BaseAction dependencies require "
                f"mode=UseCase.include or mode=UseCase.extend, got {mode!r}.",
            )
        return mode

    if _is_resource_target(klass):
        if mode is not None:
            raise ValueError(
                f"@depends({klass.__name__}): resource dependencies must not set mode (got {mode!r}).",
            )
        return None

    if mode is not None:
        raise ValueError(
            f"@depends({klass.__name__}): mode is only valid for BaseAction targets; got {mode!r}.",
        )
    return None


def depends(
    klass: Any,
    *,
    mode: str | None = None,
    factory: Callable[..., Any] | None = None,
    description: str = "",
) -> Callable[[type], type]:
    """
    Class decorator that declares a dependency on an external service.

    Writes a ``DependencyInfo`` record into the target class's ``_depends_info``
    list. When first applied to a subclass, copies the parent list to avoid
    mutation.

    Args:
        klass: Dependency class (must be a type and satisfy the bound).
        mode: For ``BaseAction`` targets, ``UseCase.include`` or ``UseCase.extend``.
              Must be ``None`` for resources and non-action dependency types.
        factory: Optional factory for creating the instance.
        description: Human‑readable description for documentation.

    Returns:
        A decorator that adds ``DependencyInfo`` to ``cls._depends_info``.

    Raises:
        TypeError: Invalid argument types, target not a class, or missing intent.
        ValueError: Duplicate dependency declaration or invalid ``mode`` for target kind.

    AI-CORE-BEGIN
    PURPOSE: Entry point for dependency declaration grammar on classes.
    INPUT/OUTPUT: Accepts dependency class metadata and returns a class decorator.
    SIDE EFFECTS: Writes ``DependencyInfo`` entries into ``cls._depends_info``.
    FAILURES: Raises ``TypeError``/``ValueError`` on contract violations.
    ORDER: Applied at class definition time before coordinator graph build.
    AI-CORE-END
    """
    # ── Validate decorator arguments ──

    if not isinstance(klass, type):
        raise TypeError(
            f"@depends expects a class, got {type(klass).__name__}: {klass!r}. "
            f"Pass a class, not an instance or string."
        )

    if mode is not None and not isinstance(mode, str):
        raise TypeError(
            f"@depends: parameter 'mode' must be str or None, got {type(mode).__name__}.",
        )

    if not isinstance(description, str):
        raise TypeError(f"@depends: parameter 'description' must be a string, " f"got {type(description).__name__}.")

    def decorator(cls: type) -> type:
        """
        Inner decorator applied to the target class.

        Validates:
        1. ``cls`` is a class.
        2. ``klass`` is a subclass of at least one allowed bound (from
           ``DependsIntent[T]`` or ``DependsIntent[A | B | ...]``, else ``object``
           when the class does not inherit ``DependsIntent``).
        3. No duplicate declarations.

        Then appends ``DependencyInfo`` to ``cls._depends_info``.
        """
        # ── Validate target ──
        if not isinstance(cls, type):
            raise TypeError(
                f"@depends can only be applied to a class. " f"Got object of type {type(cls).__name__}: {cls!r}."
            )

        allowed: tuple[type, ...] = cls.get_depends_bounds() if hasattr(cls, "get_depends_bounds") else (object,)
        if not any(issubclass(klass, b) for b in allowed):
            allowed_names = ", ".join(b.__name__ for b in allowed)
            raise TypeError(
                f"@depends({klass.__name__}): class {klass.__name__} "
                f"is not a subclass of any allowed dependency type "
                f"({allowed_names}) for {cls.__name__}."
            )

        validated_mode = _validate_dependency_mode(klass, mode)

        target = cast(Any, cls)

        # ── Create own dependency list ──
        if "_depends_info" not in target.__dict__:
            target._depends_info = list(getattr(target, "_depends_info", []))

        # ── Check for duplicates ──
        if any(info.cls is klass for info in target._depends_info):
            raise ValueError(
                f"@depends({klass.__name__}) already declared for class {cls.__name__}. "
                f"Remove the duplicate decorator."
            )

        # ── Register dependency ──
        target._depends_info.append(
            DependencyInfo(cls=klass, factory=factory, description=description, mode=validated_mode),
        )

        return cls

    return decorator
