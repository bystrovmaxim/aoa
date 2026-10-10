# Quickstart: validating the demonstrator stand

Runnable validation for the feature, in two stages: everything that can be proven locally, then the host steps.

## Prerequisites

- Docker with Compose on the machine running the validation.
- Node toolchain for the Maxitor client build (the image builds it inside Docker, so the local machine does not need it).
- For the host stage: SSH access with either existing key, and the DNS names resolving.

## 1. The model still builds and the shapes exist

```bash
uv run --extra dev pytest packages/aoa-demo/tests/ -q
```

**Expected**: zero failures. The `generalization_shapes` fixtures exist in the graph — asserted by `packages/aoa-demo/tests/model/test_generalization_shapes.py` (parent action with two children via `parent_action` edges; parent entity with a child via `parent_entity`).

## 2. Both images build from the repository

```bash
docker compose -f deploy/stand/docker-compose.yml build
```

**Expected**: two images build from the repository sources — the demo with the `[fastapi]`/`[mcp]` extras, Maxitor with the client built inside the image. No `aoa-*` package is installed from PyPI.

## 3. Both containers come up and answer

```bash
docker compose -f deploy/stand/docker-compose.yml up -d
curl -fsS http://127.0.0.1:8100/health
curl -fsS http://127.0.0.1:8100/api/v1/ping
curl -fsS http://127.0.0.1:8101/api/health
```

**Expected**: the demo answers on 8100 (`/health` → `{"status":"ok"}`, `/api/v1/ping` → `{"message":"pong"}`), Maxitor answers on 8101 (`/api/health` → `{"status":"ok"}`); `docker compose ps` shows both healthy.

## 4. The shape audit is filled

```bash
uv run --extra dev python scripts/stand_shape_audit.py
```

**Expected**: the script prints and writes `specs/004-demonstrator-stand/contracts/shape-coverage.md` — every published node/edge kind marked `carried & drawn` or `named gap`, with the specialization axis named until #199 lands.

## 5. The picture is recorded

Generate the DOT and the WASM-rendered SVG for the use-case diagram and the ERD slice (the same builders as issue #201), save them to `specs/004-demonstrator-stand/contracts/`, and verify by eye against `contracts/stand.md`: generalization edges visible, every label names its shape.

## 6. Host deployment (the real acceptance)

```bash
bash scripts/deploy_demonstrator_stand.sh
```

**Expected**, in order: the DNS and terminator gates pass; both images build; both containers start; healthchecks go green; both `https://` domains answer; on any failure the previous stand is restored. Then restart the host (or the container runtime) and confirm both domains are reachable — the `restart: unless-stopped` policy is what carries this.

## 7. Record the stand's picture

Capture `stand-use-case.png` and `stand-erd.png` from the live stand (the browser look-at evidence) and commit them beside the generated DOT/SVG under `contracts/`.
