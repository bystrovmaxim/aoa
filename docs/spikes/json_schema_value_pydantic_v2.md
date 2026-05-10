# Spike: JsonSchemaValue — Pydantic v2 compatibility (PR-0)

**Date:** 2026-05-11  
**Environment:** Repository root `uv run python3`, **Pydantic 2.12.5** (`pydantic-core` as pulled by workspace).  
**Scope:** Validate six PR-0 questions from `archive/plan/CURRENT.md`. No production code changes; spike-only experiments.

---

## Method

A minimal `type(name, (), {...})` factory defines a custom annotation with:

- `classmethod __get_pydantic_core_schema__` → `no_info_plain_validator_function` (toy validation: `dict` with required keys) + `plain_serializer_function_ser_schema(lambda v: v, info_arg=False)` so serialization returns the raw value.
- `classmethod __get_pydantic_json_schema__` → returns a **copy** of a dict shaped like JSON Schema (`type`, `properties`, `required`, `additionalProperties`, optional `title`).

PR-1 will swap the toy validator for `jsonschema.validate`; conclusions below concern **Pydantic integration only**.

---

## Question 1 — Hooks on a class created via `type()`

**Result:** **Works.**

`BaseModel` subclasses with a field annotated as `MyJson = make_type("MyJson", SCHEMA)` build successfully, validate on normal construction, and serialize.

**PR-1 implication:** No need to abandon dynamic `type()` for a named subclass **unless** future edge cases appear (e.g. pickling, typing tooling); current Pydantic v2 path is fine.

---

## Question 2 — `model_json_schema()`: `$ref` vs inline for the custom type

**Result:** **Inline schema under `properties.<field_name>`** for the tested models; **no top-level `$defs`** in the generated root schema JSON.

Observed shapes:


| Model field           | `properties[field]`                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `field: MyJson`       | Full object schema inline; Pydantic set `"title": "Field"` (from the Python field name).                                  |
| `graph: ErdGraphJson` | Full object schema inline; our dict’s `"title": "ErdGraphJson"` was preserved alongside `type`, `properties`, `required`. |


**PR-1 / PR-2 implication:** Default Pydantic 2.12.5 output for this pattern is **inline**, not `$ref`. Tests must still **support `$ref` + `$defs`** if a future Pydantic version, schema mode, or wrapper model changes emission—use a small `_resolve_ref(openapi, node)` helper when asserting OpenAPI / `model_json_schema()`.

---

## Question 3 — `model_dump()` without a wrapper object

**Result:** **Works.** `model_dump()["field"]` is a plain `dict`, not an instance of the dynamic type.

**PR-1 implication:** The planned `plain_serializer_function_ser_schema(lambda v: v, info_arg=False)` (or equivalent) is sufficient.

---

## Question 4 — `arbitrary_types_allowed=True` with `ConfigDict(frozen=True, extra="forbid")`

**Result:** **Not required.**

A `BaseModel` with `model_config = ConfigDict(frozen=True, extra="forbid")` and a `MyJson` field builds and validates the same way as a plain `BaseModel`.

**PR-1 implication:** Do not add `arbitrary_types_allowed` to `BaseResult` for `JsonSchemaValue` fields if hooks are implemented as above.

---

## Question 5 — `Optional` / `X | None`

**Result:** **Works as expected for Pydantic unions.**

- `Model(field=None)` validates; `model_dump()` contains `None`.
- `Model(field={"nodes": [], "edges": []})` runs the custom validator branch.
- Invalid non-`None` values still raise `ValidationError` (e.g. partial dict missing `edges`).

**PR-1 implication:** Document that `None` bypasses the JSON-schema branch (standard union behavior). No special casing beyond optional-unwrapping in graph metadata (PR-3).

---

## Question 6 — `model_construct()` and validation

**Result:** `**model_construct()` skips validators** (including our plain validator). `PlainModel.model_construct(label="z", field={"invalid": True})` succeeds and `model_dump()` returns the invalid payload. Normal `PlainModel(...)` raises `ValidationError` for the same payload.

**Documentation implication:** Known limitation—mirror Pydantic’s general `model_construct` contract; recommend `Model(...)` / validated factories for schema-backed fields.

---

## Summary table


| #   | Question                  | Outcome                                                          |
| --- | ------------------------- | ---------------------------------------------------------------- |
| 1   | `type()` + hooks          | Works                                                            |
| 2   | `$ref` vs inline          | Inline in 2.12.5; keep `$ref` resolution in tests for robustness |
| 3   | `model_dump()`            | Raw `dict`                                                       |
| 4   | `arbitrary_types_allowed` | Not needed with `frozen` + `extra_forbid`                        |
| 5   | Optional                  | Union behavior OK                                                |
| 6   | `model_construct()`       | No JSON validation; document                                     |


---

## Follow-ups for PR-1 (non-blocking)

- Replace toy validation with `jsonschema` + `Draft7Validator.check_schema` at `define()` time as in the plan.
- After `jsonschema` is wired, re-run a **short** subset of Q2–Q3 checks once (schema emission and dump shape should be unchanged).