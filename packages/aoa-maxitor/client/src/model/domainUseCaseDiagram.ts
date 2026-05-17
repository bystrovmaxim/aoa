// src/model/domainUseCaseDiagram.ts
/** Wire shape for ``GET /api/v1/domain-use-case-diagram`` (``GetDomainUseCaseDiagramAction.Result``). */

export type DomainUseCaseDomainWire = {
  id: string;
  label: string;
  short_label: string;
  accent_color: string;
};

export type DomainUseCaseActionWire = {
  id: string;
  label: string;
  short_label: string;
  domain_id: string;
  domain_short_label: string;
  accent_color: string;
  /** Role vertex ids from ``@check_roles`` (sorted); may be empty. */
  role_ids: string[];
};

export type DomainUseCaseRoleWire = {
  id: string;
  label: string;
  short_label: string;
};

export type DomainUseCaseEdgeKind =
  | "action_generalization"
  | "role_generalization"
  | "association"
  | "include"
  | "extend"
  | "depends";

export type DomainUseCaseEdgeWire = {
  edge_kind: DomainUseCaseEdgeKind;
  source_id: string;
  target_id: string;
  stereotype?: string | null;
};

export type DomainUseCaseDiagramPayload = {
  domain: DomainUseCaseDomainWire;
  actions: DomainUseCaseActionWire[];
  roles: DomainUseCaseRoleWire[];
  edges: DomainUseCaseEdgeWire[];
};
