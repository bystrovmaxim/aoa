// src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx
import type { Engine } from "@hpcc-js/wasm-graphviz";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactElement, type SVGProps } from "react";
import { getActiveBase } from "@/api/client";
import { useSvgLayoutPair } from "@/lib/useSvgLayoutHash";
import { useSvgDiagramSurface } from "@/rooms/diagramSurface";
import { useGraphvizFocus } from "@/rooms/graphvizFocus";
import { enabledKeys } from "@/lib/freshGraph";
import { useCurrentPage, usePageSetting } from "@/lib/pageSettings";
import { fetchDomainUseCaseDiagram } from "@/api/domainUseCaseDiagram";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { DiffCard } from "@/components/history/DiffCard";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import {
  LayoutGlyphDotLR,
  LayoutGlyphDotTB,
  LayoutGlyphFdp,
  LayoutGlyphNeato,
} from "@/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs";
import { ErdFilterPanel, type ErdFilterRow } from "@/components/ui/ErdFilterPanel";
import { OneHopToggle } from "@/components/ui/OneHopToggle";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import useCaseRoleActorUrl from "@/assets/useCaseRoleActor.svg?url";
import {
  buildDomainUseCaseDotBundle,
  USE_CASE_FADED_CLASS,
  type DomainUseCaseLayoutEngine,
  type DomainUseCaseRankdir,
} from "@/lib/buildDomainUseCaseDotSource";
import { setDiffCounts, useDiffNames } from "@/lib/diffCounts";
import { nothingChanged } from "@/lib/erdDiff";
import { MARK_LOOK } from "@/lib/erdDiffCard";
import { statusDiskUri } from "@/lib/erdFilterPresence";
import { defaultPaint, paintSettingName, paintSource, type PaintSection } from "@/lib/erdPaint";
import { svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import { filterUseCaseDiagramByDomains } from "@/lib/filterUseCaseDiagramByDomains";
import { loadGraphvizWasmFor } from "@/lib/prefetch/erdGraphviz";
import { postProcessGraphvizSvgDom } from "@/lib/sanitizeGraphvizSvgOverlays";
import { diagramCanvasEmptyMessageSx } from "@/lib/ui";
import { filterUseCaseByChanges, filterUseCaseByElements, loadUseCaseDiff, USE_CASE_ELEMENTS, unmarkedUseCase, withUseCaseOneHop, useCaseCard, useCaseChangeKinds, useCaseChanges, useCaseCounts, useCaseIdAt } from "@/lib/useCaseDiff";
import { bindUseCaseHover } from "@/lib/useCaseHover";
import { cardPlace, useGraphvizChangeStepping } from "@/lib/useGraphvizChangeStepping";


const GRID_SX = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  position: "relative" as const,
  bgcolor: "#f4f5f7",
  backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
};

/** How wide a link's hit area is on screen. */
const LINK_HIT_PX = 14;

/** The grey of a filter disk that does not paint. */
const IDLE_DISK = "#cbd5e1";

/** How far a press may move and still be a click. */
const CLICK_SLOP_PX = 5;

type UseCaseDiagramLayoutPreset = "dot_lr" | "dot_tb" | "neato" | "fdp";


const USE_CASE_LAYOUT_TOOL_ROW: {
  preset: UseCaseDiagramLayoutPreset;
  title: string;
  Glyph: (props: SVGProps<SVGSVGElement>) => ReactElement;
}[] = [
  { preset: "dot_lr", title: "Dot — left to right", Glyph: LayoutGlyphDotLR },
  { preset: "dot_tb", title: "Dot — top to bottom", Glyph: LayoutGlyphDotTB },
  { preset: "neato", title: "Neato (spring)", Glyph: LayoutGlyphNeato },
  { preset: "fdp", title: "FDP (force)", Glyph: LayoutGlyphFdp },
];

function presetToRankdir(preset: UseCaseDiagramLayoutPreset): DomainUseCaseRankdir {
  return preset === "dot_tb" ? "TB" : "LR";
}

function presetToLayoutEngine(preset: UseCaseDiagramLayoutPreset): DomainUseCaseLayoutEngine {
  switch (preset) {
    case "neato":
      return "neato";
    case "fdp":
      return "fdp";
    default:
      return "dot";
  }
}

const graphvizRoleActorImage = {
  path: useCaseRoleActorUrl,
  width: "52px",
  height: "74px",
} as const;

export type UseCaseDiagramViewerProps = {
  /** The domain drawn; ``null`` draws every domain on one diagram. */
  domainId: string | null;
};

