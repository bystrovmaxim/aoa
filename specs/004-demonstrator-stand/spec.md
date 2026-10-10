# Feature Specification: The demonstrator stand — dev.demo.aoa.run and dev.maxitor.aoa.run

**Feature Branch**: `feature/issue-202-demonstrator-stand-containers`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "The demonstrator stand: the demonstrator and Maxitor each in their own container on 194.67.66.48, reachable at dev.demo.aoa.run and dev.maxitor.aoa.run, built from this repository — so a feature can be accepted by looking at a diagram. It also carries the demonstrator's own shapes for generalization, which the diagram does not show today."

## Clarifications

### Session 2026-10-10

- Q: Which access to the host do we use for deployment — one of the two existing keys, or a key of its own? → A: Either of the two existing keys (`up2y-prod` / `digtwin-prod`), whichever one works — no separate key.

## User Scenarios & Testing *(mandatory)*

The reader of this feature is a maintainer or reviewer who wants to judge the framework by looking at a live diagram instead of reading a test report.

### User Story 1 - Maxitor serves the diagram, built from this repository (Priority: P1)

A viewer opens `dev.maxitor.aoa.run` and sees the Maxitor diagram whose client was built from this repository's sources — not the stale PyPI release the old Dockerfile installed.

**Why this priority**: the whole stand exists for looking at diagrams; if the client is not this repository's build, the acceptance is fake before it starts.

**Independent Test**: open `https://dev.maxitor.aoa.run`, confirm the diagram renders; inspect the image build to confirm it ran the client build from the sources in this repository.

**Acceptance Scenarios**:

1. **Given** a clean checkout of this repository, **When** the Maxitor image is built, **Then** it builds the client from the sources (`npm ci && npm run build`), never from a PyPI wheel.
2. **Given** the stand is deployed, **When** a viewer opens `dev.maxitor.aoa.run`, **Then** the Maxitor diagram renders.

---

### User Story 2 - The demonstrator serves the demo service (Priority: P1)

A viewer opens `dev.demo.aoa.run` and reaches the demonstrator service built from this repository with the `[fastapi]` and `[mcp]` extras.

**Why this priority**: the demonstrator is the other half of the stand; without it there is nothing for Maxitor to draw.

**Independent Test**: open `https://dev.demo.aoa.run`, confirm the service answers; inspect the image build to confirm it installed this repository with the `[fastapi]` and `[mcp]` extras and runs the declared entry point.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** the demonstrator image is built, **Then** it installs this repository with the `[fastapi]` and `[mcp]` extras.
2. **Given** the container runs, **When** a viewer opens `dev.demo.aoa.run`, **Then** the demonstrator service answers.

---

### User Story 3 - The stand's diagram shows the shapes it cannot draw today (Priority: P2)

A viewer of the stand's diagram sees the shapes the laptop demo does not show: generalization edges, the entity-specialization axis (once it lands), and every other node and edge kind the framework publishes that the diagram can render.

**Why this priority**: the stand is the place where "all shapes" must be true rather than intended; the picture is how that is judged.

**Independent Test**: open the recorded picture and identify each of the Part-1 shapes by sight.

**Acceptance Scenarios**:

1. **Given** the demonstrator model on the stand, **When** it is drawn, **Then** generalization shapes appear — inheritance edges are drawn at all.
2. **Given** entity specialization has landed in the repository, **When** the model is drawn, **Then** the specialization axis is visible in the same diagram.
3. **Given** any other node or edge kind the framework publishes, **When** the diagram renders, **Then** it is carried by the model or the gap is named, so "all shapes" is true rather than intended.

---

### User Story 4 - One host, two domains, TLS, and health (Priority: P2)

Both domains are served over HTTPS through the TLS front end that already runs on the host — two virtual hosts added to it, certificates issued and renewed automatically, each container on its own internal port reachable only through the front end, and a health check that makes a broken container visible instead of a hanging page.

**Why this priority**: the stand must fit beside what the host already serves, not replace it; a stand that breaks the host's other projects is worse than no stand.

**Independent Test**: open both domains over HTTPS; stop one container and confirm the stand reports it unhealthy rather than hanging.

**Acceptance Scenarios**:

1. **Given** the host's existing TLS front end, **When** the stand is deployed, **Then** two virtual hosts are added to it — no second front end is started.
2. **Given** both domains, **When** certificates are needed, **Then** they are issued and renewed automatically, not created by hand once.
3. **Given** the containers run, **When** either one breaks, **Then** its health check reports it, and the page does not hang.

---

### User Story 5 - Deployment is one command, with rollback (Priority: P3)

From a clean checkout, one command builds both images, runs both containers, verifies the stand, and rolls back on failure. Configuration and secrets are named and kept out of the repository. Both containers survive a restart of the host.

