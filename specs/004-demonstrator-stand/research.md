# Phase 0 Research: The demonstrator stand

Findings from the repository, with decisions. Host-side unknowns that only the deployment time can answer are recorded as **deployment-time gates** — the deploy script asserts them instead of assuming them.

## Decision 1: Images build from the repository via the uv workspace

- **Decision**: both Dockerfiles use the repository root as build context and install the local packages with `uv sync` from the workspace — the demo with `--extra fastapi --extra mcp`, Maxitor with its own extras. No image installs any `aoa-*` package from PyPI.
- **Rationale**: the pyprojects declare `aoa-action-machine = { workspace = true }` (uv workspace); PyPI cannot provide this repository's code, and the old Maxitor Dockerfile's `pip install aoa-maxitor==1.1.6` is exactly the stale-release trap the issue forbids.
- **Alternatives considered**: per-package build contexts with path dependencies (breaks the workspace graph); `pip install .` inside the image (misses the workspace members).

## Decision 2: The Maxitor image is multi-stage, client build included

- **Decision**: stage 1 — a Node image runs `cd packages/aoa-maxitor/client && npm ci && npm run build`; stage 2 — a Python 3.12 image runs `uv sync` for the workspace and copies the built client into the image; the container serves the Maxitor API.
- **Rationale**: the API without the built client "is an API and not a diagram" (issue); the client build needs Node, the runtime does not — multi-stage keeps the runtime image slim.
- **Alternatives considered**: building the client on the host before `docker build` (breaks "one command from a clean checkout"); shipping Node in the runtime image (needless weight).

## Decision 3: The demo image serves the declared entry point

- **Decision**: `packages/aoa-demo/Dockerfile` installs the workspace with the `[fastapi]` and `[mcp]` extras and runs `uvicorn aoa.demo.fastapi_mcp_services.app_fastapi_service:app --host 0.0.0.0 --port 8100` (FR-003).
- **Rationale**: the issue names the entry point; the port is internal to the container.
- **Alternatives considered**: a compose-level `command:` instead of a Dockerfile `CMD` (the image should be runnable on its own, the compose file just wires it).

## Decision 4: Compose with healthchecks, restart policy, no published ports

- **Decision**: `deploy/stand/docker-compose.yml` defines two services on internal ports 8100 (demo) and 8101 (Maxitor), bound to the host's loopback only (127.0.0.1), each with a `healthcheck`, `restart: unless-stopped`, and `stop_grace_period`. Only the host's front end proxies the two domains to these ports (FR-004, FR-005, FR-007, FR-014).
- **Rationale**: loopback-only publishing keeps "reachable only through the front end" true; `restart: unless-stopped` is what "survive a host restart" means in Compose.
- **Health endpoints**: the demo's `GET /ping` and Maxitor's API root/health route — exact paths verified at implementation and written into the compose file.
- **Alternatives considered**: systemd units per container (more host coupling than one compose file); publishing ports on 0.0.0.0 (violates FR-005).

## Decision 5: TLS and DNS are gates, not assumptions

- **Decision**: the deploy script first asserts both names resolve (DNS gate) and that the host's existing TLS terminator can be detected (terminator gate); only then does it add the two virtual hosts and request certificates through the terminator's own renew mechanism (Let's Encrypt via the terminator). A failed gate prints the exact missing prerequisite and exits before touching anything.
- **Rationale**: the zone and the existing front end are outside this repository's reach; guessing either would half-deploy the stand. The script's job is to refuse clearly, not to invent.
- **Alternatives considered**: bundling our own TLS front end (explicitly forbidden — no second front end); hand-made certificates (forbidden — issued and renewed automatically).

## Decision 6: One deployment command with rollback

- **Decision**: `scripts/deploy_demonstrator_stand.sh` runs, in order: (1) DNS/terminator gates, (2) `docker compose build` for both images, (3) `docker compose up -d`, (4) healthcheck polling for both containers, (5) `curl` verification of both domains, (6) on any failure — roll back: restore the previously running images and containers, then report. Configuration and secrets are read from `/etc/aoa-stand.env` on the host (named, outside the repository); `deploy/stand/.env.example` documents the names.
- **Rationale**: the issue demands one command, verification, rollback, and secrets out of the repo; a step list with a rollback branch is the smallest honest form.
- **Alternatives considered**: a Makefile target (same script, more indirection); CI-only deployment (explicitly out of scope).

## Decision 7: Generalization fixtures live in a dedicated domain

- **Decision**: a new `generalization_shapes` domain in the demo model, with one parent action and two child actions (drawn as `parent_action` generalization edges) and one parent entity with a child entity (drawn as `parent_entity` edges). Descriptions name the shape they produce, exactly like the access-cascade fixtures of issue #201. The demo currently carries no `parent_action` fixtures — the grep over `packages/aoa-demo/src` found none.
- **Rationale**: the use-case diagram already renders `parent_action` (its Maxitor test draws exactly that edge), and the ERD renders `parent_entity`; what is missing is fixtures in the demo model, not drawing capability. A dedicated domain keeps the drawing diff clean, as in issue #201.
- **Alternatives considered**: extending the `access_cascade` domain (wrong story — generalization is its own shape); touching existing demo domains (violates the untouched-content pattern).

## Decision 8: The specialization axis is carried, not a gap

- **Decision**: issue #199 has already landed in main, so the generalization entity fixtures declare the specialization directly — a head with its axis and two extensions. The stand therefore shows both the `entity_specialization` axis and the `parent_entity` inheritance edges (FR-009 satisfied, not deferred).
- **Rationale**: `ParentEntityGraphEdge` is emitted only for specialization extensions (an extension → its head), never for plain `BaseEntity` subclassing — the fixture must use the specialization declaration to produce the shape.
- **Alternatives considered**: plain entity inheritance (produces no edge at all — verified against the built graph); waiting for #199 (unnecessary — it is in main).

## Decision 9: "All shapes" is an audit artifact

- **Decision**: the audit enumerates the interchange graph's published node and edge kinds (from `NodeGraphCoordinator.get_available_types()`), marks each as carried-by-the-demo and drawn-by-the-diagram (or names the gap), and the result is committed as `contracts/shape-coverage.md`. The recorded picture (DOT + SVG + browser PNG, the same way as #201) shows the stand's diagram.
- **Rationale**: "all shapes is true rather than intended" needs a checkable enumeration; a committed table is the check.
- **Alternatives considered**: a runtime test asserting the enumeration (fragile against graph-model additions); prose-only claims (not checkable).

## Decision 10: Host facts remain outside the repository

- **Decision**: SSH access uses either existing host key (`up2y-prod` / `digtwin-prod`), whichever works (Clarification Q1); the DNS records and the terminator identity are host facts the deploy script gates on. None of them is written into the repository.
- **Rationale**: the issue's open questions 2 and 3 are outside the repo's reach; the script asserts, never assumes.
