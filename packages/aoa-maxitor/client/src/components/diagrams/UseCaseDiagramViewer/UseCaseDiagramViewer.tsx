// src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { fetchDomainUseCaseDiagram } from "@/api/domainUseCaseDiagram";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import { LayoutGlyphDotLR, LayoutGlyphDotTB } from "@/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs";
import { DomainLegend } from "@/components/ui/DomainLegend";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { buildDomainUseCaseDotSource, type DomainUseCaseRankdir } from "@/lib/buildDomainUseCaseDotSource";
import { filterUseCaseDiagramByDomains } from "@/lib/filterUseCaseDiagramByDomains";
import { loadGraphvizWasm } from "@/lib/prefetch/erdGraphviz";
import { diagramCanvasEmptyMessageSx } from "@/lib/ui";

const useCaseEnabledDomainsByViewKey = new Map<string, string[]>();

const GRID_SX = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  position: "relative" as const,
  bgcolor: "#f4f5f7",
  backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
};

const useCaseRankdirByDomainId = new Map<string, DomainUseCaseRankdir>();

export type UseCaseDiagramViewerProps = {
  domainId: string;
};

export function UseCaseDiagramViewer({ domainId }: UseCaseDiagramViewerProps) {
  const load = useCallback(() => fetchDomainUseCaseDiagram(domainId), [domainId]);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });

  const [rankdir, setRankdir] = useState<DomainUseCaseRankdir>(
    () => useCaseRankdirByDomainId.get(domainId) ?? "LR",
  );

  useEffect(() => {
    setRankdir(useCaseRankdirByDomainId.get(domainId) ?? "LR");
  }, [domainId]);

  useEffect(() => {
    useCaseRankdirByDomainId.set(domainId, rankdir);
  }, [domainId, rankdir]);

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

  const [enabledDomains, setEnabledDomains] = useState<Set<string> | undefined>(undefined);
  const lastDomainIdRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    if (!data) return;
    const keys = [...new Set(data.actions.map((a) => a.domain_id))].sort();
    if (keys.length === 0) {
      setEnabledDomains(new Set());
      lastDomainIdRef.current = domainId;
      return;
    }

    if (lastDomainIdRef.current !== domainId) {
      lastDomainIdRef.current = domainId;
      const saved = useCaseEnabledDomainsByViewKey.get(domainId);
      if (saved?.length) {
        const restored = new Set(keys.filter((k) => saved.includes(k)));
        setEnabledDomains(restored.size > 0 ? restored : new Set(keys));
      } else {
        setEnabledDomains(new Set(keys));
      }
      return;
    }

    setEnabledDomains((prev) => {
      if (prev === undefined) return new Set(keys);
      const merged = new Set(keys.filter((k) => prev.has(k)));
      return merged.size > 0 ? merged : new Set(keys);
    });
  }, [data, domainId]);

  useEffect(() => {
    if (!data || enabledDomains === undefined) return;
    useCaseEnabledDomainsByViewKey.set(domainId, [...enabledDomains].sort());
  }, [domainId, data, enabledDomains]);

  const effectiveEnabled = useMemo(() => {
    if (!data) return new Set<string>();
    const all = new Set(data.actions.map((a) => a.domain_id));
    if (all.size === 0) return new Set<string>();
    if (enabledDomains === undefined) return all;
    return enabledDomains;
  }, [data, enabledDomains]);

  const filtered = useMemo(
    () => (data != null ? filterUseCaseDiagramByDomains(data, effectiveEnabled) : null),
    [data, effectiveEnabled],
  );

  const dot = useMemo(
    () => (filtered != null ? buildDomainUseCaseDotSource(filtered, rankdir) : ""),
    [filtered, rankdir],
  );

  const toggleDomain = useCallback(
    (key: string) => {
      setEnabledDomains((prev) => {
        const base = prev ?? new Set(domainKeyList);
        const next = new Set(base);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        return next;
      });
    },
    [domainKeyList],
  );

  const { viewportRef, pannerRef, zoomPct, zoomIn, zoomOut, fitToContainer, bindInteractions, resetFitFlag } =
    useSvgPanZoom({
      fitBottomInset: 56,
      fitMarginPx: 14,
      fitBoundsSelector: "g.graph g.node, g.graph g.edge, g.graph g.cluster",
    });

  const [svgMarkup, setSvgMarkup] = useState("");
  const [svgRenderVersion, setSvgRenderVersion] = useState(0);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [firstFitDone, setFirstFitDone] = useState(false);
  const prevDotRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    if (dot === prevDotRef.current) return;
    const prev = prevDotRef.current;
    prevDotRef.current = dot;
    setFirstFitDone(false);
    resetFitFlag();
    if (prev !== null) {
      setSvgMarkup("");
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
  }, [dot]);

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
        const isBackdrop =
          fill === "#f8fafc" || fill === "#f4f5f7" || fill === "#ffffff" ||
          fill === "#fff" || fill === "white" || fill === "lightgray" || fill === "lightgrey";
        if (isBackdrop) bgPoly.remove();
      }
    }

    let unbindPan: (() => void) | undefined;
    let cancelled = false;
    let raf1: number;
    let raf2: number;
    let raf3: number;
    let raf4: number | undefined;

    const doFitAndBind = () => {
      if (cancelled) return;
      fitToContainer();
      raf4 = requestAnimationFrame(() => {
        if (cancelled) return;
        fitToContainer();
        unbindPan = bindInteractions();
        setFirstFitDone(true);
      });
    };

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
      if (raf4 !== undefined) cancelAnimationFrame(raf4);
    };
  }, [svgMarkup, svgRenderVersion, fitToContainer, bindInteractions]);

  return (
    <DiagramShell loading={loading} error={error}>
      {data != null ? (
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0 }}>
          <Box sx={GRID_SX}>
            <DomainLegend
              domainKeys={domainKeyList}
              enabledDomains={effectiveEnabled}
              accents={accents}
              rowLabels={rowLabels}
              showWhenSingle
              onToggle={toggleDomain}
            />
            {filtered != null && filtered.actions.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
                {data.actions.length === 0
                  ? "No actions in this domain."
                  : "No actions for the selected domains."}
              </Typography>
            )}
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
                onChange={(_, v: DomainUseCaseRankdir | null) => {
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
