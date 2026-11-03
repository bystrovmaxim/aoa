// src/components/diagrams/EventsExplorer/ExplorerNode.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Tooltip from "@mui/material/Tooltip";
import type { ReactElement } from "react";
import { MARK_LOOK } from "@/lib/erdDiffCard";
import { svgDataUriForGraphNodeIcon, svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import { BODY_H, BODY_W, idOf, kindOf, type EventsGraph, type Paint, type Port, type PortKind } from "@/lib/eventsExplorer";
import { ACTION_COLOUR, COVERAGE_COLOUR, EVENT_COLOUR, KIND_ICON, METHOD_COLOUR, NEUTRAL, SLATE, STATUS_COLOUR } from "./explorerLook";

const PORT_ICON: Record<PortKind, string> = {
  events: KIND_ICON.event,
  actions: KIND_ICON.action,
  domains: svgDataUriForInterchangeDomainLegend(NEUTRAL),
  domain: svgDataUriForInterchangeDomainLegend(NEUTRAL),
};
const PORT_WORDS: Record<PortKind, string> = { events: "events", actions: "actions", domains: "domains", domain: "its domain" };

/** What a domain says of its events: its vocabulary's size, or what its actions emit without one (spec 055, US1). */
function DomainLine({ graph, id }: { graph: EventsGraph; id: string }) {
  const { vocabulary, emittedOnly } = graph.domainCounts(id);
  const chip = (text: string, solid: boolean) => (
    <Box component="span" sx={{ display: "inline-flex", alignItems: "center", height: 17, px: "6px", borderRadius: 999, fontSize: 10.5, fontWeight: 500, whiteSpace: "nowrap", color: solid ? "#92400e" : "#b45309", bgcolor: solid ? "#fef3c7" : "transparent", border: solid ? "1px solid #fde68a" : "1px dashed #f59e0b" }}>
      {text}
    </Box>
  );
  if (vocabulary !== null) return vocabulary === 0 ? chip("empty vocabulary", false) : chip(`${vocabulary} in vocabulary`, true);
  if (emittedOnly > 0) return chip(`${emittedOnly} emitted · no vocabulary`, false);
  return (
    <Box component="span" sx={{ fontSize: 10.5, color: NEUTRAL }}>
      no events
    </Box>
  );
}

/** Painted by the methods: a strip down the node's left edge, one band per kind of method behind it. */
function KindStrip({ kinds }: { kinds: readonly string[] }) {
  if (kinds.length === 0) return null;
  return (
    <Box aria-hidden data-testid="explorer-kind-strip" sx={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 5, display: "flex", flexDirection: "column", borderRadius: "9px 0 0 9px", overflow: "hidden" }}>
      {kinds.map((kind) => (
        <Box key={kind} sx={{ flex: 1, bgcolor: METHOD_COLOUR[kind] }} />
      ))}
    </Box>
  );
}

export type ExplorerNodeProps = {
  graph: EventsGraph;
  node: string;
  hot: boolean;
  paint: Paint | "changes";
  /** In Diff, what the comparison says of the node; painted by the changes, it takes its mark's colour. */
  change?: string;
  /** The kinds of method behind the node, for the paint by methods. */
  kinds: readonly string[];
  onClick: () => void;
  onHover: (on: boolean, x: number, y: number) => void;
};

