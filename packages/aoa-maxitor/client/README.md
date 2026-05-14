# Maxitor client

Vite + React + TypeScript SPA for diagram workspaces (full graph / ERD). Import alias: `@/` → [`src/`](./src/).

## Source layers (`src/`)

| Layer | Role |
|-------|------|
| **`app/`** | Application glue only: [`App.tsx`](./src/app/App.tsx), [`providers/AppProviders.tsx`](./src/app/providers/AppProviders.tsx). No product widgets here. |
| **`components/`** | All UI blocks (layout, pages, navigation, `ui/`, `diagrams/`). Each **exported** PascalCase folder has `index.ts` + `README.md`; small private helpers may live as sibling `.tsx` files inside that folder (§1). Nested `hooks/` and `parts/` stay colocated (plan §4). |
| **`api/`** | HTTP clients (`fetch`), no JSX — [`client.ts`](./src/api/client.ts), domain modules (`erd.ts`, `fullGraph.ts`, `sidebar.ts`). |
| **`model/`** | Shared TypeScript contracts between UI and API (`diagramSelection`, `fullGraph`, `erd`, `sidebar`). |
| **`lib/`** | Pure helpers and **layout constants** (e.g. [`layoutConstants.ts`](./src/lib/layoutConstants.ts)) — not React components. |
| **`lib/prefetch/`** | Fire-and-forget chunk warmers (`g6Prefetch`, `erdGraphviz` / Graphviz WASM). |
| **`styles/`** | Theme and global styling hooks for providers ([`theme.ts`](./src/styles/theme.ts)). |

Heavier rules (folder naming, barrels, README template) live in **[`archive/plan/018.md`](../../archive/plan/018.md)** — sections **§2–§6** are the contract for new work.

## Scripts

```bash
npm install   # or npm ci in CI
npm run dev
npm run build
```

Component README policy (`src/components/*/*/index.ts` → `README.md`) is enforced by the repo script **`scripts/run_checks_with_log.sh`** at the workspace root (plan archive §9.1).
