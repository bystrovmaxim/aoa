// src/components/diagrams/EventsExplorer/EventsExplorer.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { fetchEventsExplorer } from "@/api/eventsExplorer";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { ElementCard, type CardSubject } from "@/components/diagrams/ElementCard";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import { LayoutGlyphDotLR, LayoutGlyphDotTB } from "@/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs";
import { ErdFilterPanel, type FilterSection } from "@/components/ui/ErdFilterPanel";
import { HoverCardsButton, ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { enabledKeys } from "@/lib/freshGraph";
import { svgDataUriForGraphNodeIcon, svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import { usePageSetting } from "@/lib/pageSettings";
import { loadGraphvizWasmFor } from "@/lib/prefetch/erdGraphviz";
import { useHoverCard } from "@/lib/useHoverCard";
import { useSvgLayoutPair } from "@/lib/useSvgLayoutHash";
import {
  BODY_H,
  BODY_W,
  EventsGraph,
  MAIN_PORT,
  EVENT_STATUSES,
  METHOD_KINDS,
  ROOT_KIND,
  appliedFilters,
  buildDot,
  explore,
  idOf,
  kindOf,
  links,
  methodKindsOf,
  methodsOff,
  offeredSections,
  paintOf,
  portKey,
  readLayout,
  roots,
  type Filters,
  type Layout,
  type Link,
  type Mode,
  type Paint,
  type Placed,
  type PortKind,
  type SectionId,
  type Shown,
} from "@/lib/eventsExplorer";
import type { DiagramSelection } from "@/model/diagramSelection";
import type { EventsExplorerPayload } from "@/model/eventsExplorer";
import { useSvgDiagramSurface } from "@/rooms/diagramSurface";
import { ExplorerNode, PortPill } from "./ExplorerNode";
import { ACTION_COLOUR, COVERAGE_COLOUR, METHOD_COLOUR, METHOD_LABEL, NEUTRAL, STATUS_COLOUR, STATUS_LABEL } from "./explorerLook";
import { ModePill } from "./ModePill";

const GRID_SX = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  position: "relative" as const,
  bgcolor: "#f4f5f7",
  backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
};
const GLIDE = "left 380ms cubic-bezier(.2,.7,.2,1), top 380ms cubic-bezier(.2,.7,.2,1), opacity 240ms";
/** Room kept free on the stage for the filter panel, the mode pill and the toolbar. */
const INSET = { left: 170, top: 56, bottom: 56, right: 20 };

export type EventsExplorerProps = {
  /** The domain whose events the page opens with; ``null`` opens on the first layer alone. */
  domainId: string | null;
  /** Open another page, from a card's link. */
  onOpen?: (selection: DiagramSelection) => void;
};

/** A line's stroke: a domain's lines take its colour by the domains, an emitting line its method's by the methods; else grey. */
function linkStyle(graph: EventsGraph, link: Link, paint: Paint): { stroke: string; width: number; dash?: string } {
  const domainColour = (node: string) => (paint === "domains" ? (graph.domains.get(idOf(node))?.accent_color ?? NEUTRAL) : "#cbd5e1");
  switch (link.kind) {
    case "holds":
      return { stroke: domainColour(link.a), width: 1.6 };
    case "domain_emits":
      return { stroke: domainColour(link.a), width: 1.5, dash: "2 4" };
    case "emits":
      return paint === "methods" ? { stroke: METHOD_COLOUR[link.methods[0]?.kind] ?? NEUTRAL, width: 2 } : { stroke: NEUTRAL, width: 1.5 };
    case "belongs":
      return { stroke: "#cbd5e1", width: 1.3, dash: "5 4" };
  }
}

/** The card of a node: an event's fields, producers and domains; a domain's counts and emitting actions; an action's events. */
function cardOf(graph: EventsGraph, node: string, at: CardSubject["at"], onOpen: EventsExplorerProps["onOpen"]): CardSubject {
  const id = idOf(node);
  const base = { key: node, ref: { kind: "node" as const, id }, title: graph.label(node), nodeId: null, change: null, at };
  if (kindOf(node) === "event") {
    const held = graph.holders.get(id) ?? new Set<string>();
    return {
      ...base,
      detail: held.size > 0 ? "Event" : "Event · no vocabulary holds it",
      fields: graph.events.get(id)?.fields.map((field) => ({ name: field.name, type: field.type, description: field.description })) ?? [],
      links: [
        ...(graph.emittersOf.get(id) ?? []).map((emit) => ({
          group: "Emitted by",
          label: `${graph.actions.get(emit.action_id)?.label ?? emit.action_id} · ${emit.method} (${emit.kind})`,
          onOpen: () => {
            const domain = graph.actions.get(emit.action_id)?.domain_id;
            if (domain) onOpen?.({ kind: "use_case", domain_qualifier: domain });
          },
        })),
        ...graph.domainsOfEvent(id).map((domain) => ({ group: "Domains", label: `${graph.domains.get(domain)?.label ?? domain} · ${held.has(domain) ? "in vocabulary" : "emits, no vocabulary holds it"}`, onOpen: () => onOpen?.({ kind: "events", domain_qualifier: domain }) })),
      ],
    };
  }
  if (kindOf(node) === "domain") {
    const { vocabulary } = graph.domainCounts(id);
    return {
      ...base,
      detail: vocabulary === null ? "Domain · no vocabulary" : "Domain · vocabulary",
      links: [...(graph.emittingActionsOf.get(id) ?? [])].sort().map((action) => ({ group: "Actions that emit", label: graph.actions.get(action)?.label ?? action, onOpen: () => onOpen?.({ kind: "use_case", domain_qualifier: id }) })),
    };
  }
  const domain = graph.actions.get(id)?.domain_id ?? "";
  return {
    ...base,
    detail: `Action · ${graph.domains.get(domain)?.label ?? "No domain"}`,
    links: (graph.emitsOf.get(id) ?? []).map((emit) => ({ group: "Emits", label: `${emit.method} (${emit.kind}) → ${graph.events.get(emit.event_id)?.label ?? emit.event_id}`, onOpen: () => domain && onOpen?.({ kind: "use_case", domain_qualifier: domain }) })),
  };
}

function ExplorerCanvas({ payload, domainId, onOpen }: { payload: EventsExplorerPayload; domainId: string | null; onOpen: EventsExplorerProps["onOpen"] }) {
  const graph = useMemo(() => new EventsGraph(payload), [payload]);
  const [mode, setMode] = usePageSetting<Mode>("mode", "domains");
  const [layout, setLayout] = usePageSetting<Layout>("layout", "dot_lr");
  const [openedList, setOpenedList] = usePageSetting<string[]>("opened", domainId ? [portKey(`domain:${domainId}`, "events")] : []);
  const [chosenDomains, setChosenDomains] = usePageSetting<string[] | null>("domains", null);
  const [offList, setOffList] = usePageSetting<string[]>("off", []);
  const [paintChoice, setPaintChoice] = usePageSetting<string>("paint", "domains");
  const opened = useMemo(() => new Set(openedList), [openedList]);
  const domainKeys = useMemo(() => [...graph.domains.keys()].sort(), [graph]);
  const filters = useMemo<Filters>(() => ({ domains: new Set(enabledKeys(domainKeys, chosenDomains)), off: new Set(offList) }), [domainKeys, chosenDomains, offList]);
  const applied = useMemo(() => appliedFilters(mode, filters), [mode, filters]);
  // The kinds of method switched off emit nothing: the screen is read from the graph without them.
  const g = useMemo(() => graph.only(methodsOff(applied)), [graph, applied]);
  const first = useMemo(() => roots(mode, applied, graph, g), [mode, applied, graph, g]);
  const shown = useMemo(() => explore(first, opened, applied, ROOT_KIND[mode], graph, g), [first, opened, applied, mode, graph, g]);
  const drawnLinks = useMemo(() => links(shown, opened, g), [shown, opened, g]);
  // The screen as it would be with every row on: which sections the panel offers (FR-016).
  const loose: Shown = useMemo(() => {
    const all: Filters = { domains: filters.domains, off: new Set() };
    return explore(roots(mode, all, graph), opened, all, ROOT_KIND[mode], graph);
  }, [mode, filters.domains, opened, graph]);
  const offered = useMemo(() => offeredSections(mode, loose, graph), [mode, loose, graph]);
  const paint: Paint = paintOf(paintChoice, offered.ids);

  const [placed, setPlaced] = useState<Placed | null>(null);
  /** Graphviz's answer and the DOT it was laid out from: their hashes prove one input gives one picture (layout determinism). */
  const [laid, setLaid] = useState({ json: "", dot: "" });
  const layoutPair = useSvgLayoutPair(laid.json, laid.dot);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [animate, setAnimate] = useState(false);
  const [hover, setHover] = useState<{ node: string; x: number; y: number } | null>(null);
  const [hoverLink, setHoverLink] = useState<string | null>(null);
  const panZoom = useSvgPanZoom({ fitBottomInset: INSET.bottom, fitLeftInset: INSET.left, fitMarginPx: 14, fitToViewBox: true, fitMaxScale: 1.1 });
  const { viewportRef, pannerRef, zoomPct, zoomIn, zoomOut, fitToContainer, bindInteractions, placeAt, getScale, setScale } = panZoom;
  useSvgDiagramSurface(viewportRef, panZoom, placed !== null);
  const hoverCard = useHoverCard<CardSubject>(false);
  const { want, close, hold, release } = hoverCard;
  /** What the next layout keeps: the clicked node still on the screen, or a fit of the whole. */
  const anchorRef = useRef<{ node: string; client: { x: number; y: number }; before: ReadonlySet<string> } | "fit">("fit");

  useEffect(() => {
    let cancelled = false;
    const { dot, byDotId } = buildDot(shown, drawnLinks, layout);
    setRenderError(null);
    loadGraphvizWasmFor("dot")
      .then((gv) => {
        if (cancelled) return;
        const json = gv.layout(dot, "json", "dot");
        setLaid({ json, dot });
        setPlaced(readLayout(json, byDotId));
      })
      .catch((e) => {
        if (!cancelled) setRenderError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [shown, drawnLinks, layout]);

  // Gestures are bound once the first picture is placed, and stay bound while later layouts replace it.
  const ready = placed !== null;
  useEffect(() => (ready ? bindInteractions() : undefined), [ready, bindInteractions]);

  // A new layout: hold the clicked node where it was and bring what it opened into view; otherwise fit the whole.
  useLayoutEffect(() => {
    if (!placed) return;
    const anchor = anchorRef.current;
    anchorRef.current = "fit";
    const stage = viewportRef.current?.getBoundingClientRect();
    if (anchor === "fit" || !stage) {
      setAnimate(false);
      fitToContainer();
      // A first layer too tall to read once fitted starts at its top, at three quarters.
      if (getScale() < 0.75) {
        setScale(0.75);
        placeAt(stage ? stage.left + INSET.left + 20 : 0, stage ? stage.top + INSET.top : 0, 0, 0);
      }
      return;
    }
    const at = placed.nodes.get(anchor.node);
    if (!at) return;
    setAnimate(true);
    placeAt(anchor.client.x, anchor.client.y, at.x, at.y);
    const fresh = [...placed.nodes.entries()].filter(([node]) => !anchor.before.has(node)).map(([, box]) => box);
    if (fresh.length === 0) return;
    const boxes = [at, ...fresh];
    const x0 = Math.min(...boxes.map((box) => box.x));
    const y0 = Math.min(...boxes.map((box) => box.y));
    const x1 = Math.max(...boxes.map((box) => box.x + box.w));
    const y1 = Math.max(...boxes.map((box) => box.y + box.h));
    const k = getScale();
    const client = (x: number, y: number) => ({ x: anchor.client.x + (x - at.x) * k, y: anchor.client.y + (y - at.y) * k });
    const inside = (p: { x: number; y: number }) => p.x >= stage.left + INSET.left && p.y >= stage.top + INSET.top && p.x <= stage.right - INSET.right && p.y <= stage.bottom - INSET.bottom;
    if (inside(client(x0, y0)) && inside(client(x1, y1))) return;
    const room = { w: stage.width - INSET.left - INSET.right, h: stage.height - INSET.top - INSET.bottom };
    setScale(Math.min(k, room.w / (x1 - x0), room.h / (y1 - y0)));
    placeAt(stage.left + INSET.left + room.w / 2, stage.top + INSET.top + room.h / 2, (x0 + x1) / 2, (y0 + y1) / 2);
  }, [placed, fitToContainer, getScale, setScale, placeAt, viewportRef]);

  const holdStill = (node: string) => {
    const element = pannerRef.current?.querySelector(`[data-box="${CSS.escape(node)}"]`);
    const rect = element?.getBoundingClientRect();
    anchorRef.current = rect ? { node, client: { x: rect.left, y: rect.top }, before: new Set(shown.depth.keys()) } : "fit";
  };
  const togglePort = (node: string, port: PortKind) => {
    holdStill(node);
    const key = portKey(node, port);
    setOpenedList(opened.has(key) ? openedList.filter((each) => each !== key) : [...openedList, key].sort());
  };
  const refit = (apply: () => void) => {
    anchorRef.current = "fit";
    apply();
  };

  const near = useMemo(() => {
    if (!hover) return null;
    const set = new Set([hover.node]);
    for (const link of drawnLinks) if (link.a === hover.node || link.b === hover.node) set.add(link.a).add(link.b);
    return set;
  }, [hover, drawnLinks]);

  const onNodeHover = useCallback(
    (node: string, on: boolean, x: number, y: number) => {
      setHover(on ? { node, x, y } : null);
      const stage = viewportRef.current?.getBoundingClientRect();
      want(on && stage ? cardOf(graph, node, { x: x - stage.left + 12, y: y - stage.top + 12 }, onOpen) : null);
    },
    [graph, onOpen, want, viewportRef],
  );

  const toggle = (list: readonly string[], key: string) => (list.includes(key) ? list.filter((each) => each !== key) : [...list, key].sort());
  const on = (key: string) => !filters.off.has(key);
  const rowsOf: Record<SectionId, () => FilterSection> = {
    domains: () => ({
      id: "domains",
      title: "Domains",
      paints: true,
      rows: [...graph.domains.values()]
        .sort((one, other) => one.label.localeCompare(other.label))
        .map((domain) => ({ key: domain.id, label: domain.label, iconSrc: svgDataUriForInterchangeDomainLegend(domain.accent_color), on: filters.domains.has(domain.id), absent: mode !== "domains" && !graph.withEvents(domain.id) })),
    }),
    coverage: () => ({
      id: "coverage",
      title: "Coverage",
      paints: true,
      rows: [
        { key: "with", label: "With events", iconSrc: svgDataUriForInterchangeDomainLegend(COVERAGE_COLOUR.with), on: on("coverage:with") },
        { key: "without", label: "Without events", iconSrc: svgDataUriForInterchangeDomainLegend(COVERAGE_COLOUR.without), on: on("coverage:without") },
      ],
    }),
    events: () => ({
      id: "events",
      title: "Events",
      paints: true,
      rows: EVENT_STATUSES.map((status) => ({ key: status, label: STATUS_LABEL[status], iconSrc: svgDataUriForGraphNodeIcon(STATUS_COLOUR[status], "Event"), on: on(`events:${status}`), absent: !offered.statuses.has(status) })),
    }),
    methods: () => ({
      id: "methods",
      title: "Methods",
      paints: true,
      rows: METHOD_KINDS.map((kind) => ({ key: kind, label: METHOD_LABEL[kind], iconSrc: svgDataUriForGraphNodeIcon(METHOD_COLOUR[kind], kind), on: on(`methods:${kind}`), absent: !offered.kinds.has(kind) })),
    }),
    actions: () => ({
      id: "actions",
      title: "Actions",
      paints: true,
      rows: [
        { key: "with", label: "With events", iconSrc: svgDataUriForGraphNodeIcon(ACTION_COLOUR.with, "Action"), on: on("actions:with") },
        { key: "without", label: "Without events", iconSrc: svgDataUriForGraphNodeIcon(ACTION_COLOUR.without, "Action"), on: on("actions:without") },
      ],
    }),
  };
  const sections = offered.ids.map((id) => rowsOf[id]());
  const toggleRow = (section: string, row: string) =>
    refit(() => {
      if (section === "domains") setChosenDomains(toggle([...filters.domains], row));
      else setOffList(toggle(offList, `${section}:${row}`));
    });
  const counts: Record<Mode, number> = { domains: graph.domains.size, events: graph.events.size, actions: graph.emitsOf.size };
  const vertical = layout === "dot_tb";

  return (
    <Box sx={GRID_SX}>
      <ModePill
        mode={mode}
        counts={counts}
        onMode={(next) =>
          refit(() => {
            setMode(next);
            setOpenedList([]);
          })
        }
      />
      <ErdFilterPanel domainRows={[]} kindRows={[]} onToggleDomain={() => undefined} onToggleKind={() => undefined} sections={sections} onToggleRow={toggleRow} paint={{ source: paint, onPaint: setPaintChoice }} />
      {renderError != null && (
        <Typography color="error" variant="body2" sx={{ position: "absolute", left: 8, top: 8, zIndex: 2 }}>
          {renderError}
        </Typography>
      )}
      {placed && first.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", zIndex: 2 }}>
          Nothing under these filters
        </Typography>
      )}
      <Box ref={viewportRef} data-testid="events-explorer" data-layout-hash={layoutPair?.hash} data-layout-input={layoutPair?.digest} sx={{ position: "absolute", inset: 0, overflow: "hidden", cursor: "grab", touchAction: "none", zIndex: 1, "&.erd-panning": { cursor: "grabbing" } }}>
        <Box ref={pannerRef} sx={{ position: "absolute", left: 0, top: 0, transformOrigin: "0 0", opacity: placed ? 1 : 0 }}>
          {placed && (
            <svg width={placed.width} height={placed.height} viewBox={`0 0 ${placed.width} ${placed.height}`} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none" }}>
              {drawnLinks.map((link) => {
                const edge = placed.edges.get(link.id);
                if (!edge) return null;
                const style = linkStyle(graph, link, paint);
                const ofNode = hover !== null && (link.a === hover.node || link.b === hover.node);
                const named = link.kind === "emits" && (hoverLink === link.id || ofNode);
                const lit = hoverLink ? hoverLink === link.id : !near || ofNode;
                const d = { d: `path("${edge.d}")`, transition: animate ? "d 380ms cubic-bezier(.2,.7,.2,1)" : "none" } as CSSProperties;
                return (
                  <g key={link.id} data-link={link.id} style={{ opacity: lit ? 1 : 0.15, transition: "opacity 160ms" }}>
                    <path style={d} fill="none" stroke={style.stroke} strokeWidth={hoverLink === link.id ? style.width + 1.2 : style.width} strokeDasharray={style.dash} strokeLinecap="round" />
                    {/* A wide unseen stroke, so a thin line is easy to rest on. */}
                    <path style={{ ...d, pointerEvents: "stroke" }} fill="none" stroke="transparent" strokeWidth={12} onMouseEnter={() => setHoverLink(link.id)} onMouseLeave={() => setHoverLink(null)} />
                    {named && (
                      <text x={edge.start.x + 8} y={edge.start.y - 5} fontSize="11" fontWeight="500" fill="#334155" style={{ paintOrder: "stroke", stroke: "#ffffff", strokeWidth: 5, strokeLinejoin: "round", pointerEvents: "none" }}>
                        {link.methods.map((each) => `${each.method} · ${each.kind}`).join(", ")}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          )}
          {placed &&
            [...shown.depth.keys()].map((node) => {
              const box = placed.nodes.get(node);
              if (!box) return null;
              const ports = shown.ports.get(node) ?? [];
              const kind = kindOf(node);
              const main = [ports.find((port) => port.kind === MAIN_PORT[kind]), ...ports].find((port) => port && port.total > 0);
              const body = BODY_H[kind];
              return (
                <Box key={node} data-box={node} sx={{ position: "absolute", width: box.w, height: box.h, transition: animate ? GLIDE : "opacity 240ms", opacity: near && !near.has(node) ? 0.35 : 1, animation: "explorerIn 260ms ease-out", "@keyframes explorerIn": { from: { opacity: 0 }, to: { opacity: 1 } } }} style={{ left: box.x, top: box.y }}>
                  <Box sx={{ position: "absolute", left: 0, top: vertical ? 0 : (box.h - body) / 2 }}>
                    <ExplorerNode graph={graph} node={node} hot={hover?.node === node} paint={paint} kinds={methodKindsOf(node, g)} onClick={() => main && togglePort(node, main.kind)} onHover={(on, x, y) => onNodeHover(node, on, x, y)} />
                  </Box>
                  {ports.length > 0 && (
                    <Box sx={vertical ? { position: "absolute", left: 0, top: body, width: BODY_W, height: box.h - body, display: "flex", px: "14px", gap: "6px" } : { position: "absolute", left: BODY_W, top: 0, width: box.w - BODY_W, height: box.h, display: "flex", flexDirection: "column", justifyContent: "center", gap: "4px", py: ports.length > 1 ? "2px" : 0 }}>
                      {ports.map((port) => (
                        <PortPill key={port.kind} port={port} vertical={vertical} onClick={() => togglePort(node, port.kind)} />
                      ))}
                    </Box>
                  )}
                </Box>
              );
            })}
        </Box>
      </Box>
      {hoverCard.shown && <ElementCard key={hoverCard.shown.key} subject={hoverCard.shown} newer="B" onEnter={hold} onLeave={release} onClose={close} />}
      <ZoomToolbar zoomPct={zoomPct} onZoomIn={zoomIn} onZoomOut={zoomOut} onFit={fitToContainer}>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={layout}
          onChange={(_, next: Layout | null) => next && refit(() => setLayout(next))}
          aria-label="Layout"
          sx={{
            gap: "1px",
            "& .MuiToggleButtonGroup-grouped": { border: 0, borderRadius: "8px !important", mx: 0 },
            "& .MuiToggleButton-root": { px: 0.35, py: 0.25, minWidth: 30, fontSize: 15, lineHeight: 1, border: "none", bgcolor: "transparent", color: "#64748b", "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)", color: "#0f172a" }, "&.Mui-selected": { color: "#1d4ed8", bgcolor: "transparent !important" } },
          }}
        >
          {(
            [
              ["dot_lr", "Dot — left to right", LayoutGlyphDotLR],
              ["dot_tb", "Dot — top to bottom", LayoutGlyphDotTB],
            ] as const
          ).map(([value, title, Glyph]) => (
            <ToggleButton key={value} value={value} aria-label={title}>
              <Tooltip title={title} placement="top">
                <Box component="span" sx={{ display: "flex", width: "1em", height: "1em" }}>
                  <Glyph />
                </Box>
              </Tooltip>
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <Box component="span" aria-hidden sx={{ width: "1px", height: "22px", bgcolor: "rgba(15, 23, 42, 0.12)", mx: "2px" }} />
        <Tooltip title="Close every port" placement="top">
          <span>
            <ButtonBase disabled={openedList.length === 0} aria-label="Close every port" data-testid="explorer-close-all" onClick={() => refit(() => setOpenedList([]))} sx={{ width: 30, height: 30, borderRadius: "8px", fontSize: 15, color: "#64748b", "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)", color: "#0f172a" }, "&.Mui-disabled": { opacity: 0.4 } }}>
              <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M4 12h16" />
                <path d="M8 3l4 4 4-4M8 21l4-4 4 4" />
              </svg>
            </ButtonBase>
          </span>
        </Tooltip>
        <HoverCardsButton />
      </ZoomToolbar>
    </Box>
  );
}

/** The events explorer (spec 055): one layer at first, the graph opened link by link through ports. */
export function EventsExplorer({ domainId, onOpen }: EventsExplorerProps) {
  const load = useCallback(() => fetchEventsExplorer(), []);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });
  return (
    <DiagramShell loading={loading} error={error}>
      {data != null ? <ExplorerCanvas payload={data} domainId={domainId} onOpen={onOpen} /> : null}
    </DiagramShell>
  );
}
