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
import { setDiffCounts } from "@/lib/diffCounts";
import { nothingChanged } from "@/lib/erdDiff";
import { lifecycleCounts, loadLifecycle, loadLifecycleDiff, unmarkedLifecycle } from "@/lib/lifecycleDiff";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import { LayoutGlyphDotLR, LayoutGlyphDotTB } from "@/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { buildLifecycleFsmDotSource, LIFECYCLE_FADED_CLASS, type LifecycleFsmRankdir } from "@/lib/buildLifecycleFsmDotSource";
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

export type LifecycleFsmViewerProps = {
  lifecycleGraphNodeId: string;
};

export function LifecycleFsmViewer({ lifecycleGraphNodeId }: LifecycleFsmViewerProps) {
  const diffing = getActiveBase() !== null;
  const load = useCallback(() => (diffing ? loadLifecycleDiff(lifecycleGraphNodeId) : loadLifecycle(lifecycleGraphNodeId)), [diffing, lifecycleGraphNodeId]);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });

  // A page setting: shared inside a room (spec 028, FR-030).
  const [rankdir, setRankdir] = usePageSetting<LifecycleFsmRankdir>("rankdir", "LR");

  // In Diff the diagram's counts go to the version button; when nothing on it changed it is drawn as One (spec 042, FR-010 – FR-012).
  const counts = useMemo(() => (diffing && data ? lifecycleCounts(data) : null), [diffing, data]);
  const drawn = useMemo(() => (data && counts && nothingChanged(counts) ? unmarkedLifecycle(data) : data), [data, counts]);
  useEffect(() => setDiffCounts(counts), [counts]);
  useEffect(() => () => setDiffCounts(null), []);

  const dot = useMemo(
    () => (drawn != null ? buildLifecycleFsmDotSource(drawn, rankdir) : ""),
    [drawn, rankdir],
  );

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
    setFirstFitDone(true);
    const raf = requestAnimationFrame(() => {
      if (needsFit()) fitToContainer();
    });

    return () => {
      unbindPan();
      cancelAnimationFrame(raf);
    };
  }, [svgMarkup, svgRenderVersion, fitToContainer, bindInteractions, needsFit]);

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
            </ZoomToolbar>
          </Box>
        </Box>
      ) : null}
    </DiagramShell>
  );
}
