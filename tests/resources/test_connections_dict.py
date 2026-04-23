# tests/resources/test_connections_dict.py
"""
Tests for typing the ``connections`` mapping as ``dict[str, BaseResource]``.

Aspects and ``machine.run(..., connections=...)`` accept a plain dict at runtime;
this module checks that a typical payload type-checks as the shared annotation.
"""

from action_machine.resources.base_resource import BaseResource


class DummyResourceManager(BaseResource):
    """Stub resource manager for tests."""

    def get_wrapper_class(self):
        return None


def test_connections_dict_annotation() -> None:
    """A dict with key 'connection' satisfies dict[str, BaseResource]."""
    res = DummyResourceManager()
    conn: dict[str, BaseResource] = {"connection": res}
    assert conn["connection"] is res
