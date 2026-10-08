# Working in this repository

## Where the governing text lives

`.specify/memory/constitution.md` is the binding text for this project. It is the maintainer's, written gradually, and nothing else in the repository overrides it. Today its six principles are written plus the section on the final check run; the remaining sections are still the toolkit's template.

The rationale behind it lives in `docs/explanation/architectural-constitution.md` (the nine primitives) and `docs/reference/intents-and-invariants.md` (the invariants of each intent).

## The workflow

This repository uses Spec Kit (`specify 1.1.1`, `sh` scripts). Its commands are agent skills, not terminal commands:

- **Short path:** `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` → `/speckit-converge`
- **Full path** adds `/speckit-clarify`, `/speckit-checklist` and `/speckit-analyze` as quality gates
- `/speckit-constitution` edits the constitution — the maintainer's text: an agent writes in it only when explicitly asked in the current turn

The skills are installed for the tools this repository configures: DeepSeek Harness (`.dsh/skills/speckit-*`, the environment this work is actually done in), Claude Code (`.claude/skills/speckit-*`) and Cursor (`.cursor/skills/speckit-*`).

## House rules that already apply

- **Nothing is committed, pushed, opened as a pull request or merged without an explicit instruction** from the maintainer in the current conversation. Prepare the change, show the diff, wait. This is Principle I of the constitution (`.specify/memory/constitution.md`).
- **One phase = one commit.** A phase that is not a commit is a procedure, not a phase.
- **English wherever it is read as code or as history** — commit messages, issues, pull requests, review comments, and every comment, docstring or example in the code (Principle II of the constitution).
- **The tail of a change is three steps, in this order** (Principle VI of the constitution): the closing check run taken to zero, then the documentation, then the changelog. The changelog is **one article** about what the work created — plain words, the nuances a user needs, no technical detail and no per-file account of what moved. The agent writes it; planning reserves a task for each of the three.
- **The constitution is the maintainer's** too: do not edit `.specify/memory/constitution.md` unless the user asks in the current turn.
- **Two remarks in the check log are accepted and are not to be acted on**: the Vite build's chunk-size advisory and LangGraph's pending-deprecation warning. Both come from tools rather than from this repository's code; they are named in `scripts/run_checks_with_log.sh` and in the constitution's check-run section.
- **Verification is adversarial**: break the code the way the new test must catch, confirm that test fails and no other does, restore.
- **Every report links the Russian version too** — the maintainer reads it, so a page written in this change is reported as both links, the English one and its `<page>.ru_draft.md` beside it (`_draft.md` is what `.gitignore` ignores, so the Russian page never enters a commit).
- **A finished task is reported with examples** — always, without being asked: what changed, the code before and after where it matters, one real call with the answer it gives (not a paraphrase of it), how it was verified and what the adversarial breaks were, and what is left. A claim without an example is not a report.
- **Documentation ships with the change** it describes.

## Where work is tracked

GitHub issues are the units of work; one branch per issue (`feature/issue-<n>-<slug>`), one pull request per branch.
