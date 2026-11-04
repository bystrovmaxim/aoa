# Quickstart: validate #405

Run from the repository root with the project's environment.

1. The tests of this work:

   ```bash
   uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/domain -q
   ```

   Every case of the issue is a test: 1.1–1.5 (relation containers) and 2.1–2.3 (partial entities).

2. The adversarial breaks, one at a time, run against the test files of the phase only:
   - forward dunder names again in `BaseRelationOne.__getattr__` → the tests of 1.1–1.4 fail;
   - remove `__reduce__` from the containers → the deep-copy tests of 1.4 and the copy, deepcopy and pickle tests of 1.5 fail;
   - build `partial()` through `model_construct` again → the tests of 2.1 and 2.3 fail.

3. The LangGraph case:

   ```bash
   uv run --extra dev pytest packages/aoa-langgraph/tests/test_node_binding_entities.py -q
   ```

4. The examples and pages this work touches run as written: `examples/step_22_entity/03_partial.py`, the examples of tutorial steps 22 and 24 and of the how-to page on dictionary references, through the example checks of the closing check run.

Expected: every case prints its After output from issue #405, and nothing else in the closing check run changes.
