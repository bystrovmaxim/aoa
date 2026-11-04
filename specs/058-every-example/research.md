# Research: Every example in the documentation runs as it is written

## R1. Where the example checks run today

- **Decision**: The example checks become a step of the check run (`scripts/check_run.py`), so CI runs them on every pull request.
- **Rationale**: `tests/examples/test_examples_run.py` exists but no step of the check run or of CI calls it: that is how 12 scripts broke unnoticed.
- **Alternatives considered**: A separate CI job — rejected, the check run is the one list of checks and CI already runs it.

## R2. How a fragment is marked

- **Decision**: A fragment's first line is a comment `# Fragment: <reason>.` The reason says what is missing (a name from another page, a body left as `...`, a reader's own service).
- **Rationale**: It is visible on the page and in GitHub's rendering, it survives copy and paste, and a check reads it without a Markdown extension.
- **Alternatives considered**: A word after the fence (```` ```python fragment ````) — invisible to a reader; an HTML comment above the block — invisible too.

## R3. How the blocks of one page run

- **Decision**: The blocks of a page run in order in one process; a block runs after every earlier unmarked block of its page. A fragment is not run. Each block's output is captured on its own.
- **Rationale**: Tutorials build one example over several blocks; 6 blocks run only that way today.
- **Alternatives considered**: Each block alone — would force every tutorial block to repeat its imports.

## R4. Which output a page shows for a block

- **Decision**: A ```` ```text ```` block is the output of the Python block before it when nothing but blank lines, or one lead-in sentence ending with a colon, stands between them. It is compared line by line after the values of R5 are masked.
- **Rationale**: That is how the pages already show output; it needs no new mark.
- **Alternatives considered**: A mark on every output block — more noise for the same certainty.

## R5. Values that differ on every run

- **Decision**: Masked before any comparison: UUIDs, hex addresses, ISO timestamps, durations, port numbers in URLs, JWTs and random tokens, and the version in `errors.pydantic.dev/<version>/` links.
- **Rationale**: They differ on every run or with the installed library; everything else must match.
- **Alternatives considered**: Comparing only a hash of the output — hides what differs.

## R6. How a notebook is run and compared with its script

- **Decision**: `nbclient` runs the notebook in a fresh `ipykernel` with the repository's environment, in the notebook's folder, skipping the install cell. Its printed lines must appear in its script's printed lines in the same order after R5's masking; a notebook may leave out the headings a script prints between sections.
- **Rationale**: The notebooks show the same case step by step and say the headings in Markdown cells; 228 of the 235 pairs that run already match this way.
- **Alternatives considered**: Exact equality — would fail on headings alone; comparing the code of the cells with the script — would forbid explaining a case step by step.

## R7. The install cell

- **Decision**: Every notebook's first code cell is `!pip install …` naming, by PyPI name, every package its imports need. The check scans a notebook's imports and maps each top-level module to a PyPI requirement through one table in the test (`aoa.action_machine` → `aoa-action-machine`, `aoa.fastapi` → `aoa-fastapi-adapter`, `aoa.mcp` → `aoa-mcp-adapter`, `aoa.langgraph` → `aoa-langgraph`, `aoa.otel` → `aoa-otel`, `aoa.ocel` → `aoa-ocel`, `jwt` → `aoa-action-machine[jwt]`, third-party modules to their distributions). A module in the standard library needs nothing; a module the table does not know fails the check.
- **Rationale**: The clarification asks that any notebook open in Colab; a table keeps the mapping in one reviewed place.
- **Alternatives considered**: Installing everything (`aoa-run[all]`) in every notebook — slow in Colab and hides which package a case needs.

## R8. Links and Colab buttons

- **Decision**: A check reads every link of the pages in scope: a relative link to `examples/` must lead to an existing file; a "Try in Colab" button must be `https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/<path>.ipynb` with an existing `<path>`. Every notebook a chapter links to gets a button.
- **Rationale**: The repository is public, so Colab opens a notebook straight from GitHub; the address carries the path, so the check needs no network.
- **Alternatives considered**: Asking Colab over the network — slow, and the path check proves the same.

## R9. Pages in scope

- **Decision**: `docs/**/*.md` except the changelogs and `*_draft.md`, `README.md`, and every `README.md` under `packages/` outside `node_modules`. `archive/` and `specs/` are out.
- **Rationale**: These are what a reader opens; the rest is history or planning.

## R10. Running time in CI

- **Decision**: The example step runs with `pytest-xdist` (`-n auto`). Notebooks took 440 s in one process here; spread over the CI machine's cores the step stays within a few minutes.
- **Rationale**: Each example runs in its own process already, so they parallelize without changes.
- **Alternatives considered**: Running notebooks only on a schedule — a pull request that breaks one would pass.

## R11. A pull request that changes only text

- **Decision**: Unchanged: the constitution lets such a pull request skip CI's checks, and it is opened only on the maintainer's instruction. A page's blocks are then checked by the next pull request that runs the checks.
- **Rationale**: The rule is the maintainer's; this change does not alter it.

## R12. The LangGraph examples

- **Decision**: `01_langgraph.py` and `extensions/02_langgraph.py` are rewritten on `LangGraphController`. Before `01_external_connection.py` and `05_testing.py` are touched, the controller is read: if it leaves a resource out of the graph or drops a node's result, the controller is fixed in `packages/aoa-langgraph` with a test, and that package's version rises.
- **Rationale**: The clarification keeps these here; the fault goes where it is.

## R13. Removals

- **Decision**: `examples/step_24_relations/11_specialization_two_axes.{py,ipynb}` and all of `examples/step_29_maxitor/` are removed, with every link to them; the pages that described them keep their text, and the FAQ and invariants page stop presenting two axes through one reverse field as working.
- **Rationale**: The clarifications of 2026-11-04.

## R14. Versions

- **Decision**: `aoa-langgraph` rises if its code changes (R12). The root `pyproject.toml` gains dev extras (`nbclient`, `ipykernel`, `pytest-xdist`); `examples/`, `tests/` and docs are not levels that count for version-gate.
