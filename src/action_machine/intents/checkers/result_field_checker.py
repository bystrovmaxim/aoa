# src/action_machine/intents/checkers/result_field_checker.py
"""
Abstract base checker for aspect-result fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Defines shared checker contract for all result-field validators. Each concrete
checker (``FieldStringChecker``, ``FieldIntChecker``, etc.) inherits from
:class:`BaseFieldChecker` and implements ``_check_type_and_constraints``.

Runtime (``ActionProductMachine._apply_checkers``) instantiates checkers from
snapshot metadata and calls ``checker.check(result_dict)``.

═══════════════════════════════════════════════════════════════════════════════
NAMING INVARIANT
═══════════════════════════════════════════════════════════════════════════════

Every class inheriting ``BaseFieldChecker`` (directly or indirectly) must
end with ``"Checker"`` suffix. This invariant is enforced in
``__init_subclass__`` at class definition time. Violations raise
``NamingSuffixError``.

Примеры:
    class FieldStringChecker(BaseFieldChecker):  # OK
    class FieldIntChecker(BaseFieldChecker):     # OK
    class MyCustomChecker(BaseFieldChecker):      # OK
    class StringValidator(BaseFieldChecker):      # NamingSuffixError

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``result_*`` decorators write checker metadata to method attribute
``_checker_meta``. Inspector/builder flow collects this metadata into checker
snapshots.

    @result_* decorators
            |
            v
    method._checker_meta entries
            |
            v
    CheckerIntentInspector snapshot
            |
            v
    runtime checker instance creation
            |
            v
    checker.check(result_dict)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Constructor contract: ``field_name`` + ``required``.
- Subclasses may add extra validation parameters via constructor.
- ``check()`` enforces required/non-null policy before type constraints.
- Subclasses must implement ``_check_type_and_constraints``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    # Runtime creates checker from snapshot metadata and calls check():
    checker = FieldStringChecker("txn_id", required=True)
    checker.check({"txn_id": "abc"})  # OK
    checker.check({})                  # ValidationFieldError

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``NamingSuffixError`` for subclasses without ``Checker`` suffix.
- ``ValidationFieldError`` when required field is missing/None or constraints fail.
- This base class validates structure only; concrete semantics belong to subclasses.


AI-CORE-BEGIN
ROLE: Base checker contract module.
CONTRACT: Define shared required-field flow and extension hook for concrete checkers.
INVARIANTS: Naming suffix enforcement and deterministic checker lifecycle.
FLOW: metadata -> snapshot -> runtime instantiation -> check().
AI-CORE-END
"""

from abc import ABC, abstractmethod
from typing import Any

from action_machine.model.exceptions import NamingSuffixError, ValidationFieldError

# Required suffix for all BaseFieldChecker subclasses.
_REQUIRED_SUFFIX = "Checker"


class BaseFieldChecker(ABC):
    """
    Abstract base class for all aspect-result field checkers.

    Subclasses implement concrete type/constraint checks while this class
    handles required/non-null flow and naming policy. Cannot be instantiated
    directly.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Enforce ``Checker`` suffix for every subclass.

        Args:
            **kwargs: forwarded to ``type.__init_subclass__``.

        Raises:
            NamingSuffixError: if class name lacks ``Checker`` suffix.
        """
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' inherits BaseFieldChecker but "
                f"does not end with suffix '{_REQUIRED_SUFFIX}'. "
                f"Rename it to '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

    def __init__(self, field_name: str, required: bool = True) -> None:
        """
        Initialize checker base parameters.

        Args:
            field_name: field name in result dictionary.
            required: whether field is required. Default ``True``.
        """
        self.field_name = field_name
        self.required = required

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Return subclass-specific parameters for snapshot serialization.

        Returns:
            Dictionary with extra checker params.
        """
        return {}

    def _check_required(self, result: dict[str, Any]) -> Any | None:
        """
        Validate required/non-null field presence.

        Args:
            result: aspect result dictionary.

        Returns:
            Field value when present and non-None.
            ``None`` when optional field is missing.

        Raises:
            ValidationFieldError: if required field is missing or ``None``.
        """
        value = result.get(self.field_name)

        if value is None:
            if self.required:
                raise ValidationFieldError(
                    f"Missing required parameter: '{self.field_name}'",
                    field=self.field_name,
                )
            return None

        return value

    def check(self, result: dict[str, Any]) -> None:
        """
        Run full validation for one field in aspect result.

        Executes required/non-null validation first, then delegates type and
        constraint checks to subclass hook.

        Args:
            result: aspect result dictionary.

        Raises:
            ValidationFieldError: on any validation failure.
        """
        value = self._check_required(result)
        if value is None:
            return
        self._check_type_and_constraints(value)

    @abstractmethod
    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Validate type and constraints for a non-None value.

        Args:
            value: field value (guaranteed non-None).

        Raises:
            ValidationFieldError: if value violates checker rules.
        """
        ...
