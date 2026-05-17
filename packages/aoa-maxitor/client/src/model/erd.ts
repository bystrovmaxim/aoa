// src/model/erd.ts
/** ERD API response contracts consumed by the browser-side ERD viewer. */
export type DomainInfoRow = {
  qualname: string;
  /** Interchange graph ``domain.label`` (human-readable; same idea as list-entities ``domain_label``). */
  label: string;
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

/** Batch response from ``GET /api/v1/list-entities`` (one graph scan, multiple slices). */
export type ErdDomainsBatchPayload = {
  domain_slices: ErdDomainPayload[];
};
