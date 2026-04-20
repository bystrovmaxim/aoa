# src/action_machine/domain/lifecycle.py
"""
Declarative finite-state **lifecycle** templates and typed **runtime** state for entities.

`Lifecycle` serves two roles: a **template** built with a fluent import-time API
(state graph), and a **specialized subclass** whose instances hold the current
state key on each entity. ``GraphCoordinator`` validates graph rules at
**build** time; instances enforce valid keys and transitions at **runtime**.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Model business state machines next to entity fields so transitions stay explicit,
testable, and documented. Frozen entities update lifecycles by replacing the
field value (`transition` returns a new instance), not by mutating in place.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Fluent template construction (`.state().to().initial()` / `intermediate` / `final`).
    `StateInfo` metadata, `StateType` classification, instance API (`current_state`,
    `can_transition`, `transition`).
    Strict validation while building templates (keys, display names, final states
    without transitions).

**Out of scope**
    The eight global integrity rules (exactly one initial set semantics, reachability,
    etc.) — enforced by **inspectors** when ``GraphCoordinator`` **builds**, not in
    this module’s fluent builder alone.
    Persistence, timers, and side effects on transition — application code.
    Automatic persistence when transitioning — callers use `model_copy` on the entity.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    import-time fluent chain          specialized subclass
    Lifecycle().state(...).to(...).initial()
              │
              └── stored as _template on OrderLifecycle(Lifecycle)
                        │
                        ├── coordinator.build()  → validates full graph (8 rules)
                        │
                        └── runtime: OrderLifecycle("new")  → instance with current_state

    entity field (pydantic)     frozen update path
    lifecycle: OrderLifecycle   new_lc = entity.lifecycle.transition("confirmed")
                                entity.model_copy(update={"lifecycle": new_lc})

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

Encoding the graph in a fluent DSL keeps the FSM colocated with the domain model
and avoids scattering stringly state checks. Splitting **template** (class body)
from **instance** (field value) matches pydantic’s model: the template is shared
metadata; each entity row holds one current key. Immutability aligns with
`BaseEntity`: transitions return new lifecycle objects suitable for `model_copy`.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import / class body**: `_template = Lifecycle().state(...)...` runs; template
  graph is fixed.
- **Coordinator `build()`**: structural validation of lifecycles on entities.
- **Runtime**: constructing `OrderLifecycle("new")`, `can_transition`, `transition`.

"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import cast

# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class InvalidStateError(ValueError):
    """
    ``current_state`` is not a declared state key on this lifecycle class.

    Raised when constructing an instance with a key that does not appear in
    the subclass ``_template`` graph.

    Attributes:
        state_key: Value passed to the constructor.
        lifecycle_class: Specialized lifecycle class name.
        valid_states: Declared state keys from the template.
    """

    def __init__(
        self,
        state_key: str,
        lifecycle_class: str,
        valid_states: set[str],
    ) -> None:
        self.state_key = state_key
        self.lifecycle_class = lifecycle_class
        self.valid_states = valid_states
        sorted_states = ", ".join(sorted(valid_states))
        super().__init__(
            f"State '{state_key}' is not defined on {lifecycle_class}. "
            f"Valid states: {sorted_states}."
        )


class InvalidTransitionError(ValueError):
    """
    Disallowed transition for the current state.

    Raised by ``transition()`` when ``target`` is not in the current state’s
    outgoing transition set.

    Attributes:
        current_state: Current state key.
        target_state: Requested target key.
        lifecycle_class: Specialized lifecycle class name.
        valid_targets: Allowed targets from the current state (possibly empty).
    """

    def __init__(
        self,
        current_state: str,
        target_state: str,
        lifecycle_class: str,
        valid_targets: set[str],
    ) -> None:
        self.current_state = current_state
        self.target_state = target_state
        self.lifecycle_class = lifecycle_class
        self.valid_targets = valid_targets
        sorted_targets = ", ".join(sorted(valid_targets)) if valid_targets else "(no transitions)"
        super().__init__(
            f"Transition '{current_state}' → '{target_state}' is not allowed "
            f"on {lifecycle_class}. "
            f"Allowed transitions from '{current_state}': {sorted_targets}."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STATE CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════


class StateType(Enum):
    """
    How a state participates in the lifecycle graph.

    Exactly one of these applies per state — invalid combinations are rejected
    at template build time via distinct builder methods.

    Values:
        INITIAL: Entry state(s) for new business objects.
        INTERMEDIATE: Non-terminal states with at least one outgoing edge.
        FINAL: Terminal states with no outgoing edges.
    """

    INITIAL = "initial"
    INTERMEDIATE = "intermediate"
    FINAL = "final"


# ═══════════════════════════════════════════════════════════════════════════════
# STATE METADATA
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class StateInfo:
    """
    Immutable metadata for one state in a template.

    Attributes:
        key: Stable machine key (e.g. ``"new"``, ``"confirmed"``).
        display_name: Human-readable label for UI and diagrams.
        state_type: ``INITIAL``, ``INTERMEDIATE``, or ``FINAL``.
        transitions: Frozen set of target state keys allowed from this state.
    """

    key: str
    display_name: str
    state_type: StateType
    transitions: frozenset[str]

    @property
    def is_initial(self) -> bool:
        """True if this state is classified as initial."""
        return self.state_type == StateType.INITIAL

    @property
    def is_final(self) -> bool:
        """True if this state is classified as final."""
        return self.state_type == StateType.FINAL

    @property
    def is_intermediate(self) -> bool:
        """True if this state is classified as intermediate."""
        return self.state_type == StateType.INTERMEDIATE


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE-STATE BUILDER (FLUENT)
# ═══════════════════════════════════════════════════════════════════════════════


class _StateBuilder:
    """
    Internal fluent builder for one state in a ``Lifecycle`` template.

    Created by ``Lifecycle.state()``; not part of the public surface.

    Attributes:
        _lifecycle: Parent template under construction.
        _key: State key.
        _display_name: Display label.
        _transitions: Target keys added via ``.to()``.
        _completed: Set after ``.initial()`` / ``.intermediate()`` / ``.final()``.
    """

    def __init__(self, lifecycle: Lifecycle, key: str, display_name: str) -> None:
        self._lifecycle = lifecycle
        self._key = key
        self._display_name = display_name
        self._transitions: set[str] = set()
        self._completed = False

    def to(self, *target_keys: str) -> _StateBuilder:
        """
        Add allowed transition targets from this state.

        Forward references to not-yet-declared states are allowed. May be called
        multiple times.

        Args:
            *target_keys: Target state keys.

        Returns:
            ``self`` for chaining.

        Raises:
            TypeError: A target key is not a ``str``.
            ValueError: A target key is empty or whitespace-only.
        """
        for key in target_keys:
            if not isinstance(key, str):
                raise TypeError(
                    f"Transition target key must be str, got {type(key).__name__}: {key!r}."
                )
            if not key.strip():
                raise ValueError(
                    f"Transition target key cannot be empty or whitespace-only "
                    f"in state '{self._key}'."
                )
            self._transitions.add(key)
        return self

    def initial(self) -> Lifecycle:
        """Mark this state as ``INITIAL`` and register it on the template."""
        return self._finalize(StateType.INITIAL)

    def intermediate(self) -> Lifecycle:
        """Mark this state as ``INTERMEDIATE`` and register it on the template."""
        return self._finalize(StateType.INTERMEDIATE)

    def final(self) -> Lifecycle:
        """
        Mark this state as ``FINAL`` and register it on the template.

        Raises:
            ValueError: If any outgoing transitions were added (final states
                must have an empty transition set).
        """
        if self._transitions:
            raise ValueError(
                f"Final state '{self._key}' cannot have outgoing transitions, "
                f"but these were set: {sorted(self._transitions)}"
            )
        return self._finalize(StateType.FINAL)

    def _finalize(self, state_type: StateType) -> Lifecycle:
        """
        Close this state and append it to the parent template.

        Raises:
            RuntimeError: If ``.initial()`` / ``.intermediate()`` / ``.final()``
                was already called on this builder.
        """
        if self._completed:
            raise RuntimeError(
                f"State '{self._key}' is already complete. "
                f"Do not call .initial(), .intermediate(), or .final() twice."
            )
        self._completed = True
        state_info = StateInfo(
            key=self._key,
            display_name=self._display_name,
            state_type=state_type,
            transitions=frozenset(self._transitions),
        )
        self._lifecycle._register_state(state_info)
        return self._lifecycle

    @property
    def is_completed(self) -> bool:
        """True after the state has been finalized."""
        return self._completed


# ═══════════════════════════════════════════════════════════════════════════════
# LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════


class Lifecycle:
    """
