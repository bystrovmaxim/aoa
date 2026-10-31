// src/components/diagrams/LifecycleFsmViewer/LifecycleFsmViewer.tsx
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { getActiveBase } from "@/api/client";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useSvgLayoutPair } from "@/lib/useSvgLayoutHash";
import { useSvgDiagramSurface } from "@/rooms/diagramSurface";
import { useGraphvizFocus } from "@/rooms/graphvizFocus";
import { useCurrentPage, usePageSetting } from "@/lib/pageSettings";
import { DiffCard } from "@/components/history/DiffCard";
import { setDiffCounts, useDiffNames } from "@/lib/diffCounts";
import { cardPlace, useGraphvizChangeStepping } from "@/lib/useGraphvizChangeStepping";
import { nothingChanged } from "@/lib/erdDiff";
import { filterLifecycleByChanges, filterLifecycleByKinds, LIFECYCLE_KINDS, lifecycleCard, lifecycleChangeKinds, lifecycleChanges, lifecycleCounts, lifecycleIdAt, loadLifecycle, loadLifecycleDiff, unmarkedLifecycle, withLifecycleOneHop } from "@/lib/lifecycleDiff";
import { MARK_LOOK } from "@/lib/erdDiffCard";
import { statusDiskUri } from "@/lib/erdFilterPresence";
import { svgDataUriForGraphNodeIcon } from "@/lib/icons";
import { bindUseCaseHover } from "@/lib/useCaseHover";
import { ErdFilterPanel, type ErdFilterRow } from "@/components/ui/ErdFilterPanel";
import { OneHopToggle } from "@/components/ui/OneHopToggle";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import { LayoutGlyphDotLR, LayoutGlyphDotTB } from "@/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { buildLifecycleFsmDotSource, LIFECYCLE_FADED_CLASS, paletteForStateType, type LifecycleFsmRankdir } from "@/lib/buildLifecycleFsmDotSource";
import { loadGraphvizWasm } from "@/lib/prefetch/erdGraphviz";
import { postProcessGraphvizSvgDom } from "@/lib/sanitizeGraphvizSvgOverlays";
import { diagramCanvasEmptyMessageSx } from "@/lib/ui";

const GRID_SX = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  position: "relative" as const,
  bgcolor: "#f4f5f7",
  backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
};

/** A press that moved further than this is a pan, not a click. */
const CLICK_SLOP_PX = 5;
/** The graph's node type of each kind of state: the filter shows the full graph's icon for it. */
const STATE_NODE_TYPE = { initial: "StateInitial", intermediate: "StateIntermediate", final: "StateFinal" } as const;
/** A filter disk with no colour of its own. */
const IDLE_DISK = "#cbd5e1";

export type LifecycleFsmViewerProps = {
  lifecycleGraphNodeId: string;
};

