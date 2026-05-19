# aoa-examples

Publishable distribution for the `aoa.examples` namespace (FastAPI / MCP examples).

Action-to-action `@depends`: **extend** demos (`Depend*Action`) use `box.resolve` on the peer; **include** demos (`Depend*IncludeAction`) use `await box.run(...)` so the peer enters `_run_internal` (see `depend_same_domain.py` / `depend_cross_domain.py`). Dependencies on **resources** omit `mode`. Colocated tests: `packages/aoa-examples/aoa_examples_tests/test_depends_use_case_modes.py`.

See the [repository README](https://github.com/action-machine/action-machine/blob/main/README.md) for the full project.
