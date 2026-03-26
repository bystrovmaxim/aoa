"""Logging scope – stores location information in the pipeline."""

from typing import Any

from action_machine.core.readable_mixin import ReadableMixin


class LogScope(ReadableMixin):
    """
    Logging scope – stores information about the location in the pipeline.

    Values are passed as kwargs and become instance attributes.
    Inherits from ReadableMixin, therefore supports dict-like access:
    - scope['action'] returns the value of the action attribute.
    - scope.get('aspect') etc.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the scope with keyword arguments.

        Args:
            **kwargs: Arbitrary keyword arguments that become attributes.
        """
        # Set all passed keys as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        # Save the order of keys for as_dotpath
        self._key_order = list(kwargs.keys())
        self._cached_path: str | None = None

    def as_dotpath(self) -> str:
        """
        Return all values joined by dots, in the order of _key_order.
        Empty values are skipped. The result is cached.
        """
        if self._cached_path is None:
            values = []
            for key in self._key_order:
                val = getattr(self, key, None)
                if val:   # skip empty strings and None
                    values.append(str(val))
            self._cached_path = ".".join(values)
        return self._cached_path

    def to_dict(self) -> dict[str, str]:
        """
        Return a dictionary with keys in the order of _key_order.
        Used for debugging and serialization.
        """
        return {key: getattr(self, key) for key in self._key_order}