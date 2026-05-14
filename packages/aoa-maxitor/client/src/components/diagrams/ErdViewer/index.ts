/**
 * ERD viewer package surface — narrow barrel (§7): React exports only; import `@/api/*`, `@/lib/*`, `@/components/ui/*` directly elsewhere.
 */

export { ErdViewer } from "./ErdViewer";
export type { ErdViewerSelection } from "@/lib/loadErdDomainsBundle";
export { ErdGraphvizCanvas } from "./parts/ErdGraphvizCanvas";
export type { ErdGraphvizCanvasProps } from "./parts/ErdGraphvizCanvas";
