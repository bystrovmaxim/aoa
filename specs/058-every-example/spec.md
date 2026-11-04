# Feature Specification: Every example in the documentation runs as it is written

**Feature Branch**: `feature/issue-361-every-example`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Issue #361, "Check every example in the documentation", with its section "What is broken today".

## Overview

The documentation teaches by example: a reader copies a code block from a page, runs a script from `examples/`, opens its notebook, or presses "Try in Colab". If one example in a hundred is wrong, the reader cannot tell which one and stops trusting all of them.

On `main` at `d584bbba4`, 16 of 307 scripts fail, 66 of 301 notebooks fail, 268 of 328 Python blocks of the pages do not run as written and none of them says it is a fragment, and none of the 41 "Try in Colab" buttons opens the repository's notebook: 30 open copies on Google Drive, 9 lead to anchors that do not exist, 2 are placeholders. The issue lists every broken example with its cause.

After this change every example runs as it is written or says why it is a fragment, every shown output is the output the code prints, every notebook gives its script's result, every link to an example leads to it, and a pull request that breaks any of this fails.

## Clarifications

### Session 2026-11-04

- Q: Can every notebook open in Colab, or only those that already install their packages? → A: Every notebook gets a first cell that installs the packages it imports, so any notebook opens in Colab; in a checkout the reader may skip that cell. A check confirms the cell installs every package the notebook imports.
- Q: Two specialization axes of one head lead back through one `Generalization` field and give two identical edges; is that allowed? → A: No. A specialization has one reverse generalization and one head (chapter 22), so the graph is right to refuse. The example `step_24_relations/11_specialization_two_axes` is deleted, and the FAQ, the invariants page and chapter 24 no longer present it as working.
- Q: Are the LangGraph examples (issue rows 16–18) fixed here? → A: Yes. The examples written for the removed `LangGraphAdapter` are rewritten on `LangGraphController`; an action connects to a controller through `@connection`; and a node's result reaches the graph state before routing, fixed in the controller with a test if the controller is what is wrong. Chapter 16 describes `LangGraphController` alone.
- Q: What of the examples of chapter 29 (Maxitor), one of which needs a built web client? → A: Maxitor is a site, not a library to learn by examples: every script and notebook of `examples/step_29_maxitor/` is deleted. Chapter 29 and the how-to pages keep their text and lose the links to them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A script or notebook runs as the chapter promises (Priority: P1)

A reader runs a script from `examples/` or opens its notebook and sees what the chapter says, with no error.

**Why this priority**: Scripts and notebooks are the examples a reader runs most; 16 scripts and 66 notebooks fail today.

**Independent Test**: Run every script and every notebook of `examples/` in a fresh checkout; each finishes without an error.

**Acceptance Scenarios**:

1. **Given** a fresh checkout, **When** any script of `examples/` runs, **Then** it exits with code 0.
2. **Given** a fresh checkout, **When** any notebook of `examples/` runs from its first cell to its last in a new kernel, **Then** no cell fails.
3. **Given** a notebook and its script, **When** both run, **Then** they print the same lines, apart from values that differ on every run (ids, times, addresses).
4. **Given** the check that runs the scripts, **When** it lists what it runs, **Then** no example is skipped or marked as an expected failure.

---

### User Story 2 - A code block on a page is either runnable or says it is not (Priority: P1)

A reader copies a code block from a page. It either runs as written, together with the earlier blocks of the same page when the page builds one example step by step, or it is visibly marked as a fragment with the reason it does not run on its own.

**Why this priority**: 268 blocks do not run as written, and a reader cannot tell a fragment from a broken example.

**Independent Test**: Run every Python block of `docs/`, `README.md` and the package READMEs; every block that is not marked as a fragment runs, and every marked one carries a reason.

**Acceptance Scenarios**:

1. **Given** a block with no fragment mark, **When** it runs after the earlier blocks of its page, **Then** it succeeds.
2. **Given** a block marked as a fragment, **When** a reader looks at it, **Then** the mark says why it does not run on its own.
3. **Given** a block followed by the output it prints, **When** it runs, **Then** it prints exactly that output, apart from values that differ on every run.

---

### User Story 3 - "Try in Colab" opens the repository's own notebook (Priority: P2)

A reader presses "Try in Colab" next to an example and Colab opens that example's notebook from the repository, in its current version.

**Why this priority**: No button works today, and copies kept outside the repository drift from it without any check noticing.

**Independent Test**: Every "Try in Colab" button points at `https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/<path>.ipynb`, and `<path>` is a notebook that exists in the repository.

**Acceptance Scenarios**:

1. **Given** a page with a "Try in Colab" button, **When** the reader presses it, **Then** Colab opens the notebook at that path from the repository's `main`.
2. **Given** a notebook a button opens, **When** it runs in Colab from its first cell, **Then** its first cell installs every package it imports, and the rest runs.
3. **Given** a link to an example of any kind, **When** a check follows it, **Then** the file exists.

