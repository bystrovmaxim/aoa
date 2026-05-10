// packages/aoa-maxitor/client/src/features/model/types.ts
/** Shared shell types: sidebar selection targets and diagram payloads. */
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
