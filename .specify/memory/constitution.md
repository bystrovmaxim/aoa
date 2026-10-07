<!-- Sync Impact Report
  Version change: template (no version) → 1.0.0
  Rationale: MINOR would be wrong — there is no earlier ratified version to amend.
    This is the first adoption, so 1.0.0, and ratification is the maintainer's
    confirmation (see the TODO in the version line).
  Principles written (all dictated by the maintainer in conversation):
    I.   The maintainer decides — commits, pull requests and merges only on instruction
    II.  English in commits, in git, and in code
    III. Module headers
    IV.  AI-CORE blocks
    V.   Short docstrings on every class, function and method
  Sections written:
    Final step: the check run
  Intentionally retained template slots (the maintainer writes the constitution
  gradually; these are not filled in by an agent):
    [PRINCIPLE_*] slots beyond V, [SECTION_2_NAME]/[SECTION_2_CONTENT],
    [SECTION_3_NAME]/[SECTION_3_CONTENT], [GOVERNANCE_RULES]
  Changes after the first draft of this file:
    II — the paragraph allowing Russian in `*.ru.md` files and in the notes under
      `archive/` was removed at the maintainer's instruction; the rule has no
      exceptions now
  Follow-up TODOs:
    - TODO(RATIFICATION_DATE): the maintainer confirms the date this text is adopted
    - TODO(GOVERNANCE_RULES): amendment procedure, versioning policy and compliance
      review are the maintainer's text
    - the debt noted inside principles III–V (modules without docstrings, files with
      an AI-CORE block in the wrong place) is accepted as debt, paid as files are touched
  This report is scratch material for review and is removed before the amendment is
  committed.
-->

# AOA Constitution

## Core Principles

### I. The maintainer decides — commits, pull requests and merges happen only on instruction (NON-NEGOTIABLE)

Commits, pushes, pull requests and merges are made **only on an explicit instruction from the maintainer, given in the current conversation**. An agent may read, edit and run checks, and it must show what it changed — but it does not commit, push, open a pull request or merge on its own initiative: not as a side effect of finishing a task, not because a plan or an issue lists it as a phase, and not because the work looks complete. Preparing a change and shipping it are two separate decisions, and the second one belongs to the maintainer.

### II. English in commits, in git, and in code (NON-NEGOTIABLE)

Commit messages, issues, pull-request titles and descriptions, review comments, and every comment, docstring or example inside the code are written in **English**.

This is not a style preference. History and code are read by people and by agents who do not share the maintainer's first language; a mixed-language history cannot be searched, and a mixed-language codebase cannot be reviewed by the people most likely to review it.

Known non-compliant places, translated as each is next touched: `pyproject.toml`, `.pre-commit-config.yaml`, `.gitignore`. The Python code, tests and scripts contain no Russian today; docstrings and code-facing prose are additionally specified by `.cursor/rules/docstring-standards.mdc`.

### III. Module headers

Every Python module under `packages/*/src` opens the same way. The shape is not decoration: it makes a module identifiable from its first line and its purpose readable before any code.

1. **Line 1 is the file's path, relative to the repository root, as a comment:**

   ```python
   # packages/aoa-action-machine/src/aoa/action_machine/application/application.py
   ```

   All 759 modules do this today, and never in the `# src/...` form.
2. **Then the module docstring**, whose first line is a title: `Name — purpose.` — an em dash, one line.
3. **Sections are delimited by a rule of `═` (U+2550) repeated to 79 columns**, with a blank line before the first rule and after the second, and the section name in capitals between them:

   ```
   ═══════════════════════════════════════════════════════════════════════════════
   PURPOSE
   ═══════════════════════════════════════════════════════════════════════════════
   ```

4. **`PURPOSE` and `ARCHITECTURE / DATA FLOW` are the standing sections.** Further sections come from the vocabulary the code already uses: `SCOPE (IN / OUT)`, `COMPONENTS`, `RATIONALE`, `LIFECYCLE (IMPORT VS BUILD VS RUNTIME)`, `USAGE`, `EXAMPLES`. A section with nothing to say is omitted, never written as an empty shell.
5. **Diagrams** live in the architecture section as ASCII art, introduced by `::`.
6. **No `AI-CORE-BEGIN` block in a module docstring**; machine-readable blocks belong to public classes and module-level functions (principle IV).
7. **The docstring closes with `"""` on its own line.**

Known debt, paid as files are touched: 256 modules under `src` carry no module docstring at all (218 of them are not `__init__.py`); two files use an 80-column rule instead of 79; `.cursor/rules/docstring-standards.mdc` still shows `# src/package/module.py` as the line-1 example, which no module in this repository follows.

### IV. AI-CORE blocks

A public class or a module-level function carries a machine-readable contract inside its docstring, between two markers. The markers are read by agents and by the graph and tooling layers: they state what the type is for, what it promises, and what a reader must not break. There are **195 such blocks in 178 modules** today.

1. **Exact markers, each on its own line:** `AI-CORE-BEGIN` and `AI-CORE-END`. No blank line between them, and nothing else on the marker line.
2. **One key per line — uppercase name, colon, then one or two sentences:**

   ```
   AI-CORE-BEGIN
   ROLE: Typed application root marker for interchange ``Application`` vertices.
   CONTRACT: ``name`` and ``description`` are non-empty class attributes for graph properties.
   INVARIANTS: No instances required; used as ``node_obj`` on ``ApplicationGraphNode``.
   AI-CORE-END
   ```

