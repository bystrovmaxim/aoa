# tests/intents/logging/test_level_validation.py
"""validate_level rejects combined or unknown level masks."""

from __future__ import annotations

import pytest

from action_machine.logging.level import Level, validate_level


def test_validate_level_accepts_single_bits() -> None:
    validate_level(Level.info)
    validate_level(Level.warning)
    validate_level(Level.critical)


def test_validate_level_rejects_combined_mask() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        validate_level(Level.info | Level.warning)
