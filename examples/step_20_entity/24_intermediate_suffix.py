"""Check an intermediate class too.

An intermediate class is part of the same hierarchy. ABC does not exempt its name from the kind suffix.

Run: uv run python examples/step_20_entity/24_intermediate_suffix.py
"""

from abc import ABC

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError

try:
    class BaseDocumentEntity(BaseCoreEntity, ABC):
        """Attempt an intermediate class without its kind suffix."""
except NamingSuffixError as exc:
    print(type(exc).__name__ + ": " + str(exc))
else:
    raise AssertionError("The invalid declaration must be refused")
