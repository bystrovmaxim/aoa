# tests/intents/logging/test_channel_validation.py
"""Error paths for ``validate_channels`` (non-empty mask, known bits only)."""

from __future__ import annotations

import pytest

from aoa.action_machine.logging.channel import Channel, validate_channels


def test_validate_channels_rejects_non_int_like() -> None:
    with pytest.raises(TypeError, match="channels must be Channel"):
        validate_channels("debug")  # type: ignore[arg-type]


def test_validate_channels_rejects_empty_mask() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_channels(Channel(0))


def test_validate_channels_rejects_unknown_bits() -> None:
    with pytest.raises(ValueError, match="unknown bits"):
        validate_channels(Channel(32))
