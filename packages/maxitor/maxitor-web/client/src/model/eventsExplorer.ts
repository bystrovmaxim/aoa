// src/model/eventsExplorer.ts
import type { DiffStatus } from "@/api/compare";

/** Wire shape for ``GET /api/v1/events-explorer`` (spec 055); ``diff`` is set by the client in Diff. */

export type ExplorerDomainWire = { id: string; label: string; short_label: string; accent_color: string; vocabulary: boolean; diff?: DiffStatus };

export type ExplorerActionWire = { id: string; label: string; short_label: string; domain_id: string; diff?: DiffStatus };

export type ExplorerFieldWire = { name: string; type: string; description: string };

export type ExplorerEventWire = { id: string; label: string; fields: ExplorerFieldWire[]; diff?: DiffStatus };

export type ExplorerHoldWire = { domain_id: string; event_id: string; diff?: DiffStatus };

export type ExplorerEmitWire = { action_id: string; method_id: string; method: string; kind: string; event_id: string; diff?: DiffStatus };

export type EventsExplorerPayload = { domains: ExplorerDomainWire[]; actions: ExplorerActionWire[]; events: ExplorerEventWire[]; holds: ExplorerHoldWire[]; emits: ExplorerEmitWire[] };