AI-CORE-BEGIN
    ROLE: Unified template/instance lifecycle object.
    CONTRACT: Template mode defines graph; instance mode enforces legal transitions.
    INVARIANTS: ``transition()`` returns a new object and never mutates current instance.
    AI-CORE-END
"""

    _template: Lifecycle | None = None

    def __init__(self, current_state: str | None = None) -> None:
        """
        Create a template (no argument) or an instance (with ``current_state``).

        Args:
            current_state: If set, build a runtime instance validated against
                the subclass ``_template``. If ``None``, start an empty template
                for fluent construction.

        Raises:
            TypeError: Specialized subclass has no ``_template`` but a state
                was requested.
            InvalidStateError: ``current_state`` is not a key in ``_template``.
        """
        self._states: dict[str, StateInfo] = {}
        self._current_state: str | None = None
        self._current_builder: _StateBuilder | None = None

        if current_state is not None:
            template = self._get_template()
            if template is None:
                raise TypeError(
                    f"{self.__class__.__name__} has no _template. "
                    f"Define _template on the subclass, or use the fluent "
                    f".state().to()… chain to build a template."
                )
            valid_states = set(template._states.keys())
            if current_state not in valid_states:
                raise InvalidStateError(
                    state_key=current_state,
                    lifecycle_class=self.__class__.__name__,
                    valid_states=valid_states,
                )
            self._states = dict(template._states)
            self._current_state = current_state

    @classmethod
    def _get_template(cls) -> Lifecycle | None:
        """
        Resolve ``_template`` from the class MRO.

        Returns:
            The first ``Lifecycle`` template found on ``cls`` or its bases, or
            ``None``.
        """
        for klass in cls.__mro__:
            template = klass.__dict__.get("_template")
            if template is not None and isinstance(template, Lifecycle):
                return cast(Lifecycle, template)
        return None

    # ─────────────────────────────────────────────────────────────────────
    # Fluent API (template construction)
    # ─────────────────────────────────────────────────────────────────────

    def state(self, key: str, display_name: str) -> _StateBuilder:
        """
        Declare a new state on this template.

        Args:
            key: Unique state key.
            display_name: Non-empty label for UI and exports.

        Returns:
            ``_StateBuilder`` for ``.to()`` and classification.

        Raises:
            RuntimeError: Previous state was not finalized.
            TypeError: ``key`` or ``display_name`` is not a ``str``.
            ValueError: Empty / whitespace-only ``key`` or ``display_name``, or
                duplicate ``key``.
        """
        if self._current_builder is not None and not self._current_builder.is_completed:
            raise RuntimeError(
                f"State '{self._current_builder._key}' is not complete. "
                f"Call .initial(), .intermediate(), or .final() "
                f"before declaring a new state '{key}'."
            )

        if not isinstance(key, str):
            raise TypeError(
                f"State key must be str, got {type(key).__name__}: {key!r}."
            )
        if not key.strip():
            raise ValueError("State key cannot be empty or whitespace-only.")

        if not isinstance(display_name, str):
            raise TypeError(
                f"State display name must be str, got {type(display_name).__name__}: {display_name!r}."
            )
        if not display_name.strip():
            raise ValueError(
                f"State display name for '{key}' cannot be empty or whitespace-only."
            )

        if key in self._states:
            raise ValueError(
                f"State '{key}' is already defined."
            )

        builder = _StateBuilder(self, key, display_name)
        self._current_builder = builder
        return builder

    def _register_state(self, state_info: StateInfo) -> None:
        """Register a finalized ``StateInfo`` (used by ``_StateBuilder``)."""
        self._states[state_info.key] = state_info

    # ─────────────────────────────────────────────────────────────────────
    # Instance API (current state)
    # ─────────────────────────────────────────────────────────────────────

    @property
    def current_state(self) -> str:
        """
        Current state key for this instance.

        Raises:
            RuntimeError: This object is a template without ``current_state``.
        """
        if self._current_state is None:
            raise RuntimeError(
                f"{self.__class__.__name__} is a template, not an instance. "
                f"current_state is only available on instances such as "
                f"{self.__class__.__name__}('state_key')."
            )
        return self._current_state

    @property
    def current_state_info(self) -> StateInfo:
        """``StateInfo`` for ``current_state``."""
        return self._states[self.current_state]

    @property
    def available_transitions(self) -> set[str]:
        """Set of state keys reachable in one step from ``current_state``."""
        return set(self.current_state_info.transitions)

    @property
    def is_initial(self) -> bool:
        """True if the current state is initial."""
        return self.current_state_info.is_initial

    @property
    def is_final(self) -> bool:
        """True if the current state is final."""
        return self.current_state_info.is_final

    def can_transition(self, target: str) -> bool:
        """
        Whether ``target`` is an allowed successor of ``current_state``.

        Args:
            target: Candidate next state key.

        Returns:
            ``True`` if the template allows an edge from the current state to
            ``target``.
        """
        return target in self.current_state_info.transitions

    def transition(self, target: str) -> Lifecycle:
        """
        Return a **new** instance of this class with ``current_state == target``.

        Does not mutate ``self``. Typical entity update::

            new_lc = entity.lifecycle.transition("confirmed")
            updated = entity.model_copy(update={"lifecycle": new_lc})

        Args:
            target: Destination state key.

        Returns:
            New instance of the same specialized class.

        Raises:
            InvalidTransitionError: Edge not present in the template.
        """
        if not self.can_transition(target):
            raise InvalidTransitionError(
                current_state=self.current_state,
                target_state=target,
                lifecycle_class=self.__class__.__name__,
                valid_targets=self.available_transitions,
            )
        return self.__class__(target)

    # ─────────────────────────────────────────────────────────────────────
    # Template introspection (coordinator / tooling)
    # ─────────────────────────────────────────────────────────────────────

    def get_states(self) -> dict[str, StateInfo]:
        """
        Copy of all ``StateInfo`` entries in this template.

        Returns:
            ``dict`` mapping state key → ``StateInfo``.
        """
        return dict(self._states)

    def get_initial_keys(self) -> set[str]:
        """Keys of all states marked ``INITIAL``."""
        return {
            key for key, info in self._states.items()
            if info.state_type == StateType.INITIAL
        }

    def get_final_keys(self) -> set[str]:
        """Keys of all states marked ``FINAL``."""
        return {
            key for key, info in self._states.items()
            if info.state_type == StateType.FINAL
        }

    def get_transitions(self) -> dict[str, set[str]]:
        """
        Adjacency map for the template.

        Returns:
            Map ``source_key → set(target_keys)``.
        """
        return {
            key: set(info.transitions)
            for key, info in self._states.items()
        }

    def has_state(self, key: str) -> bool:
        """Return whether ``key`` exists in this template."""
        return key in self._states

    def __repr__(self) -> str:
        if self._current_state is not None:
            return (
                f"{self.__class__.__name__}('{self._current_state}')"
            )
        return (
            f"Lifecycle(states={len(self._states)}, "
            f"initial={len(self.get_initial_keys())}, "
            f"final={len(self.get_final_keys())})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Lifecycle):
            return NotImplemented
        return (
            type(self) is type(other)
            and self._current_state == other._current_state
        )

    def __hash__(self) -> int:
        return hash((type(self), self._current_state))