/** A node's body: no frame around anything, an icon, its name, and what the paint gives it. */
export function ExplorerNode({ graph, node, hot, paint, change, kinds, onClick, onHover }: ExplorerNodeProps): ReactElement {
  const kind = kindOf(node);
  const id = idOf(node);
  const label = graph.label(node);
  const methodFrame = paint === "methods" && kinds.length === 1 ? METHOD_COLOUR[kinds[0]] : null;
  const strip = paint === "methods" ? <KindStrip kinds={kinds} /> : null;
  const marked = change === "added" || change === "removed" || change === "changed" ? MARK_LOOK[change].colour : null;
  // Painted by the changes, a node's frame and icon take its mark's colour, an unchanged one grey.
  const changeColour = paint === "changes" ? (marked ?? "#cbd5e1") : null;
  const common = {
    position: "absolute" as const,
    left: 0,
    top: 0,
    width: BODY_W,
    height: BODY_H[kind],
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-start",
    gap: "9px",
    px: "11px",
    textAlign: "left" as const,
    borderRadius: kind === "domain" ? "14px" : "10px",
    cursor: "pointer",
    boxShadow: hot ? "0 6px 18px rgba(15,23,42,0.16)" : "0 1px 3px rgba(15,23,42,0.08)",
    transition: "box-shadow 140ms, border-color 200ms, background-color 200ms",
  };
  const pointer = (enter: boolean) => (event: React.MouseEvent) => onHover(enter, event.clientX, event.clientY);
  const events = { onClick, onMouseEnter: pointer(true), onMouseMove: pointer(true), onMouseLeave: pointer(false), "data-testid": "explorer-node", "data-node": node };
  const name = (sx: object = {}) => <Box sx={{ fontSize: 12.5, color: "#0f172a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", ...sx }}>{label}</Box>;

  if (kind === "domain") {
    const domain = graph.domains.get(id);
    const quiet = !graph.withEvents(id);
    const coverage = COVERAGE_COLOUR[quiet ? "without" : "with"];
    const disk = changeColour ?? (paint === "domains" ? (domain?.accent_color ?? "#3b82f6") : paint === "coverage" ? coverage : NEUTRAL);
    return (
      <ButtonBase {...events} sx={{ ...common, bgcolor: "#fff", border: `${paint === "coverage" || changeColour ? 1.5 : 1}px solid ${changeColour ?? (paint === "coverage" ? coverage : "#e2e8f0")}`, opacity: quiet ? 0.6 : 1 }}>
        <img src={svgDataUriForInterchangeDomainLegend(disk)} width={26} height={26} alt="" style={{ borderRadius: "50%", flexShrink: 0 }} />
        <Box sx={{ minWidth: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
          {name({ fontSize: 13, fontWeight: 600 })}
          <DomainLine graph={graph} id={id} />
        </Box>
      </ButtonBase>
    );
  }
  if (kind === "event") {
    const held = (graph.holders.get(id)?.size ?? 0) > 0;
    // An event keeps its own amber by the domains, which give it no colour; another section that does not paint it makes it grey.
    const colour = changeColour ?? (paint === "events" ? STATUS_COLOUR[graph.eventStatus(id)] : paint === "methods" ? (methodFrame ?? NEUTRAL) : paint === "domains" ? EVENT_COLOUR : NEUTRAL);
    const fill = paint === "events" ? `${colour}14` : paint === "domains" ? "#fffbeb" : "#ffffff";
    return (
      <ButtonBase {...events} sx={{ ...common, bgcolor: fill, border: `1.5px ${held ? "solid" : "dashed"} ${colour}` }}>
        {strip}
        <img src={svgDataUriForGraphNodeIcon(colour, "Event")} width={18} height={18} alt="" style={{ borderRadius: "50%", flexShrink: 0 }} />
        {name()}
      </ButtonBase>
    );
  }
  const action = graph.actions.get(id);
  const domain = graph.domains.get(action?.domain_id ?? "");
  const emits = graph.emitsOf.has(id);
  const own = ACTION_COLOUR[emits ? "with" : "without"];
  const frame = changeColour ?? (paint === "domains" ? (domain?.accent_color ?? NEUTRAL) : paint === "actions" ? own : (methodFrame ?? "#cbd5e1"));
  const icon = changeColour ?? (paint === "actions" ? own : (methodFrame ?? SLATE));
  return (
    <ButtonBase {...events} sx={{ ...common, bgcolor: "#fff", border: `1.5px solid ${frame}`, opacity: emits ? 1 : 0.6 }}>
      {strip}
      <img src={svgDataUriForGraphNodeIcon(icon, "Action")} width={18} height={18} alt="" style={{ borderRadius: "50%", flexShrink: 0 }} />
      <Box sx={{ minWidth: 0, display: "flex", flexDirection: "column", gap: "1px" }}>
        {name()}
        <Box sx={{ fontSize: 10.5, color: NEUTRAL, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{emits ? (domain?.label ?? "No domain") : `${domain?.label ?? "No domain"} · no events`}</Box>
      </Box>
    </ButtonBase>
  );
}

/** One port: a short line out of the body, and a pill with what it leads to, how many, and + or −; dashed when it joins. */
export function PortPill({ port, vertical, changes, onClick }: { port: Port; vertical: boolean; changes?: ReactElement | null; onClick: () => void }) {
  const empty = port.total === 0;
  const all = !port.open && port.hidden === 0 && !port.join;
  const title = port.join
    ? empty
      ? `No ${PORT_WORDS[port.kind]} on screen to join to`
      : `${port.open ? "Unjoin" : "Join to"} ${port.total} ${PORT_WORDS[port.kind]} on screen`
    : empty
      ? `No ${PORT_WORDS[port.kind]}`
      : `${port.open ? "Close" : "Open"} ${PORT_WORDS[port.kind]} · ${port.total}${port.hidden > 0 && port.hidden < port.total ? ` (${port.hidden} not shown yet)` : all ? " (all on screen)" : ""}`;
  return (
    <Box sx={{ flex: 1, display: "flex", flexDirection: vertical ? "column" : "row", alignItems: "center", justifyContent: vertical ? "flex-start" : "flex-end", minWidth: 0, minHeight: 0 }}>
      <Box sx={vertical ? { width: "1.5px", height: 6, bgcolor: "#cbd5e1" } : { flex: 1, height: "1.5px", bgcolor: "#cbd5e1", minWidth: 6 }} />
      <Tooltip title={title} placement={vertical ? "bottom" : "right"} disableInteractive>
        <span>
          <ButtonBase
            disabled={empty}
            data-testid="explorer-port"
            data-port={port.kind}
            onClick={(event) => {
              event.stopPropagation();
              onClick();
            }}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: "3px",
              height: 18,
              pl: "3px",
              pr: "6px",
              borderRadius: 999,
              fontSize: 10.5,
              fontWeight: 600,
              fontVariantNumeric: "tabular-nums",
              whiteSpace: "nowrap",
              color: port.open ? "#fff" : all ? NEUTRAL : "#334155",
              bgcolor: port.open ? "#334155" : "#fff",
              border: `1px ${port.join && !port.open ? "dashed" : "solid"} ${port.open ? "#334155" : port.join ? NEUTRAL : "#cbd5e1"}`,
              boxShadow: port.open ? "none" : "0 1px 2px rgba(15,23,42,0.06)",
              "&:hover": { borderColor: "#334155" },
              "&.Mui-disabled": { color: "#cbd5e1", borderColor: "#e2e8f0", bgcolor: "#f8fafc", boxShadow: "none" },
            }}
          >
            <img src={PORT_ICON[port.kind]} width={12} height={12} alt="" style={{ borderRadius: "50%", opacity: empty ? 0.3 : all ? 0.55 : 1 }} />
            {port.total}
            <Box component="span" sx={{ fontWeight: 700, ml: "1px", width: 7, textAlign: "center" }}>
              {empty ? "" : port.open ? "−" : "+"}
            </Box>
            {changes}
          </ButtonBase>
        </span>
      </Tooltip>
    </Box>
  );
}
