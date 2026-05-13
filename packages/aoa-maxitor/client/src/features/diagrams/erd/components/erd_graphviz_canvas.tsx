// packages/aoa-maxitor/client/src/features/diagrams/erd/components/erd_graphviz_canvas.tsx
import type { Engine } from "@hpcc-js/wasm-graphviz";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useEffect, useLayoutEffect, useMemo, useState } from "react";
import { ZoomToolbar } from "../../shared";
import { DomainLegend } from "./domain_legend";
import { OneHopToggle } from "./one_hop_toggle";
import { loadGraphvizWasm } from "../hooks/use_graphviz";
import { useSvgPanZoom } from "../hooks/use_svg_pan_zoom";
import {
  buildDotSource,
  erdGraphvizEngine,
  type ErdEntity,
  type ErdGraphPayload,
  type ErdGraphvizLayout,
  type ErdRelation,
} from "../lib/build_dot_source";
import { enrichErdDataForViewer } from "../lib/enrich_erd_data";
import type { ErdDomainsBundle } from "../lib/load_erd_domains_bundle";

function mergeDomainPayloads(parts: ErdGraphPayload[]): ErdGraphPayload {
  const nodeById = new Map<string, ErdEntity>();
  const seenRelations = new Set<string>();
  const relationsOut: ErdRelation[] = [];
  const edgeSig = (e: ErdRelation) => `${e.source}\u001f${e.target}\u001f${e.label ?? ""}`;
  for (const part of parts) {
    for (const n of part.entities ?? []) nodeById.set(n.id, n);
    for (const e of part.relations ?? []) {
      const sig = edgeSig(e);
      if (seenRelations.has(sig)) continue;
      seenRelations.add(sig);
      relationsOut.push(e);
    }
  }
  return { entities: [...nodeById.values()], relations: relationsOut };
}

function getMergedFromDomains(enriched: Record<string, unknown>, enabled: Set<string>): ErdGraphPayload {
  const domainsRaw = enriched.domains;
  if (!domainsRaw || typeof domainsRaw !== "object") {
    return { entities: [], relations: [] };
  }
  const domains = domainsRaw as Record<string, { entities?: ErdEntity[]; relations?: ErdRelation[] }>;
  const keys = Object.keys(domains);
  if (!keys.length) return { entities: [], relations: [] };
  const on = keys.filter((k) => enabled.has(k));
  if (!on.length) return { entities: [], relations: [] };
  if (on.length === 1) {
    const slice = domains[on[0]!]!;
    return { entities: slice.entities ?? [], relations: slice.relations ?? [] };
  }
  return mergeDomainPayloads(
    on.map((k) => ({
      entities: domains[k]!.entities ?? [],
      relations: domains[k]!.relations ?? [],
    })),
  );
}

export type ErdGraphvizCanvasProps = {
  bundle: ErdDomainsBundle;
  includeOneHop: boolean;
  onIncludeOneHopChange: (next: boolean) => void;
};

