# aoa-action-machine

Publishable distribution for the `aoa.action_machine` namespace (ActionMachine core).

`@depends` on another **action** requires `mode=UseCase.include` or `UseCase.extend`; resource dependencies omit `mode`. After a successful root run, `include` peers must have entered `_run_internal` at least once in that run (see `runtime/include_contract_checker.py`). Graph JSON carries `mode`; the default Maxitor DuckDB path does not add a separate `mode` column on `depends_edges`.

See the [repository README](https://github.com/action-machine/action-machine/blob/main/README.md) for the full project.
