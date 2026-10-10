# Implementation Plan: The demonstrator stand

**Branch**: `feature/issue-202-demonstrator-stand-containers` | **Date**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-demonstrator-stand/spec.md`

## Summary

The demonstrator and Maxitor each get their own container built from **this repository's sources** (the demo with the `[fastapi]` and `[mcp]` extras, Maxitor with the client built from the sources — replacing the stale PyPI install), deployed by one command onto `194.67.66.48`, served over HTTPS through the host's existing TLS front end at `dev.demo.aoa.run` and `dev.maxitor.aoa.run`, with health checks and a rollback on failure. The demonstrator model also gains the shapes the diagram cannot draw today — generalization fixtures first, the entity-specialization axis once #199 lands, and an audit that makes "all shapes" true rather than intended. Acceptance is recorded as a picture, the same way as issue #201.

## Technical Context

**Language/Version**: Python 3.12 (services), TypeScript/Vite (Maxitor client)

**Primary Dependencies**: uv workspace (the packages install from the repository, not PyPI), Docker + Compose on the host, the host's existing TLS terminator (to be identified at deployment time), Let's Encrypt via the terminator's renew mechanism

**Storage**: none beyond the containers themselves; the demo graph lives in memory/DuckDB inside the containers

**Testing**: the repository check run (`scripts/run_checks_with_log.sh`) for all code; local container bring-up (`docker compose up` + curl) for the stand; the recorded picture for the shapes

**Target Platform**: one Linux host (`194.67.66.48`), Docker runtime, two subdomains of `aoa.run`

**Project Type**: deployment stand (containers + compose + deploy script) plus demonstrator fixture shapes

**Performance Goals**: N/A — an acceptance stand, not a production service

**Constraints**: containers reachable only through the host's front end; no second TLS front end; configuration and secrets out of the repository; deployment is one command with rollback; both containers survive a host restart

**Scale/Scope**: two containers, two virtual hosts, two certificates, one deploy script, one fixture domain group, one shape audit, one recorded picture

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. The maintainer decides | No commit, push or PR without an explicit instruction | PASS — planning writes nothing to git |
| II. English in code and history | All new files, scripts and comments in English | PASS — planned so |
| III. Module headers | New Python modules carry the standard header; scripts carry clear purpose comments | PASS — reserved in tasks |
| IV. AI-CORE blocks | Public classes in new fixtures carry ROLE/CONTRACT | PASS — planned |
| V. Short docstrings | One-line docstrings on new classes/methods | PASS — planned |
| VI. The last three steps | Exactly three tail tasks in order: check run → documentation → changelog | PASS — reserved for `/speckit-tasks` |

Re-check after Phase 1: no violations — the design adds containers, scripts and fixtures; it does not touch the constitution, the graph model or the check-run machinery.

## Project Structure

### Documentation (this feature)

```text
specs/004-demonstrator-stand/
├── plan.md              # This file
├── spec.md              # Feature specification (+ Clarifications session)
├── checklists/
│   └── requirements.md  # Spec quality checklist (16/16 passing)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── stand.md             # The deployment contract: commands, failure modes, picture manifest
│   └── shape-coverage.md    # The "all shapes" enumeration: kinds published vs drawn
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/aoa-demo/
├── Dockerfile                        # NEW: built from the repository, [fastapi]+[mcp] extras
└── src/aoa/demo/model/
    └── generalization_shapes/        # NEW: fixture domain for inheritance edges
        ├── __init__.py
        ├── generalization_shapes_domain.py
        ├── actions/                  # parent action + child actions (parent_action edges)
        └── entities/                 # parent entity + child entity (parent_entity edges)

packages/aoa-maxitor/
└── Dockerfile                        # REWRITE: build from sources, client build included

deploy/stand/
├── docker-compose.yml                # NEW: two services, own ports, healthchecks, restart policy
└── .env.example                      # NEW: named configuration placeholders (real values live on the host)

scripts/
└── deploy_demonstrator_stand.sh      # NEW: build → up → verify → rollback; DNS and terminator gates

packages/aoa-demo/tests/model/
└── test_generalization_shapes.py     # NEW: the fixture shapes exist in the graph
```

**Structure Decision**: Dockerfiles live beside their packages (the demo gains one, Maxitor's is rewritten); the stand's compose file and environment template live under `deploy/stand/`; the deploy script joins the existing `scripts/` checks. Real `.env` values never enter the repository.

## Complexity Tracking

No constitution violations — table intentionally empty.