export function LifecycleFsmViewer({ lifecycleGraphNodeId }: LifecycleFsmViewerProps) {
  const diffing = getActiveBase() !== null;
  const load = useCallback(() => (diffing ? loadLifecycleDiff(lifecycleGraphNodeId) : loadLifecycle(lifecycleGraphNodeId)), [diffing, lifecycleGraphNodeId]);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });

  // A page setting: shared inside a room (spec 028, FR-030).
  const [rankdir, setRankdir] = usePageSetting<LifecycleFsmRankdir>("rankdir", "LR");

  // Page settings like the direction: a room shares them, the address carries them (spec 042, FR-024).
  const [offChangeList, setOffChangeList] = usePageSetting<string[]>("disabled_changes", []);
  const [offKindList, setOffKindList] = usePageSetting<string[]>("disabled_kinds", []);
  const [includeOneHop, setIncludeOneHop] = usePageSetting("one_hop", true);
  const offChanges = useMemo(() => new Set(offChangeList), [offChangeList]);
  const offKinds = useMemo(() => new Set(offKindList), [offKindList]);
  const filtered = useMemo(() => {
    if (data == null) return null;
    const kept = filterLifecycleByKinds(filterLifecycleByChanges(data, diffing ? offChanges : new Set<string>()), offKinds);
    return includeOneHop ? withLifecycleOneHop(kept, data) : kept;
  }, [data, diffing, offChanges, offKinds, includeOneHop]);
  const baseChanges = useMemo(() => (diffing && data ? lifecycleChangeKinds(data) : []), [diffing, data]);

  // In Diff the diagram's counts go to the version button; when nothing on it changed it is drawn as One (spec 042, FR-010 – FR-012).
  const counts = useMemo(() => (diffing && filtered ? lifecycleCounts(filtered) : null), [diffing, filtered]);
  const drawn = useMemo(() => (filtered && counts && nothingChanged(counts) ? unmarkedLifecycle(filtered) : filtered), [filtered, counts]);
  useEffect(() => setDiffCounts(counts), [counts]);
  useEffect(() => () => setDiffCounts(null), []);
  const diffNames = useDiffNames();
  const changes = useMemo(() => (drawn && counts && !nothingChanged(counts) ? lifecycleChanges(drawn) : []), [drawn, counts]);

  const dot = useMemo(
    () => (drawn != null ? buildLifecycleFsmDotSource(drawn, rankdir) : ""),
    [drawn, rankdir],
  );

  // Each change is sent as the whole new set, never as a toggle.
  const toggled = (list: readonly string[], key: string) => (list.includes(key) ? list.filter((each) => each !== key) : [...list, key].sort());
  // In One the kinds show the states' own colours; in Diff the changes paint, so the kinds' disks stay grey (spec 042, FR-023).
  const kindRows: ErdFilterRow[] = LIFECYCLE_KINDS.filter((kind) => data?.states.some((state) => state.state_type === kind)).map((kind) => ({
    key: kind,
    label: kind.charAt(0).toUpperCase() + kind.slice(1),
    iconSrc: svgDataUriForGraphNodeIcon(diffing ? IDLE_DISK : paletteForStateType(kind).stroke, STATE_NODE_TYPE[kind]),
    on: !offKinds.has(kind),
    absent: !filtered?.states.some((state) => state.state_type === kind),
  }));
  const shownChanges = new Set(filtered ? lifecycleChangeKinds(filtered) : []);
  const changeRows: ErdFilterRow[] = baseChanges.map((status) => ({
    key: status,
    label: status.charAt(0).toUpperCase() + status.slice(1),
    iconSrc: statusDiskUri(status === "unchanged" ? IDLE_DISK : MARK_LOOK[status].colour, status === "unchanged" ? "" : MARK_LOOK[status].sign),
    on: !offChanges.has(status),
    absent: !shownChanges.has(status),
  }));

  // Reserve space for the floating zoom + rankdir toolbar (bottom: 10 + ~36px button row)
  // so vertical fit doesn't push the diagram under the controls in TB mode.
  const panZoom = useSvgPanZoom({ fitBottomInset: 56 });
  const { viewportRef, pannerRef, zoomPct, zoomIn, zoomOut, fitToContainer, bindInteractions, resetFitFlag, needsFit } = panZoom;

  const [svgMarkup, setSvgMarkup] = useState("");
  // Graphviz's own output goes on screen unchanged, so its hash is the picture's (FR-005, FR-090); the text Graphviz
  // was given, hashed with it as one pair, is the settings digest a room compares layouts under (FR-093).
  const layoutPair = useSvgLayoutPair(svgMarkup, `dot\n${dot}`);
  const [svgRenderVersion, setSvgRenderVersion] = useState(0);
  const [renderError, setRenderError] = useState<string | null>(null);
  const { card, setCard, openCard } = useGraphvizChangeStepping({ changes, pannerRef, viewportRef, panZoom, svgMarkup });
  const cardId = card?.target.elements[0]?.id;
  const cardTarget = useMemo(() => (cardId && drawn ? lifecycleCard(drawn, cardId) : null), [cardId, drawn]);
  const [firstFitDone, setFirstFitDone] = useState(false);
  // Registered after the second fit (one frame after the first), so a placed view is not undone.
  useSvgDiagramSurface(viewportRef, panZoom, Boolean(svgMarkup) && firstFitDone);
  // Hover and tooltip shared with followers, and the followed person's shown here (spec 029).
  useGraphvizFocus(pannerRef.current, svgMarkup, useCurrentPage(), "node");
  const prevDotRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    if (dot === prevDotRef.current) return;
    prevDotRef.current = dot;
    resetFitFlag();
    // The previous drawing stays until the new one is placed and fitted in one frame (spec 038): no blank frame.
  }, [dot, resetFitFlag]);

  useEffect(() => {
    if (!dot) {
      setSvgMarkup("");
      setRenderError(null);
      return;
    }
    let cancelled = false;
    setRenderError(null);
    loadGraphvizWasm()
      .then((gv) => {
        if (cancelled) return;
        const svg = gv.layout(dot, "svg", "dot");
        if (cancelled) return;
        setSvgMarkup(svg);
        setSvgRenderVersion((v) => v + 1);
      })
      .catch((e) => {
        if (!cancelled) setRenderError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [dot]);

  // Identical structure to ErdGraphvizCanvas.useLayoutEffect
  useLayoutEffect(() => {
    if (!svgMarkup) return;
    const panner = pannerRef.current;
    if (!panner) return;
    // The markup is placed here, not through ``dangerouslySetInnerHTML``: React put it back on every render (a zoom
    // click is enough) as Graphviz wrote it — a third larger, in points, and without the steps below — so the drawing
    // on screen was not the one just fitted (spec 038; ErdGraphvizCanvas places its own the same way).
    panner.innerHTML = svgMarkup;

    const svg = panner.querySelector("svg");
    if (svg instanceof SVGSVGElement) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      const vb = svg.viewBox.baseVal;
      if (Number.isFinite(vb.width) && vb.width > 0) {
        svg.style.width = `${vb.width}px`;
      }
      if (Number.isFinite(vb.height) && vb.height > 0) {
        svg.style.height = `${vb.height}px`;
      }

      postProcessGraphvizSvgDom(svg);
    }

    // A new drawing is fitted here, before the frame is painted, and shown at once: no frame with the old view, a blank
    // or a hidden panner (spec 038). One frame later it is fitted again only if this one could not measure.
    fitToContainer();
    const unbindPan = bindInteractions();
    const hover = new AbortController();
    bindUseCaseHover(panner, hover.signal);
    setFirstFitDone(true);
    const raf = requestAnimationFrame(() => {
      if (needsFit()) fitToContainer();
    });

    return () => {
      unbindPan();
      hover.abort();
      cancelAnimationFrame(raf);
    };
  }, [svgMarkup, svgRenderVersion, fitToContainer, bindInteractions, needsFit]);

  useEffect(() => {
    const panner = pannerRef.current;
    if (!panner || !drawn || !diffing) return;
    let press: { x: number; y: number } | null = null;
    const onDown = (event: PointerEvent) => {
      press = { x: event.clientX, y: event.clientY };
    };
    const onUp = (event: PointerEvent) => {
      const started = press;
      press = null;
      if (!started || Math.hypot(event.clientX - started.x, event.clientY - started.y) > CLICK_SLOP_PX) return;
      const id = lifecycleIdAt(event.target as Element | null, drawn);
      const box = viewportRef.current?.getBoundingClientRect();
      const target = id ? lifecycleCard(drawn, id) : null;
      if (target && box) openCard(target, cardPlace(box, event.clientX - box.left + 8, event.clientY - box.top + 8));
    };
    panner.addEventListener("pointerdown", onDown);
    panner.addEventListener("pointerup", onUp);
    return () => {
      panner.removeEventListener("pointerdown", onDown);
      panner.removeEventListener("pointerup", onUp);
    };
  }, [pannerRef, viewportRef, drawn, diffing, openCard]);

  return (
    <DiagramShell loading={loading} error={error}>
      {!loading && !error && data === null ? (
        <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
          This lifecycle is not in this version. Move the range, or open another page from the left panel.
        </Typography>
      ) : null}
      {data != null ? (
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0 }}>
          <Box sx={GRID_SX}>
            {kindRows.length > 1 || changeRows.length > 0 ? (
              <ErdFilterPanel
                domainRows={[]}
                withDomains={false}
                kindRows={kindRows}
                kindsTitle="Elements"
                kindsPaint={!diffing}
                onToggleDomain={() => undefined}
                onToggleKind={(kind) => setOffKindList(toggled(offKindList, kind))}
                changeRows={changeRows}
                onToggleChange={(status) => setOffChangeList(toggled(offChangeList, status))}
                paint={{ source: changeRows.length > 0 ? "changes" : "kinds", onPaint: () => undefined }}
              />
            ) : null}
            {filtered != null && filtered.states.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
                Everything is filtered out.
              </Typography>
            )}
            {renderError != null && (
              <Typography color="error" variant="body2" sx={{ position: "absolute", left: 8, top: 8, zIndex: 2 }}>
                {renderError}
              </Typography>
            )}
            <Box
              ref={viewportRef}
              data-layout-hash={layoutPair?.hash}
              data-layout-input={layoutPair?.digest}
              sx={{
                position: "absolute",
                inset: 0,
                overflow: "hidden",
                cursor: "grab",
                touchAction: "none",
                zIndex: 1,
                "&.erd-panning": { cursor: "grabbing" },
                "&.erd-wheel-zooming .lifecycle-fsm-panner": { pointerEvents: "none" },
              }}
            >
              <Box
                ref={pannerRef}
                className="lifecycle-fsm-panner"
                sx={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  transformOrigin: "0 0",
                  display: "block",
                  opacity: firstFitDone ? 1 : 0,
                  pointerEvents: firstFitDone ? "auto" : "none",
                  transition: "none",
                  // Unchanged in Diff: grey and dim, whatever colour a state declares (spec 042, FR-005).
                  [`& .${LIFECYCLE_FADED_CLASS}`]: { opacity: 0.3, filter: "grayscale(1)" },
                  "& svg": {
                    display: "block",
                    maxWidth: "none",
                    width: "auto",
                    height: "auto",
                    overflow: "visible",
                    transformOrigin: "0 0",
                  },
                }}
              />
            </Box>

            {cardTarget && card && <DiffCard target={cardTarget} newer={diffNames?.b ?? "B"} at={card.at} onClose={() => setCard(null)} />}

            <ZoomToolbar zoomPct={zoomPct} onZoomIn={zoomIn} onZoomOut={zoomOut} onFit={fitToContainer}>
              <Box
                component="span"
                aria-hidden
                sx={{ width: "1px", height: "22px", bgcolor: "rgba(15, 23, 42, 0.12)", flexShrink: 0, mx: "2px" }}
              />
              <ToggleButtonGroup
                exclusive
                size="small"
                value={rankdir}
                onChange={(_, v: LifecycleFsmRankdir | null) => {
                  if (v !== null) setRankdir(v);
                }}
                sx={{
                  flexWrap: "wrap",
                  gap: "1px",
                  bgcolor: "transparent",
                  "& .MuiToggleButtonGroup-grouped": { border: 0, borderRadius: "8px !important", mx: 0 },
                  "& .MuiToggleButton-root": {
                    px: 0.35, py: 0.25, minWidth: 30, fontSize: 15, lineHeight: 1,
                    border: "none", bgcolor: "transparent", color: "#64748b",
                    "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)", color: "#0f172a" },
                    "&.Mui-selected": { color: "#1d4ed8", bgcolor: "transparent !important" },
                    "&.Mui-selected:hover": { bgcolor: "rgba(15, 23, 42, 0.06) !important", color: "#1d4ed8" },
                  },
                }}
              >
                <ToggleButton value="LR" aria-label="Dot — left to right">
                  <Tooltip title="Dot — left to right" placement="top">
                    <Box component="span" sx={{ display: "flex", alignItems: "center", justifyContent: "center", width: "1em", height: "1em" }}>
                      <LayoutGlyphDotLR />
                    </Box>
                  </Tooltip>
                </ToggleButton>
                <ToggleButton value="TB" aria-label="Dot — top to bottom">
                  <Tooltip title="Dot — top to bottom" placement="top">
                    <Box component="span" sx={{ display: "flex", alignItems: "center", justifyContent: "center", width: "1em", height: "1em" }}>
                      <LayoutGlyphDotTB />
                    </Box>
                  </Tooltip>
                </ToggleButton>
              </ToggleButtonGroup>
              <Box
                component="span"
                aria-hidden
                sx={{ width: "1px", height: "22px", bgcolor: "rgba(15, 23, 42, 0.12)", flexShrink: 0, mx: "2px" }}
              />
              <OneHopToggle checked={includeOneHop} onChange={setIncludeOneHop} />
            </ZoomToolbar>
          </Box>
        </Box>
      ) : null}
    </DiagramShell>
  );
}