3. **`ROLE` and `CONTRACT` are the standing keys on a class**; `INVARIANTS` is added whenever the type has invariants a reader could break — 130 blocks carry all three, 38 carry the first two. Further keys come from the vocabulary the code already uses: `FAILURES` (19 blocks), `PROPERTIES`, `INPUT/OUTPUT`, `SIDE EFFECTS`, `FACTORY`, `ORDER`, `PURPOSE`, `EDGES`, `CACHE`, `ACCESS`. A key with nothing to say is omitted, never filled with a placeholder.
4. **Where a block may live:** public classes (184 blocks) and module-level functions (10 blocks). **Never in a module docstring and never on a method** — a method gets the one line of principle V, or a comment above `def`.
5. **No narrative prose inside the markers.** The content is structured, one to two sentences per key; explanation belongs in a short human summary above the block (14 blocks have one) or in the prose around it.
6. **Nothing follows `AI-CORE-END`** in the same docstring.

Held by review only: nothing in `scripts/`, `tests/`, `.pre-commit-config.yaml` or `pyproject.toml` inspects these markers, so the shape survives because humans and agents read it. Known violations, to fix as the files are touched: `EntityFieldGraphNode.pretty_annotation` carries a block in a method docstring; `packages/aoa-fastapi-adapter/src/aoa/fastapi/query_field_before/query_str_list.py` carries one in a module docstring; three blocks have text after `AI-CORE-END`.

### V. Short docstrings on every class, function and method

Every class, every function and every method carries a docstring that says in one line what it is for. This is the layer between the code and the reader: short enough to be read at the call site, precise enough to say what the name does not.

1. **One line of text, ending with a period.** All 446 single-line docstrings on functions and methods in this repository end with one. Typical length is five to ten words; a longer explanation belongs in the module header (principle III) or in an AI-CORE block (principle IV).
2. **Identifiers are wrapped in double backticks** — ```UserInfo```, ```Context``` — so they render as code (190 of those 446 do this).
3. **Physical form.** `"""Text."""` on one line when it fits (691 docstrings), or the opening `"""` on its own line, the text below, and the closing `"""` on its own line (88):

   ```python
   class _UserFields:
       """
       Dot-path constants for ``UserInfo`` fields inside ``Context``.
       """
   ```

4. **A class that carries an AI-CORE block may use the block instead of the one line.** A short human summary above the block is allowed; a method never carries a block, it carries the one line.
5. **Fields and properties may carry their own one-line docstring**, written as a string directly under the assignment (18 fields do today; `context/ctx_constants.py` is the reference).
6. **The line states purpose, not mechanics.** "Assigned role classes. ``UserInfo`` type: role tuple." — not a restatement of the code beneath it.

Known debt: this rule is met for roughly half of the code. Classes 431 of 846 (51 %), methods 410 of 840 (49 %), class and static methods 137 of 157 (87 %), module-level functions 207 of 316 (66 %), properties 62 of 115 (54 %), nested functions 11 of 47 (23 %). The debt is paid as files are touched, unless the maintainer decides to schedule a sweep.

## Final step: the check run

Work is not finished when the code looks right; it is finished when the repository's own check run says so.

1. **The last step of any change is `bash scripts/run_checks_with_log.sh`**, executed from the repository root. It is the local counterpart of a gate CI does not yet provide, and it covers: the Maxitor client build; a ban on `__getattr__` in package `__init__.py`; README files beside `components/*/index.ts`; Ruff with `--fix`; Ruff lint; mypy across all eight packages; pylint; the package-boundary and package-metadata checkers; a wheel and sdist build of every package; the packaging smoke test; vulture; the Maxitor samples public-API check; Radon complexity and maintainability; and the test suite of every package.
2. **Errors are fixed until the run is clean.** The point is not to report the failures but to leave the repository in a state where the script exits without errors. A failing check is either fixed in the change or reported to the maintainer with the exact command and output — "known failure" is not an outcome, and neither is skipping the step because the diff looked small.
3. **The log is evidence, not a deliverable.** The script appends to `archive/logs/check-all.txt`, and `archive/` is outside Git; the pull request states that the run passed, and pastes the tail only for what could not be fixed.
4. **The run may edit the code, and those edits are part of the change.** The first Python step is `ruff check --fix .`, so the run is not read-only: whatever it fixes is reviewed like any other change and re-committed, and an auto-fix the reviewer does not want is reverted rather than left in place.
5. **The script itself is part of what is checked.** If it cannot run — a missing tool, a broken path, a command whose configuration no longer exists — that is a defect in the check run and is repaired as part of the change, not bypassed.

## [SECTION_2_NAME]
<!-- Retained from the toolkit's template: the maintainer writes this. -->

[SECTION_2_CONTENT]

## [SECTION_3_NAME]
<!-- Retained from the toolkit's template: the maintainer writes this. -->

[SECTION_3_CONTENT]

## Governance
<!-- Retained from the toolkit's template: the maintainer writes this. -->

[GOVERNANCE_RULES]

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE) | **Last Amended**: 2026-10-07
