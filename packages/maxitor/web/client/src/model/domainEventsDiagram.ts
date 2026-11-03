// src/model/domainEventsDiagram.ts
import type { DiffStatus } from "@/api/compare";

/** Wire shape for ``GET /api/v1/domain-events-diagram`` and ``/api/v1/events-diagram`` (spec 053). */

export type EventBand = "in_vocabulary" | "not_emitted" | "emitted";

export type EventsDomainWire = {
  id: string;
  label: string;
  short_label: string;
  accent_color: string;
  /** Whether the domain has a vocabulary; ``null`` on the diagram of all domains. */
  typed_events: boolean | null;
  /** In Diff: A's answer, when it differs from B's. */
  typed_events_was?: boolean;
};

export type EventsActionWire = { id: string; label: string; short_label: string; domain_id: string; domain_short_label: string; accent_color: string; diff?: DiffStatus };

export type EventsMethodWire = { id: string; label: string; kind: string; action_id: string; diff?: DiffStatus };

export type EventFieldWire = { name: string; type: string; description: string };

export type EventProducerWire = { id: string; label: string; kind: string; action_id: string; action_label: string };

export type EventDomainWire = { id: string; label: string; in_vocabulary: boolean };

export type EventWire = { id: string; label: string; band: EventBand; fields: EventFieldWire[]; methods: EventProducerWire[]; domains: EventDomainWire[]; diff?: DiffStatus };

export type EventsEdgeWire = { id: string; edge_kind: "method" | "emits"; source_id: string; target_id: string; diff?: DiffStatus };

export type DomainEventsDiagramPayload = { domain: EventsDomainWire; actions: EventsActionWire[]; methods: EventsMethodWire[]; events: EventWire[]; edges: EventsEdgeWire[] };
