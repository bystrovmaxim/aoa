# Quickstart: validate #407

Run from the repository root with the project's environment.

1. The tests of each phase:

   ```bash
   uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_relation_json_form.py -q
   uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_reference_forms.py packages/aoa-action-machine/tests/action_machine/domain/test_dictionary_association_schema.py -q
   uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain/test_lifecycle_json_form.py -q
   uv run --extra dev pytest packages/aoa-fastapi-adapter/tests/test_fastapi_entity_fields.py -q
   uv run --extra dev pytest packages/aoa-mcp-adapter/tests/test_mcp_entity_fields.py -q
   uv run --extra dev pytest packages/aoa-langgraph/tests/test_node_binding_entities.py -q
   ```

2. The adversarial breaks of each phase, as plan.md lists them, against that phase's files only.

3. The timing of case 4.5, reported with phase 2: `model_dump_json()` of an entity with ten `CompositeOne[CurrencyEnumEntity]` fields, before (25.3 µs) and after.

4. The pages and examples this work touches run as written, through the example checks.

Expected: every case gives its After output from #407, and nothing else in the closing check run changes beyond the corrected tests and examples.
