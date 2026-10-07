# Working in this repository

## Where the governing text lives

`.specify/memory/constitution.md` is the binding text for this project. It is the maintainer's, written gradually, and nothing else in the repository overrides it. Today it still holds the Spec Kit template.

The rationale behind it lives in `docs/explanation/architectural-constitution.md` (the nine primitives) and `docs/reference/intents-and-invariants.md` (the invariants of each intent).

## The workflow

This repository uses Spec Kit (`specify 1.1.1`, `sh` scripts). Its commands are agent skills, not terminal commands:

- **Short path:** `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` → `/speckit-converge`
- **Full path** adds `/speckit-clarify`, `/speckit-checklist` and `/speckit-analyze` as quality gates
- `/speckit-constitution` edits the constitution — the maintainer's text, never an agent's

The skills are installed for the two integrations this repository configures: Claude Code (`.claude/skills/speckit-*`) and Cursor (`.cursor/skills/speckit-*`).

## House rules that already apply

- **One phase = one commit.** A phase that is not a commit is a procedure, not a phase.
- **English** in commit messages and issues.
- **The changelog is the maintainer's**; agents leave it alone unless explicitly asked (`.cursor/rules/changelog-hands-off.mdc`).
- **The constitution is the maintainer's** too: do not edit `.specify/memory/constitution.md` unless the user asks in the current turn.
- **Verification is adversarial**: break the code the way the new test must catch, confirm that test fails and no other does, restore.
- **Documentation ships with the change** it describes.

## Where work is tracked

GitHub issues are the units of work; one branch per issue (`feature/issue-<n>-<slug>`), one pull request per branch.
