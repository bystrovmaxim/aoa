# Dictionary reference verification

## Scope and baseline

Branch: `feature/issue-256-dictionary-reference`. Main branch: `origin/main`.
Merge base: `d1f28968b8a500ec7b1e519a38cced7519981ec7`.
The branch contains two specification commits: `f445014e` and `9a6e8935`.
Behavior changes were present in the working tree. No staging operation was performed.

## Executed evidence

The focused validator, reference graph, reference JSON and Maxitor dictionary payload suites passed: **85 tests** using pytest's importlib mode. Default import mode collided between package test modules during collection; importlib mode resolves that test-runner naming conflict.

Five scripts and five matching notebooks were executed in fresh Python processes. Notebook code was executed directly, without a Jupyter kernel; stdout and execution counts were saved. Script and notebook stdout matched. The standalone Python block in the reference guide also passed.

Ruff lint and formatting checks passed on the five scripts. Local file links in the six updated pages were checked. Heading anchors were not exhaustively checked.

An isolated process suppressed collection validation in the declarations example. Its expected-refusal assertion failed. The unmodified graph example passed separately. This proves the scenario detects a missing refusal; it does not exhaustively mutate every validation branch or edge projection.

No additional source defect was reproduced within these checks. This is limited evidence, not proof of complete correctness. Full package suites, browser rendering, builds, type checking and the repository-wide check script were not run. Existing source behavior was not changed.

## Actual graph output

Command: `.venv/bin/python examples/step_20_dictionaries/08_graph.py`

```text
Kind: enum
Values: ['eur', 'usd']
Reference: CurrencyEnumEntity
Edge: entity_reference -> CurrencyEnumEntity
```

See [declarations and exact refusals](../how-to/dictionary-references.md).
