// src/components/diagrams/LifecycleFsmViewer/LifecycleFsmViewer.tsx
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { fetchLifecycleFiniteAutomaton } from "@/api/lifecycleFiniteAutomaton";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import { LayoutGlyphDotLR, LayoutGlyphDotTB } from "@/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { buildLifecycleFsmDotSource, type LifecycleFsmRankdir } from "@/lib/buildLifecycleFsmDotSource";
import { loadGraphvizWasm } from "@/lib/prefetch/erdGraphviz";

const TOOLBAR_BOTTOM_INSET = 52;

const GRID_SX = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  position: "relative" as const,
  bgcolor: "#f4f5f7",
  backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
};

const lifecycleFsmRankdirByNodeId = new Map<string, LifecycleFsmRankdir>();

export type LifecycleFsmViewerProps = {
  lifecycleGraphNodeId: string;
};

/** Lifecycle template FSM via Graphviz WASM (entry / exit pseudostates, dotted canvas). */
export function LifecycleFsmViewer({ lifecycleGraphNodeId }: LifecycleFsmViewerProps) {
  const load = useCallback(() => fetchLifecycleFiniteAutomaton(lifecycleGraphNodeId), [lifecycleGraphNodeId]);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });

  const [rankdir, setRankdir] = useState<LifecycleFsmRankdir>(
    () => lifecycleFsmRankdirByNodeId.get(lifecycleGraphNodeId) ?? "LR",
  );

  useEffect(() => {
    setRankdir(lifecycleFsmRankdirByNodeId.get(lifecycleGraphNodeId) ?? "LR");
  }, [lifecycleGraphNodeId]);

  useEffect(() => {
    lifecycleFsmRankdirByNodeId.set(lifecycleGraphNodeId, rankdir);
  }, [lifecycleGraphNodeId, rankdir]);

  const dot = useMemo(
    () => (data != null ? buildLifecycleFsmDotSource(data, rankdir) : ""),
    [data, rankdir],
  );

  const { viewportRef, pannerRef, zoomPct, zoomIn, zoomOut, fitToContainer, bindInteractions, resetFitFlag } =
    useSvgPanZoom({ fitBottomInset: TOOLBAR_BOTTOM_INSET, fitMaxScale: 1 });
  const [svgMarkup, setSvgMarkup] = useState("");
  const [svgRenderVersion, setSvgRenderVersion] = useState(0);
  const [renderError, setRenderError] = useState<string | null>(null);
  const prevDotRef = useRef("");

  useLayoutEffect(() => {
    if (dot !== prevDotRef.current) {
      prevDotRef.current = dot;
      resetFitFlag();
    }
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
  }, [dot, resetFitFlag]);

  useLayoutEffect(() => {
    if (!svgMarkup) return;
    const panner = pannerRef.current;
    if (!panner) return;

    const svg = panner.querySelector("svg");
    if (svg) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      const vb = svg.viewBox.baseVal;
      if (Number.isFinite(vb.width) && vb.width > 0) {
        svg.style.width = `${vb.width}px`;
      }
      if (Number.isFinite(vb.height) && vb.height > 0) {
        svg.style.height = `${vb.height}px`;
      }

      const gg = svg.querySelector("g.graph");
      const bgPoly = gg?.querySelector("polygon");
      if (bgPoly) {
        const fill = String(bgPoly.getAttribute("fill") || "").toLowerCase().trim();
        const backdrop =
          fill === "#f8fafc" ||
          fill === "#f4f5f7" ||
          fill === "#ffffff" ||
          fill === "#fff" ||
          fill === "white" ||
          fill === "lightgray" ||
          fill === "lightgrey";
        if (backdrop) {
          bgPoly.remove();
        }
      }
    }

    let unbindPan: (() => void) | undefined;
    let cancelled = false;

    const doFitAndBind = () => {
      if (cancelled) return;
      fitToContainer();
      unbindPan = bindInteractions();
    };

    let raf1: number;
    let raf2: number;
    let raf3: number;
    raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        raf3 = requestAnimationFrame(doFitAndBind);
      });
    });

    return () => {
      cancelled = true;
      unbindPan?.();
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      cancelAnimationFrame(raf3);
    };
  }, [svgMarkup, svgRenderVersion, fitToContainer, bindInteractions]);

  return (
    <DiagramShell loading={loading} error={error}>
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
                  "& svg": {
                    display: "block",
                    maxWidth: "none",
                    width: "auto",
                    height: "auto",
                    overflow: "visible",
                    transformOrigin: "0 0",
                  },
                }}
                dangerouslySetInnerHTML={{ __html: svgMarkup }}
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
                  "& .MuiToggleButtonGroup-grouped": {
                    border: 0,
                    borderRadius: "8px !important",
                    mx: 0,
                  },
                  "& .MuiToggleButton-root": {
                    px: 0.35,
                    py: 0.25,
                    minWidth: 30,
                    fontSize: 15,
                    lineHeight: 1,
                    border: "none",
                    bgcolor: "transparent",
                    color: "#64748b",
                    "&:hover": {
                      bgcolor: "rgba(15, 23, 42, 0.06)",
                      color: "#0f172a",
                    },
                    "&.Mui-selected": {
                      color: "#1d4ed8",
                      bgcolor: "transparent !important",
                    },
                    "&.Mui-selected:hover": {
                      bgcolor: "rgba(15, 23, 42, 0.06) !important",
                      color: "#1d4ed8",
                    },
                  },
                }}
              >
                <ToggleButton value="LR" aria-label="Dot — left to right">
                  <Tooltip title="Dot — left to right" placement="top">
                    <Box
                      component="span"
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: "1em",
                        height: "1em",
                      }}
                    >
                      <LayoutGlyphDotLR />
                    </Box>
                  </Tooltip>
                </ToggleButton>
                <ToggleButton value="TB" aria-label="Dot — top to bottom">
                  <Tooltip title="Dot — top to bottom" placement="top">
                    <Box
                      component="span"
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: "1em",
                        height: "1em",
                      }}
                    >
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
