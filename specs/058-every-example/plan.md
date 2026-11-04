# Implementation Plan: Every example in the documentation runs as it is written

**Branch**: `feature/issue-361-every-example` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

## Summary

Four checks, then the fixes they ask for. The checks live in `tests/examples/` and share one harness: the scripts of `examples/` run with no skips (package folders are not scripts); every notebook runs in a fresh kernel and prints its script's lines; every Python block of the pages runs in page order or carries `# Fragment: <reason>.`, and a shown output equals what its block prints; every link to an example and every "Try in Colab" button leads to a file of the repository. The check run gains one step that runs them, so CI fails a pull request that breaks an example. Then every broken example of the issue is fixed or removed as the clarifications decided, every notebook gets its install cell, and the 41 Colab buttons point at the repository's notebooks.

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14)
**Primary Dependencies**: pytest; `nbclient` and `ipykernel` to run notebooks; `pytest-xdist` to run examples in parallel (new dev extras of the root `pyproject.toml`)
**Storage**: none
**Testing**: pytest under `tests/examples/`; the LangGraph fix, if any, under `packages/aoa-langgraph/tests/`
**Target Platform**: the repository and its CI
**Project Type**: monorepo
**Performance Goals**: the example step finishes within a few minutes on the CI machine (R10)
**Constraints**: no network in the checks (the install cell is skipped; Colab addresses are checked by path); `examples/` keeps a script and a notebook for each case
**Scale/Scope**: 307 → 260 scripts and 301 → 254 notebooks after the removals; 328 Python blocks on 149 pages; 824 example links and 41 Colab buttons

## Constitution Check

- I. The maintainer asked for the whole cycle (2026-11-04); commits, the pull request and the merge wait for their own instruction.
- II. English in code, commits and the issue; no tool attribution.
- III–V. New test modules and any changed module of `aoa-langgraph` carry the header, one-line docstrings and, for public classes, AI-CORE blocks.
- VI. Planning reserves the three tail tasks: the closing check run, the documentation (chapter 16, the pages that lose `step_29` and two-axis links, the page on the checks), the changelog. The pull request opens whole. Principle VI.6 says the closing check run does not execute the examples; this change makes it execute them, so that sentence is no longer true. The constitution is the maintainer's: the plan reports the conflict and does not edit it.

Gates pass, with the VI.6 conflict to put to the maintainer before the pull request opens.

## Project Structure

### Documentation (this feature)

```text
specs/058-every-example/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/example-checks.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
tests/examples/
├── harness.py                 # pages and blocks in scope, masking of volatile values, running a page
├── test_examples_run.py       # scripts: no xfail, package folders skipped
├── test_notebooks.py          # notebooks: run, compare with the script, install cell
├── test_page_blocks.py        # page blocks: run or fragment mark, shown outputs
└── test_example_links.py      # links to examples and Colab buttons
scripts/check_run.py           # one new step: the example checks
pyproject.toml                 # dev extras: nbclient, ipykernel, pytest-xdist
examples/                      # fixes; step_29_maxitor/ and step_24/11 removed; install cells
docs/, README.md, packages/*/README.md   # fragment marks, fixed blocks, Colab buttons
packages/aoa-langgraph/        # only if the controller is at fault (R12)
docs/how-to/run-the-checks.md  # the new step
```

## Complexity Tracking

None.
