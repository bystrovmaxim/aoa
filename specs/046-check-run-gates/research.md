# Research: Check run — Radon as a real gate, one Ruff step, package builds confirmed

Checked against `main` at 197415c3.

## 1. How the gate reads Radon

**Decision**: A new script, `scripts/check_radon.py`, runs `radon cc -j` or `radon mi -j` over `packages/` as a subprocess and judges the JSON. The tasks `cc` and `mi` in `pyproject.toml` call it, so the two steps keep their names and their place.

**Rationale**: Radon has no failing threshold, and the issue asks for a few lines over its JSON with no new dependency. The steps already call `task cc` and `task mi`, so the step table does not change.

**What the JSON looks like** (1,248 files for `cc`, 1,482 for `mi`, read on this tree):

- `cc`: `{file: [block, ...]}`. A block has `type` (`function`, `class`, `method`), `name`, `rank`, `complexity`, `lineno`, and `classname` on a method. A class block also holds its `methods`, and those methods stand in the top-level list too, so reading the top-level list alone sees each once.
- `mi`: `{file: {"mi": 11.45, "rank": "B"}}`.
- A file Radon cannot parse gives `{"error": "..."}` in place of its value. There are none today; the gate treats one as a failure.

**Alternatives considered**: Ruff's `C901` counts more mildly, and at a limit of 15 finds nothing (issue, phase 2). Importing Radon as a library ties the gate to its internal API; the command line and its JSON are the stable surface. A shell pipeline with `grep` cannot tell an empty report from a broken one.

## 2. Where exceptions live

**Decision**: A table in `scripts/check_radon.py`: `(file, name) → reason`, for functions, and `file → reason`, for modules. Both are empty unless a simplification turns out not to be reasonable.

**Rationale**: The reason sits beside the exception, in a reviewed file, as the issue asks. The table is small enough that a config file would add a place to look and nothing else.

**Alternatives considered**: A marker comment in the code would scatter the exceptions and could not fail when stale. Radon's `--ignore`/`--exclude` hide a whole path and carry no reason.

## 3. One Ruff step in both places

**Decision**: "Ruff auto-fix" moves from `home=LOCAL` to `home=BOTH`, with `ci_command` set to the same paths without `--fix`. "Ruff lint" is removed from the table. The step gets a new field, `fast_keeps_command`, so `--fast` keeps fixing.

**Rationale**: `ci_command` is the table's existing way to say "this differs in CI". But `_select` applies `ci_command` under `--fast` too, because the pytest rows want that. Without the new field, `check_before_commit.sh` would stop fixing files. That is a behaviour change nobody asked for, and exactly what a plain reading of the table hides.

**Alternatives considered**:

- Removing "Ruff lint" outright, as the issue says: CI would have no Ruff at all.
- Keeping "Ruff lint" as a CI-only row: two rows again, which is what the issue set out to end.
- Removing "`ci_command` under `--fast`": the pytest rows rely on it.
- Dropping "`after`" dependencies: not needed. In CI the other steps now wait on the Ruff step, which takes about 0.1 s, and a failing step never stops the others.

`task lint` stays in `pyproject.toml`: a developer's read-only shortcut, and the same three paths.

## 4. Package builds

**Decision**: No change. #326 moved the builds from `python -m build` to `uv build --package <name> --out-dir packages/<name>/dist`, in CI only.

**Evidence to collect**: for each of the eight packages, build with `uv build` and with `python -m build` (through `uv run --with build`, so no dependency is added), and compare wheel and sdist member lists, plus times. The steps are in [quickstart.md](./quickstart.md).

**Rationale**: The issue's goal, a faster build with the same files, has landed. Its comparison has not been shown, so the phase closes with that proof, in a comment on the issue and with no commit.

## 5. Simplifying the six functions

**Decision**: Extract named helpers in the same module; no behaviour, signature or public-name changes. The target is grade C (complexity 20 or less), and a function that needs only one extraction gets only one.

| Function | Complexity | Where the seams are |
|---|---|---|
| `split_areas` | 23 | Standing of the nodes, and cutting edges into inner, across and links, are each self-contained |
| `assemble` | 21 | Building one overview area; the bundles |
| `_build_payload_from_duckdb` | 24 | Splitting rows by `result_type`; building node dicts |
| `_fill_database` | 28 | One helper per group of tables it fills |
| `test_examples_model_interchange_includes_parent_generalization_edges` | 24 | Assertion helpers; every assertion stays |
| `test_no_line_is_missing_or_off_screen_for_any_view` | 28 | Assertion helpers; every assertion stays |

**Rationale**: Each function has clear stages. Existing tests and the graph-file check guard behaviour. Two functions are themselves tests, so each of those is proved by a deliberate break before and after: the same break fails it both times.

**Alternatives considered**: Exceptions for all six would turn the gate on at no cost and pay nothing down; FR-005 makes simplifying the default.

## 6. `test_graph_map.py` at grade B

**Decision**: Split it by what it tests into five modules: areas, places, assembling, unions, marks. The shared builders (`node`, `edge`, `document`, `by_id`) move to a helper module beside them. Every test stays, unchanged.

**Rationale**: The index falls with file size, and the file already reads in sections by subject. Each piece reached grade A, at 41.70 to 58.29. Grade A needs an index above 19, and the file is at 11.45.


## 7. The two remaining questions in the issue

- **Times**: "before" is taken on this tree before the first change, with the same machine and `AOA_CHECK_JOBS` unset, for each step touched plus the whole fast run.
- **Issue text**: phase 1 and phase 3 of #296 no longer say what is being done. Only the maintainer asks for the body to change, so the comments on the phases explain the difference.
