<p align="center">
  <img src="../../../docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript 5.7"></a>
  <img src="https://img.shields.io/badge/Vite-build-646cff?logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/Node.js-22-339933?logo=node.js&logoColor=white" alt="Node 22">
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="../README.md"><img src="https://img.shields.io/badge/backend-aoa--maxitor-blue?logo=python&logoColor=white" alt="aoa-maxitor"></a>
</p>

# Maxitor client

Vite + React + TypeScript SPA for diagram workspaces (full graph / ERD). Import alias: `@/` → [`src/`](./src/).

## Source layers (`src/`)

| Layer | Role |
|-------|------|
| **`app/`** | Application glue only: [`App.tsx`](./src/app/App.tsx), [`providers/AppProviders.tsx`](./src/app/providers/AppProviders.tsx). No product widgets here. |
| **`components/`** | All UI blocks (layout, pages, navigation, `ui/`, `diagrams/`). Each **exported** PascalCase folder has `index.ts` + `README.md`; small private helpers may live as sibling `.tsx` files inside that folder (§1). Nested `hooks/` and `parts/` stay colocated (plan §4). |
| **`api/`** | HTTP clients (`fetch`), no JSX — names mirror FastAPI handlers / ``/api/v1`` routes ([`getSidebar`](./src/api/sidebar.ts), [`listDomains`](./src/api/erd.ts), [`listEntities`](./src/api/erd.ts), [`fullGraph`](./src/api/fullGraph.ts)); see [`client.ts`](./src/api/client.ts). |
| **`model/`** | Shared TypeScript contracts between UI and API (`diagramSelection`, `fullGraph`, `erd`, `sidebar`). |
| **`lib/`** | Pure helpers and **layout constants** (e.g. [`layoutConstants.ts`](./src/lib/layoutConstants.ts)) — not React components; also [`pageSettings.ts`](./src/lib/pageSettings.ts), the one way a viewer reads and sets its filters and layout mode: per page for the tab, shared inside a room; and [`freshGraph.ts`](./src/lib/freshGraph.ts), which redraws an open page in place when its model changes. |
| **`lib/prefetch/`** | Fire-and-forget chunk warmers (`g6Prefetch`, `erdGraphviz` / Graphviz WASM). |
| **`rooms/`** | Looking at one service together (spec 028): the room connection with its reconnects ([`connection.ts`](./src/rooms/connection.ts)), the room rebuilt from server events ([`roomStore.ts`](./src/rooms/roomStore.ts)), the tab's session ([`useRoomSession.ts`](./src/rooms/useRoomSession.ts)), the diagram on screen as one surface for all four viewers ([`diagramSurface.ts`](./src/rooms/diagramSurface.ts), [`coordinates.ts`](./src/rooms/coordinates.ts)), pointers sent at most 20 and screens 10 times a second ([`usePointerSender.ts`](./src/rooms/usePointerSender.ts)), going to someone ([`goTo.ts`](./src/rooms/goTo.ts)), following ([`follow.ts`](./src/rooms/follow.ts), [`followCircle.ts`](./src/rooms/followCircle.ts)), the picture check ([`pageCheck.ts`](./src/rooms/pageCheck.ts)), and the room UI — `RoomBar`, `Circles`, `ParticipantCard`, `NameDialog`, `InviteCard`, `PointerLayer`, `FollowFrame`, each with `index.ts` + `README.md` like a component. |
| **`styles/`** | Theme and global styling hooks for providers ([`theme.ts`](./src/styles/theme.ts)). |

Heavier rules (folder naming, barrels, README template) live in **[`archive/plan/018.md`](../../archive/plan/018.md)** — sections **§2–§6** are the contract for new work.

## Scripts

```bash
npm install   # or npm ci in CI
npm run dev
npm run build
```

Component README policy (`src/components/*/*/index.ts` → `README.md`) is enforced by the repo script **`scripts/run_checks_with_log.sh`** at the workspace root (plan archive §9.1).
