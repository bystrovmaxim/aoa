// src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx
import type { Engine } from "@hpcc-js/wasm-graphviz";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactElement, type SVGProps } from "react";
import { fetchDomainUseCaseDiagram } from "@/api/domainUseCaseDiagram";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import {
  LayoutGlyphDotLR,
  LayoutGlyphDotTB,
  LayoutGlyphFdp,
  LayoutGlyphNeato,
} from "@/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs";
import { DomainLegend } from "@/components/ui/DomainLegend";
import { OneHopToggle } from "@/components/ui/OneHopToggle";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import useCaseRoleActorUrl from "@/assets/useCaseRoleActor.svg?url";
import {
  buildDomainUseCaseDotBundle,
  type DomainUseCaseLayoutEngine,
  type DomainUseCaseRankdir,
} from "@/lib/buildDomainUseCaseDotSource";
import { filterUseCaseDiagramByDomains } from "@/lib/filterUseCaseDiagramByDomains";
import { loadGraphvizWasm } from "@/lib/prefetch/erdGraphviz";
import { postProcessGraphvizSvgDom } from "@/lib/sanitizeGraphvizSvgOverlays";
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

type UseCaseDiagramLayoutPreset = "dot_lr" | "dot_tb" | "neato" | "fdp";

const useCaseRankdirByDomainId = new Map<string, DomainUseCaseRankdir>();

/** LR/TB + Neato/FDP when Boundary off; persisted per domain together with Boundary. */
const useCaseLayoutPresetByDomainId = new Map<string, UseCaseDiagramLayoutPreset>();

const useCaseBoundaryByDomainId = new Map<string, boolean>();

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

function readStoredLayoutPreset(domainId: string): UseCaseDiagramLayoutPreset {
  const preset = useCaseLayoutPresetByDomainId.get(domainId);
  if (preset) return preset;
  const legacyRd = useCaseRankdirByDomainId.get(domainId);
  return legacyRd === "TB" ? "dot_tb" : "dot_lr";
}

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
  domainId: string;
};

export function UseCaseDiagramViewer({ domainId }: UseCaseDiagramViewerProps) {
  const load = useCallback(() => fetchDomainUseCaseDiagram(domainId), [domainId]);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });

  const [layoutPreset, setLayoutPreset] = useState<UseCaseDiagramLayoutPreset>(() =>
    readStoredLayoutPreset(domainId),
  );

  useEffect(() => {
    setLayoutPreset(readStoredLayoutPreset(domainId));
  }, [domainId]);

  useEffect(() => {
    useCaseLayoutPresetByDomainId.set(domainId, layoutPreset);
    if (layoutPreset === "dot_lr" || layoutPreset === "dot_tb") {
      useCaseRankdirByDomainId.set(domainId, presetToRankdir(layoutPreset));
    }
  }, [domainId, layoutPreset]);

  const [boundary, setBoundary] = useState(
    () => useCaseBoundaryByDomainId.get(domainId) ?? true,
  );

  useEffect(() => {
    setBoundary(useCaseBoundaryByDomainId.get(domainId) ?? true);
  }, [domainId]);

  useEffect(() => {
    useCaseBoundaryByDomainId.set(domainId, boundary);
  }, [domainId, boundary]);

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

  const bundle = useMemo(
    () =>
      filtered != null
        ? buildDomainUseCaseDotBundle(
            filtered,
            presetToRankdir(layoutForBundler),
            { roleActorImageUrl: useCaseRoleActorUrl },
            { boundary, layoutEngine: presetToLayoutEngine(layoutForBundler) },
          )
        : null,
    [filtered, layoutForBundler, boundary],
  );

  const graphvizEngineForBundle = useMemo(
    (): Engine => presetToLayoutEngine(layoutForBundler) as Engine,
    [layoutForBundler],
  );

  const dot = bundle?.dot ?? "";

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
    const d = bundle?.dot ?? "";
    if (d === prevDotRef.current) return;
    const prev = prevDotRef.current;
    prevDotRef.current = d;
    setFirstFitDone(false);
    resetFitFlag();
    if (prev !== null) {
      setSvgMarkup("");
    }
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
    loadGraphvizWasm()
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
            </ZoomToolbar>
          </Box>
        </Box>
      ) : null}
    </DiagramShell>
  );
}
