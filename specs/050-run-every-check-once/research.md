# Research: Run every check once

## 1. How a late proof counts

- **Decision**: the ruleset of `main` requires the commit status `Local check run` directly, and the job `Proof of the local run` is removed with `--await-sign-off`.
- **Rationale**: the job polls for 15 minutes and then fails, so a proof arriving later would need a rerun. A required status has no time limit, costs no CI minutes, and is bound to the exact commit, so a new commit starts without it.
- **Alternatives considered**: the sign-off reruns the failed job (more code, a red mark in between); a workflow on the `status` event (runs on the default branch, not attached to the pull request).

## 2. The `--fast` mode

- **Decision**: removed with its seals and tests.
- **Rationale**: `check_before_commit.sh` was its only caller; a mode nobody calls is dead code.
- **Alternatives considered**: keeping it for quick local runs, which would invite the double run this work removes.

## 3. Pull requests into feature branches

- **Decision**: no proof is required there.
- **Rationale**: the ruleset covers `main`; sub-issue branches are checked on their way and the proof is required when the work reaches `main`.
- **Alternatives considered**: a ruleset for `feature/**`, which would add a browser run per step.

## 4. Ruff auto-fix

- **Decision**: CI stays read-only and fails on findings; the developer fixes them.
- **Rationale**: CI must not change the tree.
