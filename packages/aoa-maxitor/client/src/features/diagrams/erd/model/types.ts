// packages/aoa-maxitor/client/src/features/diagrams/erd/model/types.ts
/** ERD API response contracts consumed by the browser-side ERD viewer. */
export type DomainInfoRow = {
  qualname: string;
  color: string;
};

export type DomainQualnamesPayload = {
  list_domains: DomainInfoRow[];
};

export type ErdDomainPayload = {
  domain_label: string;
  domain_qualname: string;
  list_entities: {
    entities: Array<Record<string, unknown>>;
    relations: Array<Record<string, unknown>>;
  };
};
