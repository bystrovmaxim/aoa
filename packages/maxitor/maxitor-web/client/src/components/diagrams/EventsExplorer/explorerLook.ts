// src/components/diagrams/EventsExplorer/explorerLook.ts
/** The colours and icons of the explorer: kinds of node, standings of an event, kinds of method, the two-row sections. */
import { svgDataUriForGraphNodeIcon, svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import type { EventStatus } from "@/lib/eventsExplorer";

export const EVENT_COLOUR = "#d97706";
export const SLATE = "#64748b";
/** What is grey while another section paints. */
export const NEUTRAL = "#94a3b8";

export const KIND_ICON = {
  domain: svgDataUriForInterchangeDomainLegend("#3b82f6"),
  event: svgDataUriForGraphNodeIcon(EVENT_COLOUR, "Event"),
  action: svgDataUriForGraphNodeIcon(SLATE, "Action"),
};

/** The colour of each standing of an event, when the events paint the diagram. */
export const STATUS_COLOUR: Record<EventStatus, string> = { emitted_held: EVENT_COLOUR, emitted_free: "#7c3aed", not_emitted: NEUTRAL };
export const STATUS_LABEL: Record<EventStatus, string> = { emitted_held: "In vocabulary, emitted", emitted_free: "Emitted, no vocabulary", not_emitted: "In vocabulary, not emitted" };

/** The colour of each kind of method, when the methods paint the diagram. */
export const METHOD_COLOUR: Record<string, string> = { RegularAspect: "#2563eb", SummaryAspect: "#059669", Compensator: "#db2777", ErrorHandler: "#dc2626", AccessDecide: "#0891b2" };
export const METHOD_LABEL: Record<string, string> = { RegularAspect: "Regular aspect", SummaryAspect: "Summary aspect", Compensator: "Compensator", ErrorHandler: "Error handler", AccessDecide: "Access decision" };

/** Domains with and without events, actions with and without events. */
export const COVERAGE_COLOUR = { with: EVENT_COLOUR, without: "#cbd5e1" };
export const ACTION_COLOUR = { with: "#475569", without: "#cbd5e1" };
