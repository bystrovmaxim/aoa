# aoa-maxitor

Publishable distribution for the `aoa.maxitor` namespace (samples and visualization).

See the [repository README](https://github.com/action-machine/action-machine/blob/main/README.md) for the full project.

## React SPA + FastAPI API

Maxitor is split into a standard Vite React frontend and a FastAPI backend.

### Backend API

```bash
uv run task maxitor-api
```

This starts `aoa.maxitor.api.app:app` on `http://127.0.0.1:8000`.

**Local dev (two processes):** terminal A — `uv run task maxitor-api` (or `uv run maxitor-api` from the package); terminal B — `cd packages/aoa-maxitor/client && npm run dev`, then open `http://127.0.0.1:5173`.

Environment for the `maxitor-api` console script: `MAXITOR_API_HOST` (default `127.0.0.1`), `MAXITOR_API_PORT` (default `8000`). The repo `task maxitor-api` uses uvicorn with `--reload` on port 8000.

- `GET /api/health` returns API health.
- `GET /api/sidebar` returns navigation rows for the sidebar.
- `GET /api/v1/full-graph` returns interchange graph JSON for the React G6 viewer.
- `GET /api/v1/list-domains` returns domain qualnames with accent colours; `GET /api/v1/list-entities` returns ERD entity slices (repeat ``domain_qualnames`` as query params).

Diagram viewers in the SPA are plain React: G6 for the interchange graph and `@hpcc-js/wasm-graphviz` for ERD (no iframe shell).

### React frontend

Local development:

```bash
cd packages/aoa-maxitor/client
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000` by default. For production hosting,
build the SPA and point it at the deployed API:

```bash
VITE_MAXITOR_API_BASE_URL=https://api.example.com npm run build
```

### React source layout (`client/src`)

- `app/` — application composition: root shell (`app.tsx`), providers, layout, and app-level views such as `views/main_diagram_view.tsx`.
- `features/diagram_selection/` — shared selection contract between navigation and the app-level diagram view.
- `features/diagrams/` — diagram rendering features only: `interchange_graph/` and `erd/`.
- `features/diagrams/erd/model/` — ERD API payload contracts.
- `features/maxitor_navigation/` — current left navigation feature (`api/`, `model/`, `ui/`) backed by `/api/sidebar`.
- `features/index.ts` — public feature barrel for app composition.
- `shared/` — theme, API config, and layout constants.
