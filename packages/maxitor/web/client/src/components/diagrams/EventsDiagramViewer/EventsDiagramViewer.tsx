// src/components/diagrams/EventsDiagramViewer/EventsDiagramViewer.tsx
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import { getActiveBase } from "@/api/client";
import { fetchDomainEventsDiagram } from "@/api/domainEventsDiagram";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { ElementCard, type CardSubject } from "@/components/diagrams/ElementCard";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import { HalfNote } from "@/components/diagrams/SideBySide";
import { ErdFilterPanel, type ErdFilterRow } from "@/components/ui/ErdFilterPanel";
import { OneHopToggle } from "@/components/ui/OneHopToggle";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { setDiffCounts, useDiffNames } from "@/lib/diffCounts";
import { nothingChanged } from "@/lib/erdDiff";
import { CHANGE_ORDER, changeDiskUri } from "@/lib/erdFilterPresence";
import { buildEventsDot, eventAtTitle, eventsCard, eventsChanges, eventsCounts, eventsOfSide, filterEvents, loadEventsDiff } from "@/lib/eventsDiagram";
import { enabledKeys } from "@/lib/freshGraph";
import { svgOfHalf, useHalf, writesForPair } from "@/lib/half";
import { svgDataUriForGraphNodeIcon, svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import { usePageSetting } from "@/lib/pageSettings";
import { loadGraphvizWasmFor } from "@/lib/prefetch/erdGraphviz";
import { postProcessGraphvizSvgDom } from "@/lib/sanitizeGraphvizSvgOverlays";
import { diagramCanvasEmptyMessageSx } from "@/lib/ui";
import { useGraphvizChangeStepping } from "@/lib/useGraphvizChangeStepping";
import { useHoverCard } from "@/lib/useHoverCard";
import { useSvgLayoutPair } from "@/lib/useSvgLayoutHash";
import type { DiagramSelection } from "@/model/diagramSelection";
import type { DomainEventsDiagramPayload, EventWire } from "@/model/domainEventsDiagram";
import { useSvgDiagramSurface } from "@/rooms/diagramSurface";

const GRID_SX = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  position: "relative" as const,
  bgcolor: "#f4f5f7",
  backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
};

/** The colour of an icon on the diagram. */
const ICON_DISK = "#64748b";
const NODE_TYPES = ["Action", "RegularAspect", "SummaryAspect", "Compensator", "ErrorHandler", "AccessDecide", "Event"];

export type EventsDiagramViewerProps = {
  /** The domain drawn; ``null`` draws every domain on one diagram. */
  domainId: string | null;
  /** Open another page, from a card's link. */
  onOpen?: (selection: DiagramSelection) => void;
};

/** What a domain says on an event's card: which of its roles it plays. */
function domainLine(domain: EventWire["domains"][number]): string {
  return domain.in_vocabulary ? `${domain.label} · in vocabulary` : `${domain.label} · emits, no vocabulary holds it`;
}

/** The card of ``event``, with what the comparison says of it. */
function eventSubject(event: EventWire, diagram: DomainEventsDiagramPayload, at: CardSubject["at"], onOpen: EventsDiagramViewerProps["onOpen"]): CardSubject {
  const held = event.domains.some((domain) => domain.in_vocabulary);
  const domainOf = (actionId: string) => diagram.actions.find((action) => action.id === actionId)?.domain_id ?? event.domains.find((domain) => !domain.in_vocabulary)?.id ?? event.domains[0]?.id;
  return {
    key: event.id,
    ref: { kind: "node", id: event.id },
    title: event.label,
    detail: held ? "Event" : "Event · no vocabulary holds it",
    nodeId: null,
    change: eventsCard(diagram, event.id),
    fields: event.fields.map((field) => ({ name: field.name, type: field.type, description: field.description })),
    links: [
      ...event.methods.map((method) => ({
        group: "Emitted by",
        label: `${method.action_label} · ${method.label}`,
        onOpen: () => {
          const domain = domainOf(method.action_id);
          if (domain) onOpen?.({ kind: "use_case", domain_qualifier: domain });
        },
      })),
      ...event.domains.map((domain) => ({ group: "Domains", label: domainLine(domain), onOpen: () => onOpen?.({ kind: "events", domain_qualifier: domain.id }) })),
    ],
    at,
  };
}

