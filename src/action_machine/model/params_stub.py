# src/action_machine/model/params_stub.py
"""
``ParamsStub`` — minimal ``BaseParams`` subclass for tests and tooling.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Real actions must bind concrete parameter schemas (subclasses of ``BaseParams``).
Graph inspectors intentionally **omit** the abstract root ``BaseParams`` from the
interchange walk, so ``BaseAction[BaseParams, …]`` yields dangling ``params`` edges.
Use ``ParamsStub`` (or another real subclass) as the generic parameter when a
placeholder input contract is enough (unit tests, meta validation, naming checks).
"""

from __future__ import annotations

from action_machine.model.base_params import BaseParams


class ParamsStub(BaseParams):
    """
    AI-CORE-BEGIN
    ROLE: Canonical empty params type for non-production ``BaseAction`` bindings.
    CONTRACT: Strict subclass of ``BaseParams`` so params-axis graph nodes materialize.
    INVARIANTS: No fields; frozen/forbid inherited from ``BaseParams``.
    AI-CORE-END
    """

    pass
