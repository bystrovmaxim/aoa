# tests/adapters/mcp/test_mcp_schema.py
"""
JSON Schema shape for MCP ``inputSchema`` (Pydantic ``Params`` models).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror what ``McpAdapter`` does internally: ``effective_request_model.model_json_schema()``
must expose types, descriptions, constraints, required vs optional fields,
nested objects, and examples in a form suitable for tool-calling clients.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Domain action ``Params`` (Pydantic ``BaseModel``)
              |
              v
    _get_schema(model)  ==  model.model_json_schema()
              |
              v
    Assertions on JSON Schema fragments (types, required, $ref, ...)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Uses the same Pydantic major version as the library under test.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/adapters/mcp/test_mcp_schema.py -q

Edge case: empty ``Params`` → object schema with no required properties.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Schema keys and ``$ref`` layout can shift with Pydantic upgrades; tests encode
  current stable expectations.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Contract tests for tool input JSON Schema from Params models.
CONTRACT: ``model_json_schema`` parity with MCP adapter expectations.
INVARIANTS: Scenario models ``PingAction``, ``SimpleAction``, ``FullAction``.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from pydantic import BaseModel, Field

from tests.scenarios.domain_model import FullAction, PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Helper — extract schema from a Pydantic model the same way McpAdapter does.
# McpAdapter calls effective_request_model.model_json_schema() internally.
# ─────────────────────────────────────────────────────────────────────────────


def _get_schema(model: type[BaseModel]) -> dict:
    """Get JSON Schema dict from a Pydantic model."""
    return model.model_json_schema()


# ═════════════════════════════════════════════════════════════════════════════
# PingAction.Params — empty model
# ═════════════════════════════════════════════════════════════════════════════


class TestEmptyParams:
    """Verify schema for an empty Params model (no fields)."""

    def test_schema_is_object_type(self) -> None:
        """Empty Params produces a schema with type=object."""
        schema = _get_schema(PingAction.Params)
        assert schema.get("type") == "object"

    def test_no_required_fields(self) -> None:
        """Empty Params has no required fields."""
        schema = _get_schema(PingAction.Params)
        required = schema.get("required", [])
        assert len(required) == 0

    def test_properties_empty_or_absent(self) -> None:
        """Empty Params has no properties (or an empty properties dict)."""
        schema = _get_schema(PingAction.Params)
        properties = schema.get("properties", {})
        assert len(properties) == 0


# ═════════════════════════════════════════════════════════════════════════════
# SimpleAction.Params — single required field
# ═════════════════════════════════════════════════════════════════════════════


class TestSimpleParams:
    """Verify schema for SimpleAction.Params (one required string field)."""

    def test_name_field_exists(self) -> None:
        """The 'name' field appears in schema properties."""
        schema = _get_schema(SimpleAction.Params)
        assert "name" in schema.get("properties", {})

    def test_name_field_type(self) -> None:
        """The 'name' field has type=string in the schema."""
        schema = _get_schema(SimpleAction.Params)
        name_prop = schema["properties"]["name"]
        assert name_prop.get("type") == "string"

    def test_name_is_required(self) -> None:
        """The 'name' field appears in the required list."""
        schema = _get_schema(SimpleAction.Params)
        assert "name" in schema.get("required", [])

    def test_name_has_description(self) -> None:
        """The 'name' field carries its Field(description=...) value."""
        schema = _get_schema(SimpleAction.Params)
        name_prop = schema["properties"]["name"]
        assert "description" in name_prop
        assert len(name_prop["description"]) > 0

    def test_name_min_length(self) -> None:
        """The 'name' field carries the minLength constraint from Field(min_length=1)."""
        schema = _get_schema(SimpleAction.Params)
        name_prop = schema["properties"]["name"]
        assert name_prop.get("minLength") == 1

    def test_name_has_examples(self) -> None:
        """The 'name' field carries examples from Field(examples=[...])."""
        schema = _get_schema(SimpleAction.Params)
        name_prop = schema["properties"]["name"]
        assert "examples" in name_prop
        assert "Alice" in name_prop["examples"]


# ═════════════════════════════════════════════════════════════════════════════
# FullAction.Params — multiple fields with constraints
# ═════════════════════════════════════════════════════════════════════════════


class TestFullParams:
    """Verify schema for FullAction.Params (multiple fields, defaults, constraints)."""

    def test_user_id_field_exists(self) -> None:
        """The 'user_id' field appears in schema properties."""
        schema = _get_schema(FullAction.Params)
        assert "user_id" in schema.get("properties", {})

    def test_amount_field_exists(self) -> None:
        """The 'amount' field appears in schema properties."""
        schema = _get_schema(FullAction.Params)
        assert "amount" in schema.get("properties", {})

    def test_currency_field_exists(self) -> None:
        """The 'currency' field appears in schema properties."""
        schema = _get_schema(FullAction.Params)
        assert "currency" in schema.get("properties", {})

    def test_user_id_is_required(self) -> None:
        """user_id is in the required list (no default)."""
        schema = _get_schema(FullAction.Params)
        assert "user_id" in schema.get("required", [])

    def test_amount_is_required(self) -> None:
        """amount is in the required list (no default)."""
        schema = _get_schema(FullAction.Params)
        assert "amount" in schema.get("required", [])

    def test_currency_not_required(self) -> None:
        """currency has a default ('RUB') and is NOT in the required list."""
        schema = _get_schema(FullAction.Params)
        required = schema.get("required", [])
        assert "currency" not in required

    def test_currency_default_value(self) -> None:
        """currency has default='RUB' in the schema."""
        schema = _get_schema(FullAction.Params)
        currency_prop = schema["properties"]["currency"]
        assert currency_prop.get("default") == "RUB"

    def test_amount_exclusive_minimum(self) -> None:
        """amount has exclusiveMinimum=0 from Field(gt=0)."""
        schema = _get_schema(FullAction.Params)
        amount_prop = schema["properties"]["amount"]
        assert amount_prop.get("exclusiveMinimum") == 0

    def test_currency_pattern(self) -> None:
        """currency has a pattern constraint from Field(pattern=...)."""
        schema = _get_schema(FullAction.Params)
        currency_prop = schema["properties"]["currency"]
        assert "pattern" in currency_prop

    def test_user_id_min_length(self) -> None:
        """user_id has minLength=1 from Field(min_length=1)."""
        schema = _get_schema(FullAction.Params)
        user_id_prop = schema["properties"]["user_id"]
        assert user_id_prop.get("minLength") == 1

    def test_amount_has_description(self) -> None:
        """amount carries its Field description."""
        schema = _get_schema(FullAction.Params)
        amount_prop = schema["properties"]["amount"]
        assert "description" in amount_prop
        assert len(amount_prop["description"]) > 0


# ═════════════════════════════════════════════════════════════════════════════
# Custom model with nested structure
# ═════════════════════════════════════════════════════════════════════════════


class _Address(BaseModel):
    """Nested model for schema nesting tests."""
    city: str = Field(description="City name")
    zip_code: str = Field(description="Postal code", pattern=r"^\d{5,6}$")


class _OrderWithAddress(BaseModel):
    """Model with a nested Pydantic model field."""
    order_id: str = Field(description="Order identifier")
    address: _Address = Field(description="Delivery address")


class TestNestedModel:
    """Verify that nested Pydantic models produce valid schema references."""

    def test_address_field_exists(self) -> None:
        """The 'address' field appears in schema properties."""
        schema = _get_schema(_OrderWithAddress)
        assert "address" in schema.get("properties", {})

    def test_nested_model_has_ref_or_properties(self) -> None:
        """The nested address field uses $ref or inline properties."""
        schema = _get_schema(_OrderWithAddress)
        address_prop = schema["properties"]["address"]
        # Pydantic v2 uses $ref pointing to $defs
        has_ref = "$ref" in address_prop
        has_all_of = "allOf" in address_prop
        has_properties = "properties" in address_prop
        assert has_ref or has_all_of or has_properties

    def test_defs_contains_address(self) -> None:
        """The $defs section contains the Address model definition."""
        schema = _get_schema(_OrderWithAddress)
        defs = schema.get("$defs", {})
        # Pydantic v2 names the def after the class name
        assert "_Address" in defs or "Address" in defs or len(defs) > 0

    def test_nested_city_has_description(self) -> None:
        """The nested Address model's city field carries its description."""
        schema = _get_schema(_OrderWithAddress)
        defs = schema.get("$defs", {})

        # Find the Address definition regardless of exact key name
        address_def = None
        for _key, value in defs.items():
            if "city" in value.get("properties", {}):
                address_def = value
                break

        assert address_def is not None, f"No Address definition found in $defs: {defs.keys()}"
        city_prop = address_def["properties"]["city"]
        assert city_prop.get("description") == "City name"

    def test_nested_zip_has_pattern(self) -> None:
        """The nested Address model's zip_code field carries its pattern."""
        schema = _get_schema(_OrderWithAddress)
        defs = schema.get("$defs", {})

        address_def = None
        for _key, value in defs.items():
            if "zip_code" in value.get("properties", {}):
                address_def = value
                break

        assert address_def is not None
        zip_prop = address_def["properties"]["zip_code"]
        assert "pattern" in zip_prop