export function ErdGraphvizCanvas({ bundle, includeOneHop, onIncludeOneHopChange }: ErdGraphvizCanvasProps) {
  const [layout, setLayout] = useState<ErdGraphvizLayout>("gv-dot-lr");
  const [svgMarkup, setSvgMarkup] = useState("");
  const [renderError, setRenderError] = useState<string | null>(null);
  const [gvBusy, setGvBusy] = useState(false);

  const enriched = useMemo(
    () => enrichErdDataForViewer(bundle as unknown as Record<string, unknown>),
    [bundle],
  );

  const domainKeyList = useMemo(() => {
    const d = enriched.domains as Record<string, unknown> | undefined;
    return d ? Object.keys(d).sort() : [];
  }, [enriched]);

  const [enabledDomains, setEnabledDomains] = useState(
    () => new Set(Object.keys(bundle.domains ?? {}).sort()),
  );

  useLayoutEffect(() => {
    setEnabledDomains(new Set(Object.keys(bundle.domains ?? {}).sort()));
  }, [bundle]);

  const mergedData = useMemo(
    () => getMergedFromDomains(enriched, enabledDomains),
    [enriched, enabledDomains],
  );

  const dot = useMemo(() => buildDotSource(mergedData, layout), [mergedData, layout]);

  const { viewportRef, pannerRef, zoomPct, fitToContainer, zoomIn, zoomOut, bindInteractions } = useSvgPanZoom();

  useEffect(() => {
    let cancelled = false;
    setGvBusy(true);
    setRenderError(null);
    loadGraphvizWasm()
      .then((gv) => {
        if (cancelled) return;
        const engine = erdGraphvizEngine(layout) as Engine;
        const svg = gv.layout(dot, "svg", engine);
        if (cancelled) return;
        setSvgMarkup(svg);
      })
      .catch((e) => {
        if (!cancelled) setRenderError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setGvBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [dot, layout]);

  useLayoutEffect(() => {
    if (!svgMarkup) return;
    const panner = pannerRef.current;
    if (!panner) return;

    const ac = new AbortController();
    const svg = panner.querySelector("svg");
    if (svg) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      const gg = svg.querySelector("g.graph");
      const bgPoly = gg?.querySelector("polygon");
      if (bgPoly) {
        const fill = String(bgPoly.getAttribute("fill") || "").toLowerCase();
        if (fill === "#f8fafc" || fill === "#f4f5f7" || fill === "lightgray" || fill === "lightgrey") {
          bgPoly.setAttribute("fill", "none");
        }
      }
    }

    const onEnter = (evt: Event) => {
      const el = evt.currentTarget as Element;
      const title = el.querySelector("title")?.textContent?.trim() || "";
      panner.querySelectorAll("g.node").forEach((n) => {
        (n as HTMLElement).style.opacity =
          n.querySelector("title")?.textContent?.trim() === title ? "1" : "0.35";
      });
      panner.querySelectorAll("g.edge").forEach((e) => {
        const edgeTitle = e.querySelector("title")?.textContent?.trim() || "";
        (e as HTMLElement).style.opacity = edgeTitle.includes(title) ? "1" : "0.2";
      });
    };
    const onLeave = () => {
      panner.querySelectorAll("g.node").forEach((n) => {
        (n as HTMLElement).style.opacity = "1";
      });
      panner.querySelectorAll("g.edge").forEach((e) => {
        (e as HTMLElement).style.opacity = "1";
      });
    };

    panner.querySelectorAll("g.node").forEach((node) => {
      (node as HTMLElement).style.cursor = "pointer";
      node.addEventListener("mouseenter", onEnter, { signal: ac.signal });
      node.addEventListener("mouseleave", onLeave, { signal: ac.signal });
    });

    let unbindPan: (() => void) | undefined;
    let cancelled = false;
    const raf = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (cancelled) return;
        fitToContainer();
        unbindPan = bindInteractions();
      });
    });

    return () => {
      cancelled = true;
      ac.abort();
      unbindPan?.();
      cancelAnimationFrame(raf);
    };
  }, [svgMarkup, fitToContainer, bindInteractions]);

  const accents = (enriched.domain_accent_colors ?? {}) as Record<string, string>;
  const icons = (enriched.domain_legend_icons ?? {}) as Record<string, string>;

  const toggleDomain = (key: string) => {
    setEnabledDomains((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0, position: "relative" }}>
      {renderError && (
        <Typography color="error" variant="body2" sx={{ p: 1 }}>
          {renderError}
        </Typography>
      )}
      <Box
        sx={{
          flex: 1,
          position: "relative",
          minHeight: 0,
          bgcolor: "#f4f5f7",
          backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
          backgroundSize: "20px 20px",
        }}
      >
        <DomainLegend
          domainKeys={domainKeyList}
          enabledDomains={enabledDomains}
          accents={accents}
          icons={icons}
          onToggle={toggleDomain}
        />

        <Box
          ref={viewportRef}
          className="erd-svg-viewport"
          sx={{
            position: "absolute",
            inset: 0,
            overflow: "hidden",
            cursor: "grab",
            touchAction: "none",
            zIndex: 1,
            "&.erd-panning": { cursor: "grabbing" },
          }}
        >
          {gvBusy && !svgMarkup && (
            <Typography variant="body2" sx={{ p: 2, color: "text.secondary" }}>
              Loading Graphviz…
            </Typography>
          )}
          <Box
            ref={pannerRef}
            className="erd-svg-panner"
            sx={{
              position: "absolute",
              left: 0,
              top: 0,
              transformOrigin: "0 0",
              willChange: "transform",
              "& svg": { display: "block", maxWidth: "none", height: "auto" },
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
            value={layout}
            onChange={(_, v: ErdGraphvizLayout | null) => {
              if (v !== null) setLayout(v);
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
                px: 0.75,
                py: 0.25,
                minWidth: 0,
                border: "none",
                bgcolor: "transparent",
                color: "#64748b",
                textTransform: "none",
                fontSize: 11,
                fontWeight: 500,
                lineHeight: 1.2,
                "&:hover": {
                  bgcolor: "rgba(15, 23, 42, 0.06)",
                  color: "#0f172a",
                },
                "&.Mui-selected": {
                  color: "#1d4ed8",
                  bgcolor: "transparent !important",
                  fontWeight: 600,
                },
                "&.Mui-selected:hover": {
                  bgcolor: "rgba(15, 23, 42, 0.06) !important",
                  color: "#1d4ed8",
                },
              },
            }}
          >
            <ToggleButton value="gv-dot-lr">Dot LR</ToggleButton>
            <ToggleButton value="gv-dot-tb">Dot TB</ToggleButton>
            <ToggleButton value="gv-neato">Neato</ToggleButton>
            <ToggleButton value="gv-fdp">FDP</ToggleButton>
            <ToggleButton value="gv-circo">Circo</ToggleButton>
          </ToggleButtonGroup>
          <Box
            component="span"
            aria-hidden
            sx={{ width: "1px", height: "22px", bgcolor: "rgba(15, 23, 42, 0.12)", flexShrink: 0, mx: "2px" }}
          />
          <OneHopToggle checked={includeOneHop} onChange={onIncludeOneHopChange} />
        </ZoomToolbar>
      </Box>
    </Box>
  );
}
