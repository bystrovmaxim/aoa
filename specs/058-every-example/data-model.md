# Data Model: Every example in the documentation runs as it is written

No stored data. The checks read these things from the repository.

## Page

A Markdown file in scope (research R9). Holds blocks in order.

## Block

A fenced block of a page.

- `language`: the word after the fence (`python`, `text`, …).
- `line`: where it starts on the page.
- `fragment_reason`: the text after `# Fragment:` on its first line, or none. Required to be non-empty when present.
- `shown_output`: the `text` block that follows it (research R4), or none.

Rules: a Python block with no fragment reason runs after the earlier unmarked Python blocks of its page; its printed text, masked (R5), equals its shown output when there is one.

## Script

A `.py` file under `examples/` outside a package folder (a folder with `__init__.py`). Runs from the repository root, exit code 0.

## Notebook

An `.ipynb` file under `examples/`, beside a script of the same name.

- `install_cell`: the first code cell, `!pip install …`.
- `imports`: the top-level modules its code cells import.

Rules: every module in `imports` is in the standard library or maps (R7) to a requirement the install cell names; with the install cell skipped it runs without an error in its own folder; every line it prints is a line its script prints, in order (R6).

## Example link

A link on a page to a file under `examples/`, or a "Try in Colab" button.

Rules: a relative link resolves to an existing file; a button's address is `https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/<path>.ipynb` with an existing `<path>`.
