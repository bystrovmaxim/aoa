# Documentation verification

Reviewed the ten commits from `origin/main` (`e791ad28`) through `83f425c7`, the issue,
implementation and tests before rewriting the English teaching material. This pass
changes documentation, examples and their generated artifacts; it does not change the
runtime implementation. Demo and Russian drafts are outside the requested scope.

## Executable material

- Executed 99 scripts and their 99 notebooks in separate repository Python processes,
  including 21 new focused cases. Every process completed successfully. Outputs match;
  only the integration example's generated `ord-XXXXXXXX` identifier is normalized.
- Checked all 99 notebooks against the notebook 4.5 schema, including unique cell IDs,
  valid Python cells, recorded execution counts and absence of error outputs.
- Executed all 22 printed dictionary-chapter examples with their stated preparation;
  every output matches the page.
- Ruff passes for all 198 script/notebook files. All 378 relative file links in the
  revised pages resolve. The specialization JSON, DOT and SVG were regenerated from
  the current model and renderer.

## Runtime checks before the documentation rewrite

The action-machine suite passed 2,811 tests; three JWT tests could not bind a local
server in the sandbox. Rerunning their whole module with local-server access passed
all 31 tests. Maxitor passed 147 tests, with one skip and one expected failure. The
client's dictionary-property and group-label checks passed, as did its production build
with the accepted chunk-size advisory.

The branch's earlier full 33-step check and six isolated adversarial breaks are recorded
in [closing-check-run.md](closing-check-run.md). Those mutations were not repeated in
this documentation-only pass; the new examples exercise the existing implementation.

## Remaining implementation limitations

The documentation distinguishes implemented checks from stronger guarantees. Two probes
reproduced gaps beyond the branch's current tests:

1. A declared `Enum` property exports successfully, but requesting its serialization
   schema raises `KeyError '#/$defs/Grade'`. The schema extraction loses the referenced
   definition.
2. An after-validator can return a list for a `tuple[str, ...]` field. The declaration
   checks its annotation, not the returned value. Appending to the resulting list changed
   the shared member to `['original', 'changed']`.

These are reported as limitations, not repaired by prose. The chapter also explains
that nested output-property keys are not marked required, input schema validation does
not replace catalogue lookup, and state properties are not recursively frozen.
