# Quickstart: validate #406

Run from the repository root with the project's environment.

1. The tests of this work:

   ```bash
   uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/model/test_json_schema_check.py packages/aoa-action-machine/tests/action_machine/model/test_json_schema_value.py packages/aoa-action-machine/tests/action_machine/domain/test_entity_schema_pydantic.py packages/aoa-action-machine/tests/action_machine/domain/test_entity_schema_projection.py -q
   ```

   Case 6.5 is a test of each of its parts: the tuple schema refused at declaration for both kinds of field, the same schema with Draft 7 accepted and its values checked as Draft 7, the reported message unchanged, and zero schema checks while values are checked.

2. The adversarial breaks, one at a time, against the phase's test files only:
   - check the schema as Draft 7 again at declaration → the tuple-schema tests fail;
   - check each value with `jsonschema.validate` again → the zero-schema-check test fails;
   - report the first error of `iter_errors` instead of `best_match` → the message test fails;
   - remove `JsonSchemaCheck.__reduce__` → the pickle test fails.

3. The timing (SC-001), reported with the phase: `ProjectionResult(order=row)` and `AuditResult(audit=row)` for `row = {"id": "o1", "status": "paid", "total": 99.5}`, against `jsonschema.validate(row, ORDER_WIRE)` in the same process; expected about 10 µs against about 550 µs, at least 25 times faster.

4. The pages this work touches run as written: tutorial steps 17 and 18 and their examples, through the example checks of the closing check run.

Expected: every part of case 6.5 gives its After output from issue #406, and nothing else in the closing check run changes.
