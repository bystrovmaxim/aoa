// packages/aoa-maxitor/client/src/features/index.ts
/**
 * Maxitor UI — re-exports diagrams workspace, sidebar, and shared model types for app composition.
 */

export { MainDiagramView } from "./diagrams/main_diagram_view";
export type { DiagramSelection, DomainQualnamesPayload, ErdDomainPayload } from "./model/types";
export * from "./diagrams/erd";
export * from "./diagrams/interchange_graph";

export { SidebarNav } from "./sidebar/sidebar_nav";
export { buildSidebarGroupedMaps } from "./sidebar/model";
export { useSidebarPayload } from "./sidebar/use_sidebar_payload";
