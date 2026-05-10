// packages/aoa-maxitor/client/src/features/diagram-viewer/model/types.ts
/** How the main workspace renders the selected sidebar diagram target. */
export type DiagramSelection =
  | { kind: "interchange_graph" }
  | { kind: "erd"; qualifier: string | null };

export type DomainQualnamesPayload = {
  domain_qualnames: string[];
};

export type ErdDomainPayload = {
  domain_label: string;
  domain_qualifier: string;
  graph: {
    nodes: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
  };
};
