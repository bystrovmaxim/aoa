# src/action_machine/auth/role_class_inspector.py
"""
Graph inspector for typed role topology (``includes``, ``requires_role``, names).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materialize ``role_class`` nodes for every ``BaseRole`` subtype (except
``BaseRole`` itself) that participates in the static graph, connect them with
structural ``role_includes`` edges for ``includes``, and attach informational
``requires_role`` edges toward existing action ``role`` facet nodes. Run
graph-level validations that belong to role topology rather than lifecycle
scratch.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Every graphed role must carry ``@role_mode`` (``_role_mode_info`` present).
- **Unique** stable ``name`` among all graphed ``BaseRole`` subclasses.
- **No** ``RoleMode.UNUSED`` role in the transitive ``includes`` closure of any
  graphed role.
- **No** ``RoleMode.UNUSED`` ``BaseRole`` ancestor (other than ``BaseRole``) in
  the MRO of a graphed role.
- Structural ``role_includes`` edges participate in coordinator acyclicity
  (cycles raise ``CyclicDependencyError`` from ``GateCoordinator.build()``).
- **Does not** re-validate non-empty ``name`` / ``description`` strings (handled
  in ``BaseRole.__init_subclass__``). **Does not** duplicate lifecycle facet
  work (see ``RoleModeGateHostInspector``).

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseRole subclasses (with @role_mode)
          │
          ├── includes → structural edges ``role_includes`` → included role_class
          │
          └── scan RoleGateHost + _role_info → informational ``requires_role``
                    → existing ``role:<Action>`` nodes

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: ``ManagerRole`` includes ``ViewerRole`` → one structural edge
``ManagerRole`` → ``ViewerRole``.

Edge case: two unrelated classes both use ``name = "dup"`` →
``InvalidGraphError`` at ``build()``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``InvalidGraphError``: duplicate ``name``, ``UNUSED`` in ``includes`` / MRO,
  missing ``@role_mode``, broken ``requires_role`` target (missing action
  ``role`` node — should not happen when ``RoleGateHostInspector`` is
  registered).
- Cycle detection: delegated to ``GateCoordinator`` structural pass.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role-class topology inspector.
CONTRACT: ``role_class`` nodes; ``role_includes`` + ``requires_role`` edges.
INVARIANTS: Unique name; no UNUSED in includes/MRO; acyclic includes via graph.
FLOW: collect subclasses → validate → FacetPayload per role type.
FAILURES: InvalidGraphError on broken topology.
EXTENSION POINTS: Align new cross-facet edges with ``RoleGateHostInspector``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.auth.base_role import BaseRole
from action_machine.auth.constants import ROLE_ANY, ROLE_NONE
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.auth.role_mode import RoleMode, get_declared_role_mode
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.exceptions import InvalidGraphError
from action_machine.metadata.payload import EdgeInfo, FacetPayload


def _all_base_role_types() -> tuple[type[BaseRole], ...]:
    return tuple(
        c
        for c in BaseGateHostInspector._collect_subclasses(BaseRole)
        if c is not BaseRole
    )


def _assert_unique_role_name(cls: type[BaseRole]) -> None:
    my_name = cls.name
    for other in _all_base_role_types():
        if other is cls:
            continue
        if other.name == my_name:
            raise InvalidGraphError(
                f"Duplicate role name {my_name!r}: {cls.__qualname__} and "
                f"{other.__qualname__}. "
                f"Stable role names must be unique across BaseRole subclasses.",
            )


def _assert_includes_no_unused(root: type[BaseRole]) -> None:
    stack: list[type[BaseRole]] = list(root.includes)
    seen: set[type[BaseRole]] = set()
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if get_declared_role_mode(cur) is RoleMode.UNUSED:
            raise InvalidGraphError(
                f"Role {root.__qualname__!r} includes {cur.__qualname__!r}, "
                f"which is RoleMode.UNUSED. Remove the inclusion or revive the role.",
            )
        stack.extend(cur.includes)


def _assert_mro_no_unused_base(cls: type[BaseRole]) -> None:
    for base in cls.__mro__[1:]:
        if base is BaseRole or base is object:
            continue
        if not (isinstance(base, type) and issubclass(base, BaseRole)):
            continue
        try:
            mode = get_declared_role_mode(base)
        except TypeError:
            continue
        if mode is RoleMode.UNUSED:
            raise InvalidGraphError(
                f"Role {cls.__qualname__!r} inherits from {base.__qualname__!r}, "
                f"which is RoleMode.UNUSED.",
            )


def _iter_action_classes_with_role_spec() -> tuple[type, ...]:
    return tuple(BaseGateHostInspector._collect_subclasses(RoleGateHost))


def _required_role_types_from_spec(spec: object) -> tuple[type[BaseRole], ...]:
    if spec in (ROLE_NONE, ROLE_ANY):
        return ()
    if isinstance(spec, type) and issubclass(spec, BaseRole):
        return (spec,)
    if isinstance(spec, tuple):
        return tuple(r for r in spec if isinstance(r, type) and issubclass(r, BaseRole))
    return ()


class RoleClassInspector(BaseGateHostInspector):
    """
    Emits ``role_class`` topology: ``includes`` structure and action requirements.
    """

    _target_mixin: type = BaseRole

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed snapshot for a ``role_class`` graph node."""

        class_ref: type[BaseRole]

        def to_facet_payload(self) -> FacetPayload:
            return FacetPayload(
                node_type="role_class",
                node_name=RoleClassInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=RoleClassInspector._make_meta(
                    name=self.class_ref.name,
                    description=self.class_ref.description,
                ),
                edges=RoleClassInspector._edges_for_role(self.class_ref),
            )

        @classmethod
        def from_target(cls, target_cls: type[BaseRole]) -> RoleClassInspector.Snapshot:
            return cls(class_ref=target_cls)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return list(cls._collect_subclasses(cls._target_mixin))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        if target_cls is BaseRole:
            return None
        if not issubclass(target_cls, BaseRole):
            return None
        role_cls: type[BaseRole] = target_cls
        if not isinstance(getattr(role_cls, "_role_mode_info", None), dict):
            raise InvalidGraphError(
                f"Role class {target_cls.__qualname__} has no @role_mode metadata "
                f"(_role_mode_info). Every BaseRole subclass in the graph must "
                f"declare a lifecycle mode.",
            )
        _assert_unique_role_name(role_cls)
        _assert_includes_no_unused(role_cls)
        _assert_mro_no_unused_base(role_cls)
        return cls._build_payload(role_cls)

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> RoleClassInspector.Snapshot | None:
        if target_cls is BaseRole:
            return None
        if not issubclass(target_cls, BaseRole):
            return None
        role_cls: type[BaseRole] = target_cls
        if not isinstance(getattr(role_cls, "_role_mode_info", None), dict):
            return None
        return cls.Snapshot.from_target(role_cls)

    @classmethod
    def facet_snapshot_storage_key(
        cls, target_cls: type, payload: FacetPayload,
    ) -> str:
        return "role_class"

    @classmethod
    def _build_payload(cls, target_cls: type[BaseRole]) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

    @classmethod
    def _edges_for_role(cls, target_cls: type[BaseRole]) -> tuple[EdgeInfo, ...]:
        inc_edges = tuple(
            cls._make_edge(
                target_node_type="role_class",
                target_cls=inc,
                edge_type="role_includes",
                is_structural=True,
            )
            for inc in target_cls.includes
        )
        req_edges: list[EdgeInfo] = []
        for action_cls in _iter_action_classes_with_role_spec():
            info = getattr(action_cls, "_role_info", None)
            if not isinstance(info, dict):
                continue
            spec = info.get("spec")
            reqs = _required_role_types_from_spec(spec)
            if target_cls not in reqs:
                continue
            req_edges.append(
                cls._make_edge(
                    target_node_type="role",
                    target_cls=action_cls,
                    edge_type="requires_role",
                    is_structural=False,
                    edge_meta=cls._make_meta(required_role=target_cls.__qualname__),
                ),
            )
        return inc_edges + tuple(req_edges)