export function EventsDiagramViewer({ domainId, onOpen }: EventsDiagramViewerProps) {
  const diffing = getActiveBase() !== null;
  const load = useCallback(() => (diffing ? loadEventsDiff(domainId) : fetchDomainEventsDiagram(domainId)), [diffing, domainId]);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });
  const [layout, setLayout] = usePageSetting<"dot_lr" | "dot_tb">("layout", "dot_lr");
  const [boundary, setBoundary] = usePageSetting("boundary", true);
  const [chosenDomains, setChosenDomains] = usePageSetting<string[] | null>("domains", null);
  const [offChangeList, setOffChangeList] = usePageSetting<string[]>("disabled_changes", []);
  const offChanges = useMemo(() => new Set(offChangeList), [offChangeList]);
  const domainKeys = useMemo(() => [...new Set(data?.actions.map((action) => action.domain_id))].sort(), [data]);
  const enabled = useMemo(() => new Set(enabledKeys(domainKeys, chosenDomains)), [domainKeys, chosenDomains]);
  const half = useHalf();
  const filtered = useMemo(() => (data ? filterEvents(data, domainId === null && chosenDomains !== null ? enabled : null, diffing ? offChanges : new Set<string>()) : null), [data, domainId, chosenDomains, enabled, diffing, offChanges]);
  const counts = useMemo(() => (diffing && filtered ? eventsCounts(filtered) : null), [diffing, filtered]);
  const drawn = useMemo(() => (half && filtered ? eventsOfSide(filtered, half.side) : filtered), [half, filtered]);
  const writesPair = writesForPair(half);
  useEffect(() => {
    if (writesPair) setDiffCounts(counts);
    return () => {
      if (writesPair) setDiffCounts(null);
    };
  }, [counts, writesPair]);
  const diffNames = useDiffNames();
  const changes = useMemo(() => (filtered && counts && !nothingChanged(counts) ? eventsChanges(filtered) : []), [filtered, counts]);

  const dot = useMemo(() => (drawn ? buildEventsDot(drawn, layout === "dot_tb" ? "TB" : "LR", boundary, (kind) => svgDataUriForGraphNodeIcon(ICON_DISK, kind)) : ""), [drawn, layout, boundary]);
  const [svgMarkup, setSvgMarkup] = useState("");
  const [renderError, setRenderError] = useState<string | null>(null);
  const layoutPair = useSvgLayoutPair(svgMarkup, `dot\n${dot}`);
  const panZoom = useSvgPanZoom({ fitBottomInset: 56, fitLeftInset: 168, fitMarginPx: 14, fitBoundsSelector: "g.graph g.node, g.graph g.edge, g.graph g.cluster", fitToViewBox: true });
  const { viewportRef, pannerRef, zoomPct, zoomIn, zoomOut, fitToContainer, bindInteractions, resetFitFlag } = panZoom;
  const [fitted, setFitted] = useState(false);
  useSvgDiagramSurface(viewportRef, panZoom, Boolean(svgMarkup) && fitted);
  const { card } = useGraphvizChangeStepping({ changes, pannerRef, viewportRef, panZoom, svgMarkup });
  const hoverCard = useHoverCard<CardSubject>(card !== null);
  const { want, close, hold, release } = hoverCard;

  useEffect(() => {
    if (!dot) return;
    let cancelled = false;
    setRenderError(null);
    resetFitFlag();
    const images = NODE_TYPES.map((kind) => ({ path: svgDataUriForGraphNodeIcon(ICON_DISK, kind), width: "16px", height: "16px" }));
    loadGraphvizWasmFor("dot")
      .then((gv) => {
        if (!cancelled) setSvgMarkup(gv.layout(dot, "svg", "dot", { images }));
      })
      .catch((e) => {
        if (!cancelled) setRenderError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [dot, resetFitFlag]);

  useLayoutEffect(() => {
    const panner = pannerRef.current;
    if (!svgMarkup || !panner) return;
    panner.innerHTML = svgOfHalf(svgMarkup, half);
    const svg = panner.querySelector("svg");
    if (svg instanceof SVGSVGElement) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      const box = svg.viewBox.baseVal;
      if (box.width > 0) svg.style.width = `${box.width}px`;
      if (box.height > 0) svg.style.height = `${box.height}px`;
      postProcessGraphvizSvgDom(svg);
    }
    fitToContainer();
    setFitted(true);
    return bindInteractions();
  }, [svgMarkup, half, pannerRef, fitToContainer, bindInteractions]);

  // Resting on an event opens its card; anything else on the drawing has none.
  useEffect(() => {
    const panner = pannerRef.current;
    if (!panner || !drawn) return;
    const onOver = (event: MouseEvent) => {
      const node = (event.target as Element | null)?.closest?.("g.node");
      const title = node?.querySelector("title")?.textContent ?? "";
      const found = eventAtTitle(drawn, title);
      const stage = viewportRef.current?.getBoundingClientRect();
      want(found && stage ? eventSubject(found, drawn, { x: event.clientX - stage.left + 12, y: event.clientY - stage.top + 12 }, onOpen) : null);
    };
    panner.addEventListener("mouseover", onOver);
    panner.addEventListener("pointerdown", close);
    return () => {
      panner.removeEventListener("mouseover", onOver);
      panner.removeEventListener("pointerdown", close);
    };
  }, [pannerRef, viewportRef, drawn, want, close, onOpen]);

  const toggle = (list: readonly string[], key: string) => (list.includes(key) ? list.filter((each) => each !== key) : [...list, key].sort());
  const domainRows: ErdFilterRow[] =
    domainId === null
      ? domainKeys.map((key) => {
          const action = data?.actions.find((each) => each.domain_id === key);
          return { key, label: action?.domain_short_label ?? key, iconSrc: svgDataUriForInterchangeDomainLegend(action?.accent_color ?? "#3b82f6"), on: enabled.has(key), absent: false };
        })
      : [];
  const present = new Set(data ? [...data.events, ...data.edges].map((element) => element.diff) : []);
  const changeRows: ErdFilterRow[] = diffing && counts ? CHANGE_ORDER.filter((status) => present.has(status)).map((status) => ({ key: status, label: status.charAt(0).toUpperCase() + status.slice(1), iconSrc: changeDiskUri(status, true), on: !offChanges.has(status), absent: false })) : [];
  const empty = data !== null && data.events.length === 0;

  return (
    <DiagramShell loading={loading} error={error}>
      {data != null ? (
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0 }}>
          <Box sx={GRID_SX}>
            {half?.side !== "b" && <ErdFilterPanel domainRows={domainRows} kindRows={[]} kindsTitle="Elements" kindsPaint={false} onToggleDomain={(key) => setChosenDomains(toggle([...enabled], key))} onToggleKind={() => undefined} changeRows={changeRows} onToggleChange={(status) => setOffChangeList(toggle(offChangeList, status))} paint={{ source: "domains", onPaint: () => undefined }} />}
            {empty && (
              <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
                No events
              </Typography>
            )}
            {renderError != null && (
              <Typography color="error" variant="body2" sx={{ position: "absolute", left: 8, top: 8, zIndex: 2 }}>
                {renderError}
              </Typography>
            )}
            <HalfNote text={half && drawn?.events.length === 0 && !empty ? `Not in ${half.name}` : null} />
            <Box ref={viewportRef} data-layout-hash={layoutPair?.hash} data-layout-input={layoutPair?.digest} sx={{ position: "absolute", inset: 0, overflow: "hidden", cursor: "grab", touchAction: "none", zIndex: 1, "&.erd-panning": { cursor: "grabbing" } }}>
              <Box ref={pannerRef} sx={{ position: "absolute", left: 0, top: 0, transformOrigin: "0 0", display: "block", opacity: fitted && !empty ? 1 : 0, "& svg": { display: "block", maxWidth: "none", overflow: "visible" } }} />
            </Box>
            {hoverCard.shown && <ElementCard key={hoverCard.shown.key} subject={hoverCard.shown} newer={diffNames?.b ?? "B"} onEnter={hold} onLeave={release} onClose={close} />}
            <ZoomToolbar zoomPct={zoomPct} onZoomIn={zoomIn} onZoomOut={zoomOut} onFit={fitToContainer}>
              <OneHopToggle checked={layout === "dot_tb"} onChange={(top) => setLayout(top ? "dot_tb" : "dot_lr")} label="Top to bottom" />
              <OneHopToggle checked={boundary} onChange={setBoundary} label="Boundary" />
            </ZoomToolbar>
          </Box>
        </Box>
      ) : null}
    </DiagramShell>
  );
}
