# src/action_machine/core/BaseState.py
"""
Base class for aspect pipeline state.

Inherits ReadableMixin and WritableMixin, providing a dict‑like interface
for reading and writing, as well as dot‑path resolution via the resolve method.

Replaces the previously used implicit dict[str, Any] in all aspects and plugins.

Advantages of replacing dict with BaseState:
    1. Uniform interface – state supports resolve, get, keys, items,
       write, update – just like all other objects based on ReadableMixin.
    2. Controlled writing – the write(key, value, allowed_keys) method
       allows restricting the set of fields that can be modified.
    3. Typing – IDE and mypy see the concrete type BaseState,
       not a vague dict[str, Any].
    4. Extensibility – you can subclass BaseState to add validation,
       change logging, or immutable fields.

Can be initialized from a dictionary. All keys become object attributes.
Supports dict‑like access (obj['key']) and attribute access (obj.key).

Example:
    >>> state = BaseState({"total": 1500, "user": "agent"})
    >>> state["count"] = 42
    >>> state.processed = True
    >>> state.resolve("user")
    'agent'
    >>> state.to_dict()
    {'total': 1500, 'user': 'agent', 'count': 42, 'processed': True}
"""

from typing import Any

from .readable_mixin import ReadableMixin
from .writable_mixin import WritableMixin


class BaseState(ReadableMixin, WritableMixin):
    """
    Aspect pipeline state.

    Can be initialized from a dictionary. All keys become attributes.
    Supports dict‑like access (obj['key']) and attribute access (obj.key).
    Also provides the resolve method for dot‑notation navigation
    and write for controlled writing with validation.
    """

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        """
        Initializes the state.

        If an initial dictionary is provided, each (key, value) pair
        is set as an attribute via setattr. None or an empty dictionary
        mean an empty state.

        Args:
            initial: initial values as a dictionary. Keys become object attributes.
                     None means empty state.

        Example:
            >>> state = BaseState({"total": 1500})
            >>> state.total
            1500
            >>> state = BaseState()
            >>> state.to_dict()
            {}
        """
        if initial:
            for key, value in initial.items():
                setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary of all public attributes of the state.

        Used to pass the state to loggers, serializers, and other components
        that expect a dictionary. Uses vars(self) and filters out private
        attributes (those starting with '_').

        Returns:
            dict[str, Any]: dictionary with (key, value) pairs for all
            public fields.

        Example:
            >>> state = BaseState({"a": 1, "b": 2})
            >>> state.to_dict()
            {'a': 1, 'b': 2}
        """
        # Collect all instance attributes except private ones (starting with '_')
        return {k: v for k, v in vars(self).items() if not k.startswith('_')}

    def __repr__(self) -> str:
        """
        Human‑readable representation of the state for debugging.

        Format: BaseState(key1=value1, key2=value2, ...).

        Returns:
            str: string representation of the object.

        Example:
            >>> state = BaseState({"total": 1500})
            >>> repr(state)
            "BaseState(total=1500)"
        """
        fields: dict[str, Any] = self.to_dict()
        pairs: str = ", ".join(f"{k}={v!r}" for k, v in fields.items())
        return f"{type(self).__name__}({pairs})"