**Why this priority**: a stand that needs a human's checklist to deploy drifts the moment it is rebuilt; the command is the deployment's memory.

**Independent Test**: from a clean checkout on the host, run the single command; then restart the host (or the container runtime) and confirm both domains still answer.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** the deployment command runs, **Then** both images build, both containers start, and the stand is verified.
2. **Given** a failure during deployment, **When** the command detects it, **Then** it rolls back to the previous working state and reports the failure.
3. **Given** the stand is deployed, **When** the host restarts, **Then** both containers come back and both domains are reachable.
4. **Given** configuration and secrets, **When** they are stored, **Then** they are named and kept out of the repository.

---

### Edge Cases

- **The TLS front end is not yet identified.** The host serves other projects; before Part 3 the existing terminator must be known. Until it is, no virtual hosts can be added — the deployment must refuse with a clear message rather than guess.
- **The DNS names do not resolve yet.** The `A` records for the two names are outside this repository's reach. The deployment must fail clearly when the names do not resolve, never half-deploy.
- **The client build fails.** The Maxitor image build fails as a whole; the deployment command must roll back, leaving the previous containers running.
- **A container dies after deployment.** Its health check must mark it; the front end must show the failure instead of a hanging page.
- **A host restart.** Containers must come back with the host (restart policy), and both domains must be reachable afterwards.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Maxitor image MUST be built from this repository's sources, including the client build — never from a PyPI wheel.
- **FR-002**: The demonstrator image MUST be built from this repository with the `[fastapi]` and `[mcp]` extras.
- **FR-003**: The demonstrator container MUST serve the declared entry point — `uvicorn aoa.demo.fastapi_mcp_services.app_fastapi_service:app`.
- **FR-004**: Each service MUST run in its own container on its own internal port.
- **FR-005**: The two containers MUST be reachable only through the host's existing TLS front end; no second front end MAY be started.
- **FR-006**: TLS certificates for both names MUST be issued and renewed automatically.
- **FR-007**: Both services MUST expose health checks; a broken container MUST be visible, never a hanging page.
- **FR-008**: The demonstrator model MUST include generalization shapes — elements producing inheritance edges — so the diagram draws them at all.
- **FR-009**: Once entity specialization has landed, the stand MUST show the specialization axis in the same diagram.
- **FR-010**: The stand MUST carry every other node or edge kind the framework publishes that the diagram can render — "all shapes" true, not merely intended; any kind that cannot be shown MUST be named as a gap.
- **FR-011**: The drawn diagram on the stand MUST be recorded as a picture, the same way issue #201 records it.
- **FR-012**: Deployment MUST be a single command from a clean checkout: build both images, run both containers, verify, and roll back on failure.
- **FR-013**: Configuration and secrets MUST be named and kept out of the repository.
- **FR-014**: Both containers MUST survive a restart of the host and be reachable after it.

### Key Entities

- **Demonstrator container** — the demo service built from this repository (`[fastapi]` and `[mcp]` extras), its own internal port, health check, restart policy.
- **Maxitor container** — the Maxitor service with the client built from this repository's sources, its own internal port, health check, restart policy.
- **Front-end virtual hosts** — two entries added to the host's existing TLS terminator, one per domain, with issued-and-renewed certificates.
- **Deployment script** — the single command: build, run, verify, roll back; reads named configuration and secrets from outside the repository.
- **Recorded picture** — the diagram of the stand's model, showing every Part-1 shape.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `https://dev.maxitor.aoa.run` serves Maxitor with the client built from this repository, and the diagram renders.
- **SC-002**: `https://dev.demo.aoa.run` serves the demonstrator built from this repository.
- **SC-003**: The recorded picture shows every Part-1 shape: generalization, the specialization axis, and every other renderable kind — or names the gap.
- **SC-004**: Both containers are reachable after a restart of the host.
- **SC-005**: The deployment completes with one command from a clean checkout, including rollback on failure, and that command is written down.

## Assumptions

- The target host is `194.67.66.48` (given by the issue), and it already serves other projects.
- **Host access:** either of the two existing SSH keys (`up2y-prod` / `digtwin-prod`), whichever one works, is used for this work — no separate key is created.
- **DNS (open question 2):** the `A` records for both `aoa.run` names are created by whoever manages the zone, before acceptance.
- **Front end (open question 3):** the TLS terminator already running on the host is identified first; the stand extends it, never replaces it.
- Entity specialization (issue #199) has landed in the repository by the time FR-009 is verified; until then the axis shape is recorded as a named gap.
- Production hardening, monitoring, and a CI job that deploys on merge are out of scope — this stand is for acceptance, and a deployment pipeline is a separate decision.
- The shape work (Part 1) is verified the same way as issue #201: the model builds, and the picture is recorded.