---

### User Story 4 - A change that breaks an example fails its pull request (Priority: P1)

A contributor changes the code in a way that breaks an example; the pull request fails and names the example.

**Why this priority**: Every broken example in the issue was broken by a change no check caught.

**Independent Test**: Break an example on purpose (remove an import from a notebook, change a shown output, point a Colab button at a missing file); the checks fail and name it.

**Acceptance Scenarios**:

1. **Given** a pull request that breaks a script, notebook, code block, shown output or example link, **When** CI runs, **Then** it fails and names the broken example.
2. **Given** a pull request that breaks nothing, **When** CI runs, **Then** the example checks pass.

---

### Edge Cases

- A notebook runs in its own folder, a script runs from the repository root: an example finds its files the same way in both.
- A notebook already runs an event loop: a notebook does not call `asyncio.run()`.
- An expected error message carries a link with the installed library's version: the comparison ignores that version.
- A package folder inside `examples/` (one with `__init__.py`) holds modules of an example, not examples.
- A page builds one example over several blocks: a block runs after the earlier blocks of the same page, and a block that needs a block of another page is a fragment.
- An example needs a secret, a network service or a file the reader brings: it is a fragment, or it supplies a stand-in.
- A page presents as working an example the library rightly refuses (two specialization axes through one reverse field): the example goes, and so does the claim.
- A node's result in a LangGraph example does not reach the graph state before routing: the controller is checked first, and the fix goes where the fault is.
- A notebook's install cell names a package that does not exist on PyPI, or leaves out one the notebook imports: the check fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every script in `examples/` MUST run to the end with exit code 0 in a fresh checkout.
- **FR-002**: The check that runs the scripts MUST NOT skip any script or mark one as an expected failure; folders that are packages of an example are not scripts.
- **FR-003**: Every notebook in `examples/` MUST run from its first cell to its last in a new kernel without an error.
- **FR-004**: Every line a notebook prints MUST be a line its script prints, in the same order, apart from values that differ on every run; a notebook may leave out the headings a script prints between sections, which its Markdown cells say instead.
- **FR-005**: Every Python block in `docs/`, `README.md` and the package READMEs MUST either run, alone or after the earlier blocks of its page, or carry a fragment mark that says why it does not run.
- **FR-006**: Every output a page shows right after a block MUST equal what that block prints, apart from values that differ on every run and the installed library's version in a link.
- **FR-007**: Every link from a page to an example MUST lead to a file that exists.
- **FR-008**: Every "Try in Colab" button MUST point at `https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/<path>.ipynb` for a notebook that exists in the repository; no button points at a copy outside it.
- **FR-009**: Every broken example the issue lists MUST be fixed in the code or on the page, whichever is wrong, or removed where FR-013 and FR-014 say so.
- **FR-010**: The checks of FR-001 to FR-008 and FR-011 MUST run in CI on every pull request and fail it, naming the broken example.
- **FR-011**: Every notebook MUST start with a cell that installs every package it imports, by its name on PyPI.
- **FR-012**: The LangGraph examples MUST use `LangGraphController`; no example, page or README refers to `LangGraphAdapter` except the changelogs.
- **FR-013**: The example of two specialization axes through one reverse field MUST be removed, and no page MUST present it as working.
- **FR-014**: The scripts and notebooks of `examples/step_29_maxitor/` MUST be removed, and no page MUST link to them.

### Key Entities

- **Example**: a script, a notebook, or a Python block of a page; it runs or it is a fragment.
- **Fragment mark**: a visible note on a block that it does not run on its own, and why.
- **Shown output**: the text a page shows as what a block prints.
- **Example link**: a link from a page to a script or notebook, or a "Try in Colab" button.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the scripts and notebooks in `examples/` run without an error; today 291 of 307 scripts and 235 of 301 notebooks do.
- **SC-002**: 100% of the Python blocks of the pages run or carry a fragment mark with a reason; today 60 of 328 run and none is marked.
- **SC-003**: 100% of the shown outputs match what their blocks print, and every notebook prints what its script prints.
- **SC-004**: 100% of the "Try in Colab" buttons open the repository's own notebook; today 0 of 41 do.
- **SC-005**: Each kind of break (a script, a notebook, a block, a shown output, a link) made on purpose fails CI and names the example.

## Assumptions

- The repository is public, so Colab opens a notebook straight from GitHub; nothing is uploaded anywhere else.
- PyPI holds the same versions of the packages as the repository, so a notebook that installs them in Colab runs the same code as in a checkout.
- Values that differ on every run (ids, tokens, times, addresses, ports) are not compared.
- The copies on Google Drive are deleted by the maintainer after the change is merged; nothing in the repository refers to them.
- Archived pages (`archive/`) and the changelogs are history, not documentation, and are not checked.
- Pages written in Russian (`*.ru_draft.md`) are not part of the repository and are not checked.
