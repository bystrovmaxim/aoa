// packages/aoa-maxitor/client/src/features/diagrams/erd/index.ts
/**
 * ERD viewer: list-domains / list-entities JSON plus in-browser Graphviz (React).
 */

export { ErdViewer } from "./components/erd_viewer";
export type { ErdViewerSelection } from "./lib/load_erd_domains_bundle";
export { ErdGraphvizCanvas } from "./components/erd_graphviz_canvas";
export type { ErdGraphvizCanvasProps } from "./components/erd_graphviz_canvas";
export { DomainLegend } from "./components/domain_legend";
export type { DomainLegendProps } from "./components/domain_legend";
export { OneHopToggle } from "./components/one_hop_toggle";
export type { OneHopToggleProps } from "./components/one_hop_toggle";
export {
  buildDotSource,
  erdGraphvizEngine,
  type ErdEntity,
  type ErdField,
  type ErdGraphPayload,
  type ErdGraphvizLayout,
  type ErdRelation,
} from "./lib/build_dot_source";
export { loadGraphvizWasm, prefetchErdGraphviz } from "./hooks/use_graphviz";
export { enrichErdDataForViewer } from "./lib/enrich_erd_data";
export { allocateDomainTabKey } from "./lib/domain_tab_keys";
export { fetchErdDomainPayload, fetchErdDomainsBatch, fetchErdDomainQualnames } from "./api/erd_api";
export type { ErdDomainsBundle, ErdDomainSliceRequest } from "./lib/load_erd_domains_bundle";
export { loadErdDomainsBundle, loadErdDomainSlicesBundle } from "./lib/load_erd_domains_bundle";