export function UseCaseDiagramViewer({ domainId }: UseCaseDiagramViewerProps) {
  const diffing = getActiveBase() !== null;
  const load = useCallback(() => (diffing ? loadUseCaseDiff(domainId) : fetchDomainUseCaseDiagram(domainId)), [diffing, domainId]);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });

  // Page settings: the person's own outside a room, the room's inside one (spec 028, FR-030). The
  // direction is part of the layout preset (``dot_lr`` / ``dot_tb``), so it needs no setting of its own.
  const [layoutPreset, setLayoutPreset] = usePageSetting<UseCaseDiagramLayoutPreset>("layout", "dot_lr");
  /** LR/TB + Neato/FDP when Boundary is off; Boundary on keeps the preset for when it goes off again. */
  const [boundary, setBoundary] = usePageSetting("boundary", true);

  /** Boundary on forces hierarchical dot ranks; preserve neato/fdp in ``layoutPreset`` for when Boundary turns off. */
  const layoutForBundler = useMemo((): UseCaseDiagramLayoutPreset => {
    if (boundary) {
      if (layoutPreset === "dot_lr" || layoutPreset === "dot_tb") return layoutPreset;
      return "dot_lr";
    }
    return layoutPreset;
  }, [boundary, layoutPreset]);

  const domainKeyList = useMemo(() => {
    if (!data) return [];
    const u = new Set(data.actions.map((a) => a.domain_id));
    return [...u].sort();
  }, [data]);

  const accents = useMemo(() => {
    if (!data) return {};
    const m: Record<string, string> = {};
    for (const a of data.actions) {
      if (m[a.domain_id] === undefined) m[a.domain_id] = a.accent_color;
    }
    return m;
  }, [data]);

  const rowLabels = useMemo(() => {
    if (!data) return {};
    const m: Record<string, string> = {};
    for (const a of data.actions) {
      if (m[a.domain_id] === undefined) m[a.domain_id] = a.domain_short_label || a.domain_id;
    }
    return m;
  }, [data]);

  /** The domains switched on; ``null`` until someone chooses, which means all of them. */
  const [chosenDomains, setChosenDomains] = usePageSetting<string[] | null>("domains", null);

  // A domain the model no longer has stops applying (spec 028, FR-076).
  const effectiveEnabled = useMemo(
    () => new Set(data ? enabledKeys([...new Set(data.actions.map((a) => a.domain_id))].sort(), chosenDomains) : []),
    [data, chosenDomains],
  );

  // A kind of change switched off hides what is of that kind, as a domain switched off does (spec 041, FR-021).
  const [offChangeList, setOffChangeList] = usePageSetting<string[]>("disabled_changes", []);
  const offChanges = useMemo(() => new Set(offChangeList), [offChangeList]);
  const [includeOneHop, setIncludeOneHop] = usePageSetting("one_hop", true);
  // As on the ERD, 1-hop brings back what stands one link from what the filters left, even what a filter hid.
  const [offElementList, setOffElementList] = usePageSetting<string[]>("disabled_kinds", []);
  const offElements = useMemo(() => new Set(offElementList), [offElementList]);
  const filtered = useMemo(() => {
    if (data == null) return null;
    const kept = filterUseCaseByElements(filterUseCaseByChanges(filterUseCaseDiagramByDomains(data, effectiveEnabled), diffing ? offChanges : new Set<string>()), offElements);
    return includeOneHop ? withUseCaseOneHop(kept, data) : kept;
  }, [data, effectiveEnabled, diffing, offChanges, includeOneHop, offElements]);

  // What paints the actions is a page setting, One's and Diff's apart; a room shares it, the address carries it (spec 041, FR-022, FR-023).
  const baseChanges = useMemo(() => (diffing && data ? useCaseChangeKinds(data) : []), [diffing, data]);
  const [chosenPaint, setChosenPaint] = usePageSetting<PaintSection>(paintSettingName(diffing), defaultPaint(diffing));
  const paintSection = paintSource(["domains", ...(baseChanges.length > 0 ? (["changes"] as const) : [])], chosenPaint);

  // In Diff the drawn diagram's counts go to the version button; when nothing on it changed it is drawn as One (spec 041, FR-010 – FR-013).
  const counts = useMemo(() => (diffing && filtered ? useCaseCounts(filtered) : null), [diffing, filtered]);
  const drawn = useMemo(() => (filtered && counts && nothingChanged(counts) ? unmarkedUseCase(filtered) : filtered), [filtered, counts]);
  useEffect(() => setDiffCounts(counts), [counts]);
  useEffect(() => () => setDiffCounts(null), []);
  const diffNames = useDiffNames();
  const changes = useMemo(() => (drawn && counts && !nothingChanged(counts) ? useCaseChanges(drawn) : []), [drawn, counts]);

  const bundle = useMemo(
    () =>
      drawn != null
        ? buildDomainUseCaseDotBundle(
            drawn,
            presetToRankdir(layoutForBundler),
            { roleActorImageUrl: useCaseRoleActorUrl },
            { boundary, layoutEngine: presetToLayoutEngine(layoutForBundler), paint: paintSection === "domains" ? "domains" : "changes" },
          )
        : null,
    [drawn, layoutForBundler, boundary, paintSection],
  );

  const graphvizEngineForBundle = useMemo(
    (): Engine => presetToLayoutEngine(layoutForBundler) as Engine,
    [layoutForBundler],
  );

  const dot = bundle?.dot ?? "";

  // Each change is sent as the whole new set, never as a toggle (FR-031).
  const toggleDomain = useCallback(
    (key: string) => {
      const next = new Set(effectiveEnabled);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      setChosenDomains([...next].sort());
    },
    [effectiveEnabled, setChosenDomains],
  );

  const toggleChange = useCallback(
    (status: string) => {
      const next = new Set(offChanges);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      setOffChangeList([...next].sort());
    },
    [offChanges, setOffChangeList],
  );

  const toggleElement = useCallback(
    (element: string) => {
      const next = new Set(offElements);
      if (next.has(element)) next.delete(element);
      else next.add(element);
      setOffElementList([...next].sort());
    },
    [offElements, setOffElementList],
  );

  // A section that does not paint shows its disks grey: the colours on screen are one section's.
  const shownChanges = new Set(filtered ? useCaseChangeKinds(filtered) : []);
  const shownDomains = new Set(filtered?.actions.map((action) => action.domain_id));
  const domainRows: ErdFilterRow[] = domainKeyList.map((key) => ({
    key,
    label: rowLabels[key] ?? key,
    iconSrc: svgDataUriForInterchangeDomainLegend(paintSection === "domains" ? accents[key] || "#3b82f6" : IDLE_DISK),
    on: effectiveEnabled.has(key),
    absent: !shownDomains.has(key),
  }));
  // The elements paint nothing: their disks stay grey whatever paints.
  const elementRows: ErdFilterRow[] = USE_CASE_ELEMENTS.map((element) => ({
    key: element,
    label: element.charAt(0).toUpperCase() + element.slice(1),
    iconSrc: statusDiskUri(IDLE_DISK, ""),
    on: !offElements.has(element),
    absent: (filtered?.[element].length ?? 0) === 0,
  }));
  const changeRows: ErdFilterRow[] = baseChanges.map((status) => ({
    key: status,
    label: status.charAt(0).toUpperCase() + status.slice(1),
    iconSrc: statusDiskUri(status === "unchanged" || paintSection !== "changes" ? IDLE_DISK : MARK_LOOK[status].colour, status === "unchanged" ? "" : MARK_LOOK[status].sign),
    on: !offChanges.has(status),
    absent: !shownChanges.has(status),
  }));

  const panZoom = useSvgPanZoom({
    fitBottomInset: 56,
    fitLeftInset: 168,
    fitMarginPx: 14,
    fitBoundsSelector: "g.graph g.node, g.graph g.edge, g.graph g.cluster",
    fitToViewBox: true,
  });
  const { viewportRef, pannerRef, zoomPct, zoomIn, zoomOut, fitToContainer, bindInteractions, resetFitFlag, needsFit, getScale, onTransform } = panZoom;

  // A link's hit area stays as wide on screen at every zoom: on a big diagram, far out, it would shrink to nothing.
  useEffect(() => {
    const keep = () => pannerRef.current?.style.setProperty("--use-case-hit", `${LINK_HIT_PX / getScale()}px`);
    keep();
    return onTransform(keep);
  }, [pannerRef, getScale, onTransform]);

  const [svgMarkup, setSvgMarkup] = useState("");
  // Graphviz's own output goes on screen unchanged, so its hash is the picture's (FR-005, FR-090); the text Graphviz
  // was given, hashed with it as one pair, is the settings digest a room compares layouts under (FR-093).
  const layoutPair = useSvgLayoutPair(svgMarkup, `${graphvizEngineForBundle}\n${dot}`);
  const [svgRenderVersion, setSvgRenderVersion] = useState(0);
  // The steps through what the drawing marks, and the card of a click or a step. The card is read again from what is
  // drawn, so it follows Live and closes by itself when its element is no longer marked (spec 041, FR-012 – FR-018).
  const { card, setCard, openCard } = useGraphvizChangeStepping({ changes, pannerRef, viewportRef, panZoom, svgMarkup });
  const cardId = card?.target.elements[0]?.id;
  const cardTarget = useMemo(() => (cardId && drawn ? useCaseCard(drawn, cardId) : null), [cardId, drawn]);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [firstFitDone, setFirstFitDone] = useState(false);
  // Registered after the second fit (one frame after the first), so a placed view is not undone.
  useSvgDiagramSurface(viewportRef, panZoom, Boolean(svgMarkup) && firstFitDone);
  // Hover and tooltip shared with followers, and the followed person's shown here (spec 029).
  useGraphvizFocus(pannerRef.current, svgMarkup, useCurrentPage(), "node");
  const prevDotRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    const d = bundle?.dot ?? "";
    if (d === prevDotRef.current) return;
    prevDotRef.current = d;
    resetFitFlag();
    // The previous drawing stays until the new one is placed and fitted in one frame (spec 038): no blank frame.
  }, [dot, resetFitFlag]);

  useEffect(() => {
    if (!bundle) {
      setSvgMarkup("");
      setRenderError(null);
      return;
    }
    let cancelled = false;
    setRenderError(null);
    const needsRoleImages = (filtered?.roles.length ?? 0) > 0;
    loadGraphvizWasmFor(graphvizEngineForBundle)
      .then((gv) => {
        if (cancelled) return;
        const images = [
          ...bundle.actionImages,
          ...(needsRoleImages ? [graphvizRoleActorImage] : []),
        ];
        const svg = gv.layout(bundle.dot, "svg", graphvizEngineForBundle, {
          files: bundle.files,
          images,
        });
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
  }, [bundle, filtered, graphvizEngineForBundle]);

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
    // A press that moved is a pan, not a click.
    let press: { x: number; y: number } | null = null;
    const onDown = (event: PointerEvent) => {
      press = { x: event.clientX, y: event.clientY };
    };
    const onUp = (event: PointerEvent) => {
      const started = press;
      press = null;
      if (!started || Math.hypot(event.clientX - started.x, event.clientY - started.y) > CLICK_SLOP_PX) return;
      const id = useCaseIdAt(event.target as Element | null, drawn);
      const box = viewportRef.current?.getBoundingClientRect();
      const target = id ? useCaseCard(drawn, id) : null;
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
      {data != null ? (
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0 }}>
          <Box sx={GRID_SX}>
            <ErdFilterPanel
              domainRows={domainRows}
              kindRows={elementRows}
              kindsTitle="Elements"
              kindsPaint={false}
              onToggleDomain={toggleDomain}
              onToggleKind={toggleElement}
              changeRows={changeRows}
              onToggleChange={toggleChange}
              paint={{ source: paintSection, onPaint: setChosenPaint }}
            />
            {filtered != null && filtered.actions.length + filtered.roles.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
                {data.actions.length + data.roles.length === 0 ? "No actions in this domain." : "Everything is filtered out."}
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
                "&.erd-wheel-zooming .use-case-panner": { pointerEvents: "none" },
              }}
            >
              <Box
                ref={pannerRef}
                className="use-case-panner"
                sx={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  transformOrigin: "0 0",
                  display: "block",
                  opacity: firstFitDone ? 1 : 0,
                  pointerEvents: firstFitDone ? "auto" : "none",
                  transition: "none",
                  // Painted by changes, the unchanged lose their colour as well, as on the ERD; painted by domains they keep it.
                  "& path.erd-hit": { strokeWidth: "var(--use-case-hit, 14px)" },
                  [`& .${USE_CASE_FADED_CLASS}`]: { opacity: 0.3, ...(paintSection === "changes" && { filter: "grayscale(1)" }) },
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
                value={layoutForBundler}
                onChange={(_, v: UseCaseDiagramLayoutPreset | null) => {
                  if (v !== null) setLayoutPreset(v);
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
                {(boundary ? USE_CASE_LAYOUT_TOOL_ROW.slice(0, 2) : USE_CASE_LAYOUT_TOOL_ROW).map(({ preset, title, Glyph: LayoutGlyph }) => (
                  <ToggleButton key={preset} value={preset} aria-label={title}>
                    <Tooltip title={title} placement="top">
                      <Box component="span" sx={{ display: "flex", alignItems: "center", justifyContent: "center", width: "1em", height: "1em" }}>
                        <LayoutGlyph />
                      </Box>
                    </Tooltip>
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
              <Box
                component="span"
                aria-hidden
                sx={{ width: "1px", height: "22px", bgcolor: "rgba(15, 23, 42, 0.12)", flexShrink: 0, mx: "2px" }}
              />
              <OneHopToggle checked={boundary} onChange={setBoundary} label="Boundary" />
              <OneHopToggle checked={includeOneHop} onChange={setIncludeOneHop} />
            </ZoomToolbar>
          </Box>
        </Box>
      ) : null}
    </DiagramShell>
  );
}
