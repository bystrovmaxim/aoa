# tests/resources/test_connections_typed_dict.py
"""
Tests for Connections — base TypedDict for the connections dict.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Connections is the base TypedDict describing the dict passed into aspects as
connections. It defines the standard key 'connection' (covers most cases). For
complex setups, developers can subclass with extra keys.

TypedDict is a static contract for the IDE and mypy. At runtime connections is a
plain dict; ActionMachine still validates contents dynamically.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS COVERED
═══════════════════════════════════════════════════════════════════════════════

- Building a dict with key 'connection' satisfies the type contract.
- Dicts with other keys are also allowed (total=False).
- Values are BaseResourceManager instances.
"""

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.connections_typed_dict import Connections


class DummyResourceManager(BaseResourceManager):
    """Stub resource manager for tests."""
    def get_wrapper_class(self):
        return None


def test_connections_typeddict() -> None:
    """
    Connections TypedDict accepts key 'connection' with a BaseResourceManager value.
    """
    # Arrange — stub instance
    res = DummyResourceManager()

    # Act — dict matching Connections
    conn: Connections = {"connection": res}

    # Assert — key access works
    assert conn["connection"] is res
