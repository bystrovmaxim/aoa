// packages/aoa-maxitor/client/src/features/diagrams/erd/model/types.ts
/** ERD API response contracts consumed by the browser-side ERD viewer. */
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
