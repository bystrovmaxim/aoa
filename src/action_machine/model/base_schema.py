# src/action_machine/model/base_schema.py
"""
BaseSchema - unified base data schema for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseSchema`` is the root class for framework data structures. It inherits
from ``pydantic.BaseModel`` and adds two interfaces beyond regular fields:

1. Dict-like field access: ``obj["key"]``, ``"key" in obj``, ``obj.get("key")``,
   ``obj.keys()``, ``obj.values()``, ``obj.items()``.

2. Dot-path navigation for nested objects: ``obj.resolve("user.user_id")``
   traverses nested BaseSchema/dict/object chains and returns terminal value.

All data structures passed between framework components (params, state, result,
context, user/request/runtime information) inherit from ``BaseSchema``.

═══════════════════════════════════════════════════════════════════════════════
INHERITANCE HIERARCHY
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        ├── BaseParams              — frozen=True, extra="forbid"
        ├── BaseState               — frozen=True, extra="allow"
        ├── BaseResult              — frozen=True, extra="forbid"
        ├── UserInfo                — frozen=True, extra="forbid"
        ├── RequestInfo             — frozen=True, extra="forbid"
        ├── RuntimeInfo             — frozen=True, extra="forbid"
        └── Context                 — frozen=True, extra="forbid"

═══════════════════════════════════════════════════════════════════════════════
DICT-LIKE INTERFACE
═══════════════════════════════════════════════════════════════════════════════

    schema = MySchema(name="test", value=42)

    schema["name"]              -> "test"           __getitem__
    "name" in schema            -> True             __contains__
    schema.get("missing", 0)    -> 0                get
    list(schema.keys())         -> ["name", "value"] keys
    list(schema.values())       -> ["test", 42]     values
    list(schema.items())        -> [("name", "test"), ("value", 42)] items

For ``extra="allow"`` descendants (``BaseState``), ``keys/values/items``
include both declared and dynamic extra fields.

═══════════════════════════════════════════════════════════════════════════════
DOT-PATH NAVIGATION
═══════════════════════════════════════════════════════════════════════════════

    context.resolve("user.user_id")      -> context.user.user_id
    params.resolve("address.city")       -> params.address.city
    state.resolve("payment.txn_id")      -> state.payment.txn_id

Navigation is delegated to shared ``DotPathNavigator``. At each step, it picks
the strategy based on current object type:

    - ``BaseSchema`` -> ``__getitem__``
    - ``LogScope`` -> ``__getitem__``
    - ``dict`` -> direct key access
    - any object -> ``getattr``

If value is missing at any step, ``default`` is returned.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TYPE HINTS
═══════════════════════════════════════════════════════════════════════════════

    def process(data: BaseSchema) -> None: ...       # any schema
    def read_only(data: BaseParams) -> None: ...     # immutable params
    def with_state(data: BaseState) -> None: ...     # pipeline state

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Input payload
         |
         v
    Pydantic model construction (BaseSchema descendant)
         |
         +--> Dict-like reads (__getitem__/get/keys/items)
         +--> Dot-path reads (resolve -> DotPathNavigator)
         |
         v
    model_dump()/model_json_schema() for runtime adapters and tooling

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.model.base_schema import BaseSchema

    class Address(BaseSchema):
        city: str = Field(description="City")
        zip_code: str = Field(description="ZIP code")

    class OrderParams(BaseSchema):
        user_id: str = Field(description="User identifier")
        address: Address = Field(description="Shipping address")

    params = OrderParams(
        user_id="user_123",
        address=Address(city="Moscow", zip_code="101000"),
    )

    params["user_id"]                    # -> "user_123"
    params.resolve("address.city")       # -> "Moscow"
    list(params.keys())                  # -> ["user_id", "address"]
    params.model_dump()                  # -> {"user_id": "user_123", "address": {...}}

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Universal schema contract used across ActionMachine boundaries.
CONTRACT: Provide dict-like access and stable dot-path navigation.
INVARIANTS: Pydantic model semantics + unified read/navigation interface.
FLOW: typed model construction -> optional key/path reads -> serialization/schema.
FAILURES: Missing path values degrade to default via sentinel-based resolution.
EXTENSION POINTS: Descendants tune frozen/extra policy and declare typed fields.
AI-CORE-END
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from action_machine.runtime.navigation import _SENTINEL, DotPathNavigator


class BaseSchema(BaseModel):
    """
    Base Pydantic schema with dict-like reads and dot-path navigation.

    Framework data structures inherit this class and configure mutability
    (frozen) and extra-field policy through descendant ``model_config``.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    # Dict-like read helpers

    def __getitem__(self, key: str) -> object:
        """
        Access field value by key: ``schema["field_name"]``.

        Works for declared fields and extra fields (if ``extra="allow"``).
        """
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def __contains__(self, key: str) -> bool:
        """
        Check field presence: ``"field_name" in schema``.

        Covers both declared fields (``model_fields``) and dynamic extra fields
        (``__pydantic_extra__``).
        """
        if key in self.__class__.model_fields:
            return True
        extra = self.__pydantic_extra__
        if extra and key in extra:
            return True
        return False

    def get(self, key: str, default: object = None) -> object:
        """
        Return field value with ``default`` fallback (``dict.get`` semantics).
        """
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """
        Return names of all fields.

        Includes declared model fields and dynamic extra fields.
        """
        names = list(self.__class__.model_fields.keys())
        extra = self.__pydantic_extra__
        if extra:
            names.extend(extra.keys())
        return names

    def values(self) -> list[object]:
        """Return all field values in ``keys()`` order."""
        return [getattr(self, k) for k in self.keys()]

    def items(self) -> list[tuple[str, object]]:
        """Return ``(name, value)`` pairs in ``keys()`` order."""
        return [(k, getattr(self, k)) for k in self.keys()]

    # Dot-path navigation

    def resolve(self, dotpath: str, default: object = None) -> object:
        """
        Resolve a dot-path by traversing nested values.

        Delegates traversal to ``DotPathNavigator``. Missing path segments return
        ``default`` without raising; explicit ``None`` values are preserved.
        """
        result = DotPathNavigator.navigate(self, dotpath)
        if result is _SENTINEL:
            return default
        return result
