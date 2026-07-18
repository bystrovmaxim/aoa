"""
Tests for route uniqueness/shadowing (issue #130, chapter 3.5, implementation task 5).

Two cases, deliberately handled differently:

- An exact ``(method, path)`` duplicate is not an error — a dev-time
  ``UserWarning`` at registration time, first-wins in the manifest (see
  ``test_manifest.py``'s ``TestExactDuplicateIsFirstWins``).
- Two *different* path templates that could match the same real URL
  (``/users/me`` alongside ``/users/{id}``) fail the build with
  ``RouteShadowError`` — checked once ``build()`` knows every route.

Drives the real ``FastApiAdapter`` registration/``build()`` path; only
``auth_coordinator`` is mocked, per this package's adapter testing contract.
"""

from __future__ import annotations

import warnings
from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter
from aoa.fastapi.route_shadow_error import RouteShadowError

from .support import CancelOrderAction, PingAction, SimpleAction


def _adapter() -> FastApiAdapter:
    return FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=AsyncMock())


class TestExactDuplicateWarns:
    """A second registration of the same (method, path) warns but does not raise."""

    def test_registering_the_same_operation_twice_warns(self) -> None:
        adapter = _adapter()
        adapter.get("/a", PingAction)

        with pytest.warns(UserWarning, match="GET '/a'"):
            adapter.get("/a", SimpleAction)

    def test_the_app_still_builds_after_the_warning(self) -> None:
        adapter = _adapter()
        adapter.get("/a", PingAction)
        with pytest.warns(UserWarning):
            adapter.get("/a", SimpleAction)

        adapter.build()  # must not raise

    def test_different_methods_on_the_same_path_do_not_warn(self) -> None:
        """(method, path) is the identity — same path, different method, is not a duplicate."""
        adapter = _adapter()
        adapter.get("/a", PingAction)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            adapter.post("/a", SimpleAction)  # must not raise/warn


class TestOverlappingTemplatesFailTheBuild:
    """Two different templates, same method, that could match one URL fail build()."""

    def test_static_segment_shadowed_by_a_param_raises(self) -> None:
        adapter = _adapter()
        adapter.get("/users/me", PingAction)
        adapter.get("/users/{id}", SimpleAction)

        with pytest.raises(RouteShadowError):
            adapter.build()

    def test_two_differently_named_params_raise(self) -> None:
        adapter = _adapter()
        adapter.get("/users/{id}", PingAction)
        adapter.get("/users/{name}", SimpleAction)

        with pytest.raises(RouteShadowError):
            adapter.build()

    def test_different_methods_do_not_conflict(self) -> None:
        adapter = _adapter()
        adapter.get("/users/me", PingAction)
        adapter.post("/users/{id}", CancelOrderAction)

        adapter.build()  # must not raise: different methods never overlap

    def test_disjoint_literal_paths_do_not_conflict(self) -> None:
        adapter = _adapter()
        adapter.get("/a", PingAction)
        adapter.get("/b", SimpleAction)

        adapter.build()  # must not raise

    def test_int_converter_literal_mismatch_does_not_conflict(self) -> None:
        """"/items/latest" cannot satisfy an int converter — not a real collision."""
        adapter = _adapter()
        adapter.get("/items/{id:int}", PingAction)
        adapter.get("/items/latest", SimpleAction)

        adapter.build()  # must not raise

    def test_int_converter_literal_match_does_conflict(self) -> None:
        """"/items/42" *does* satisfy an int converter — a real collision."""
        adapter = _adapter()
        adapter.get("/items/{id:int}", PingAction)
        adapter.get("/items/42", SimpleAction)

        with pytest.raises(RouteShadowError):
            adapter.build()

    def test_greedy_path_converter_absorbs_extra_segments(self) -> None:
        """"{rest:path}" swallows one or more trailing segments, slashes included."""
        adapter = _adapter()
        adapter.get("/files/{rest:path}", PingAction)
        adapter.get("/files/a/b", SimpleAction)

        with pytest.raises(RouteShadowError):
            adapter.build()

    def test_exact_duplicate_is_not_treated_as_shadowing(self) -> None:
        """An identical template twice is the first-wins case, not RouteShadowError."""
        adapter = _adapter()
        adapter.get("/a", PingAction)
        with pytest.warns(UserWarning):
            adapter.get("/a", SimpleAction)

        adapter.build()  # RouteShadowError must not fire for this case
