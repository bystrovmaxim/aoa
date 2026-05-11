// packages/aoa-maxitor/client/src/features/diagrams/erd/model/types.ts
/** ERD API response contracts consumed by the browser-side ERD viewer. */
export type DomainInfoRow = {
  qualname: string;
  color: string;
};

export type DomainQualnamesPayload = {
  domain_info: DomainInfoRow[];
};

export type ErdDomainPayload = {
  domain_label: string;
  domain_qualifier: string;
  graph: {
    entities: Array<Record<string, unknown>>;
    relations: Array<Record<string, unknown>>;
  };
};
