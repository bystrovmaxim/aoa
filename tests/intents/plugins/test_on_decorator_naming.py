# tests/intents/plugins/test_on_decorator_naming.py
"""
Naming invariant: methods decorated with ``@on`` must start with the ``on_`` prefix.

Violations raise ``NamingPrefixError``.
"""

import pytest

from action_machine.exceptions import NamingPrefixError


class TestPluginOnPrefix:
    """Plugin methods with @on must start with 'on_'."""

    def test_correct_prefix_passes(self) -> None:
        """Name 'on_track_finish' — decorator applies."""
        from action_machine.intents.on.on_decorator import on
        from action_machine.plugin.events import GlobalFinishEvent

        @on(GlobalFinishEvent)
        async def on_track_finish(self, state, event, log):
            return state

        assert hasattr(on_track_finish, "_on_subscriptions")

    def test_missing_prefix_raises(self) -> None:
        """Name 'track_finish' without 'on_' → NamingPrefixError."""
        from action_machine.intents.on.on_decorator import on
        from action_machine.plugin.events import GlobalFinishEvent

        with pytest.raises(NamingPrefixError, match="on_"):
            @on(GlobalFinishEvent)
            async def track_finish(self, state, event, log):
                return state

    def test_wrong_prefix_raises(self) -> None:
        """Name 'handle_track_finish' → NamingPrefixError (does not start with 'on_')."""
        from action_machine.intents.on.on_decorator import on
        from action_machine.plugin.events import GlobalFinishEvent

        with pytest.raises(NamingPrefixError, match="on_"):
            @on(GlobalFinishEvent)
            async def handle_track_finish(self, state, event, log):
                return state
