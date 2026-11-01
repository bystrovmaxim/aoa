// src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx
import type { Engine } from "@hpcc-js/wasm-graphviz";
import Box from "@mui/material/Box";
import Snackbar from "@mui/material/Snackbar";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactElement, type SVGProps } from "react";
import { useSvgLayoutPair } from "@/lib/useSvgLayoutHash";
import { useSvgDiagramSurface } from "@/rooms/diagramSurface";
import { useGraphvizFocus } from "@/rooms/graphvizFocus";
import { enabledKeys } from "@/lib/freshGraph";
import { useCurrentPage, usePageSetting } from "@/lib/pageSettings";
import { CollapseAllButton, HoverCardsButton, ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { ErdFilterPanel, type ErdFilterRow } from "@/components/ui/ErdFilterPanel";
import { defaultPaint, paintSettingName, paintSource, type PaintSection } from "@/lib/erdPaint";
import { OneHopToggle } from "@/components/ui/OneHopToggle";
import { loadGraphvizWasm, loadGraphvizWasmFor } from "../../hooks/useGraphviz";
import { useSvgPanZoom } from "../../hooks/useSvgPanZoom";
import {
  buildDotSource,
  buildErdDot,
  ERD_CARD_RADIUS,
  ERD_CARD_STROKE,
  ERD_KIND_PAINT_PALETTE,
  setErdPaint,
  erdDiffMarks,
  erdGraphvizEngine,
  erdEdgeId,
  type ErdEntity,
  type ErdGraphPayload,
  type ErdGroup,
  type ErdGraphvizLayout,
  type ErdRelation,
} from "@/lib/buildDotSource";
import { containNodeFills } from "@/lib/containNodeFills";
import { enrichErdDataForViewer } from "@/lib/enrichErdData";
import { filterGraphByKinds, kindsOnDiagram, pruneGraphToEntities } from "@/lib/erdKindFilter";
import { changeDiskUri, changesOnDiagram, domainsOn, filterGraphByChanges, onScreen, tablesToDraw } from "@/lib/erdFilterPresence";
import { mergeRelationsOnScreen } from "@/lib/mergeErdRelations";
import { diagramCounts, erdHolds, erdOfSide, erdPortable, nothingChanged, unmarked } from "@/lib/erdDiff";
import { setDiffCounts, useDiffNames } from "@/lib/diffCounts";
import { HalfNote } from "@/components/diagrams/SideBySide";
import { svgOfHalf, useHalf, writesForPair } from "@/lib/half";
import { useHalfPicking, useSelectedElement } from "@/lib/halfPicking";
import { erdChanges } from "@/lib/erdDiffCard";
import { erdSubject, fromAfar, litBy } from "@/lib/erdCard";
import { erdFolds } from "@/lib/erdCollapse";
import { cardBeside, lineBoxes } from "@/lib/cardPlace";
import { useHoverCard } from "@/lib/useHoverCard";
import { ElementCard, type CardProjection, type CardSubject } from "@/components/diagrams/ElementCard";
import { elementRefOf, elementsOf, type HoverCards } from "@/rooms/graphvizFocus";
import { isFollowing, mirroredFocus, reportHover, type ElementRef } from "@/rooms/focusStore";
import { useGraphvizChangeStepping } from "@/lib/useGraphvizChangeStepping";
import { DiffCard } from "@/components/history/DiffCard";
import { COPY_CLICK_SLOP_PX } from "@/lib/erdCopy";
import type { ErdDomainsBundle } from "@/lib/loadErdDomainsBundle";
import { bindNameCopy } from "@/lib/erdCopy";
import { addEdgeHitAreas, addEndLabelBadges, bindLineHover, clearTableFocus, drawErdCards, erdEndLabelSx, erdLineHoverSx, focusTables, placeKindIcons } from "@/lib/erdPostPass";
import { postProcessGraphvizSvgDom } from "@/lib/sanitizeGraphvizSvgOverlays";
import { kindGlyphSvg, kindLegendDiskUri, svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import { diagramCanvasEmptyMessageSx } from "@/lib/ui";
import {
  LayoutGlyphCirco,
  LayoutGlyphDotLR,
  LayoutGlyphDotTB,
  LayoutGlyphFdp,
  LayoutGlyphNeato,
} from "./layoutEngineGlyphs";

function mergeDomainPayloads(parts: ErdGraphPayload[]): ErdGraphPayload {
  const nodeById = new Map<string, ErdEntity>();
  const seenRelations = new Set<string>();
  const relationsOut: ErdRelation[] = [];
  const edgeSig = (e: ErdRelation) => `${e.source}\u001f${e.target}\u001f${e.label ?? ""}`;
  const groupsOut: ErdGroup[] = [];
  const seenGroups = new Set<string>();
  for (const part of parts) {
    for (const n of part.entities ?? []) nodeById.set(n.id, n);
    for (const e of part.relations ?? []) {
      const sig = edgeSig(e);
      if (seenRelations.has(sig)) continue;
      seenRelations.add(sig);
      relationsOut.push(e);
    }
    for (const g of part.groups ?? []) {
      if (seenGroups.has(g.group_id)) continue;
      seenGroups.add(g.group_id);
      groupsOut.push(g);
    }
  }
  return { entities: [...nodeById.values()], relations: relationsOut, groups: groupsOut };
}

function getMergedFromDomains(enriched: Record<string, unknown>, enabled: Set<string>): ErdGraphPayload {
  const domainsRaw = enriched.domains;
  if (!domainsRaw || typeof domainsRaw !== "object") {
    return { entities: [], relations: [] };
  }
  const domains = domainsRaw as Record<
    string,
    { entities?: ErdEntity[]; relations?: ErdRelation[]; groups?: ErdGroup[] }
  >;
  const keys = Object.keys(domains);
  if (!keys.length) return { entities: [], relations: [] };
  const on = keys.filter((k) => enabled.has(k));
  if (!on.length) return { entities: [], relations: [] };
  if (on.length === 1) {
    const slice = domains[on[0]!]!;
    return { entities: slice.entities ?? [], relations: slice.relations ?? [], groups: slice.groups ?? [] };
  }
  const merged = mergeDomainPayloads(
    on.map((k) => ({
      entities: domains[k]!.entities ?? [],
      relations: domains[k]!.relations ?? [],
      groups: domains[k]!.groups ?? [],
    })),
  );
  // A line whose ends came from two slices is only in the request-wide list.
  const requestRelations = Array.isArray(enriched.relations) ? (enriched.relations as ErdRelation[]) : undefined;
  const onScreen = new Set((merged.entities ?? []).map((e) => e.id));
  return { ...merged, relations: mergeRelationsOnScreen(requestRelations, merged.relations ?? [], onScreen) };
}

function readEntityQual(e: ErdEntity): string | null {
  const q = e.domain_qualname?.trim();
  if (q) return q;
  const raw = (e as unknown as Record<string, unknown>).domain_qualname;
  return typeof raw === "string" && raw.trim() ? raw.trim() : null;
}

function collectEntityQualifiers(entities: ErdEntity[] | undefined, fallbackQual: string | null): string[] {
  const s = new Set<string>();
  for (const e of entities ?? []) {
    const q = readEntityQual(e) ?? fallbackQual;
    if (q) s.add(q);
  }
  return [...s].sort();
}

function filterGraphByEntityQuals(
  data: ErdGraphPayload,
  enabled: Set<string>,
  fallbackQual: string | null,
): ErdGraphPayload {
  return pruneGraphToEntities(data, (e) => {
    const q = readEntityQual(e) ?? fallbackQual;
    return q != null && q !== "" && enabled.has(q);
  });
}

export type ErdGraphvizCanvasProps = {
  bundle: ErdDomainsBundle;
  /** Increments only when the async loader has accepted a new bundle. */
  bundleVersion: number;
  includeOneHop: boolean;
  onIncludeOneHopChange: (next: boolean) => void;
};

const LAYOUT_TOOLS: {
  value: ErdGraphvizLayout;
  title: string;
  Glyph: (props: SVGProps<SVGSVGElement>) => ReactElement;
}[] = [
  { value: "gv-dot-lr", title: "Dot — left to right", Glyph: LayoutGlyphDotLR },
  { value: "gv-dot-tb", title: "Dot — top to bottom", Glyph: LayoutGlyphDotTB },
  { value: "gv-neato", title: "Neato (spring)", Glyph: LayoutGlyphNeato },
  { value: "gv-fdp", title: "FDP (force)", Glyph: LayoutGlyphFdp },
  { value: "gv-circo", title: "Circo (circular)", Glyph: LayoutGlyphCirco },
];


export function ErdGraphvizCanvas({
  bundle,
  bundleVersion,
  includeOneHop,
  onIncludeOneHopChange,
}: ErdGraphvizCanvasProps) {
  // Page settings: the person's own outside a room, the room's inside one (spec 028, FR-030).
  const [layout, setLayout] = usePageSetting<ErdGraphvizLayout>("layout", "gv-dot-lr");
  const [svgMarkup, setSvgMarkup] = useState("");
  /** Graphviz's output before the post-passes; its hash fixes every node's position (FR-005, FR-090). */
  const [rawSvg, setRawSvg] = useState("");
  const [svgRenderVersion, setSvgRenderVersion] = useState(0);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [gvBusy, setGvBusy] = useState(false);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);

  const enriched = useMemo(
    () => enrichErdDataForViewer(bundle as unknown as Record<string, unknown>),
    [bundle],
  );

  const domainKeyList = useMemo(() => {
    const d = enriched.domains as Record<string, unknown> | undefined;
    return d ? Object.keys(d).sort() : [];
  }, [enriched]);

  const multiTab = domainKeyList.length > 1;

  const bundleEntityTotal = useMemo(() => {
    const d = enriched.domains as Record<string, { entities?: ErdEntity[] }> | undefined;
    if (!d) return 0;
    let n = 0;
    for (const slice of Object.values(d)) {
      n += slice.entities?.length ?? 0;
    }
    return n;
  }, [enriched]);

  /** The domains switched on; ``null`` until someone chooses, which means all of them. */
  const [chosenDomains, setChosenDomains] = usePageSetting<string[] | null>("domains", null);
  /** Single-domain ERD: tables switched off, so a table 1-hop brings in later starts on. */
  const [disabledEntityList, setDisabledEntityList] = usePageSetting<string[]>("disabled_entities", []);
  /** Entity kinds switched off; a kind the graph gains later starts on. */
  const [disabledKindList, setDisabledKindList] = usePageSetting<string[]>("disabled_kinds", []);

  // A domain the model no longer has stops applying (spec 028, FR-076).
  const enabledDomains = useMemo(
    () => new Set(enabledKeys(Object.keys(bundle.domains ?? {}).sort(), chosenDomains)),
    [bundle, chosenDomains],
  );
  const disabledKinds = useMemo(() => new Set(disabledKindList), [disabledKindList]);

  const panZoom = useSvgPanZoom();
  const { viewportRef, pannerRef, zoomPct, fitToContainer, zoomIn, zoomOut, bindInteractions, resetFitFlag, needsFit, centreOnClient, onTransform } = panZoom;
  /** The tables the markup on hand was drawn from: a markup older than the tables shown now is never placed again. */
  const markupDataRef = useRef<{ entities: ErdEntity[]; relations?: ErdRelation[] } | null>(null);
  useSvgDiagramSurface(viewportRef, panZoom, Boolean(svgMarkup) && panZoom.fitted);
  const portable = useMemo(() => erdPortable(() => ({ entities: markupDataRef.current?.entities ?? [], relations: markupDataRef.current?.relations ?? [] })), []);

  const tabsOn = useMemo(() => (multiTab ? enabledDomains : new Set(domainKeyList)), [multiTab, enabledDomains, domainKeyList]);

  const mergedByTabs = useMemo(() => getMergedFromDomains(enriched, tabsOn), [enriched, tabsOn]);

  const fallbackQual = useMemo(() => {
    if (multiTab || domainKeyList.length === 0) return null;
    const tab0 = domainKeyList[0]!;
    return bundle.domain_qualifiers[tab0]?.trim() || null;
  }, [multiTab, domainKeyList, bundle.domain_qualifiers]);

  const entityQualList = useMemo(
    () => collectEntityQualifiers(mergedByTabs.entities, fallbackQual),
    [mergedByTabs.entities, fallbackQual],
  );

  const enabledEntityQualifiers = useMemo(
    () => new Set(entityQualList.filter((q) => !disabledEntityList.includes(q))),
    [entityQualList, disabledEntityList],
  );

  // The tables the diagram shows before kinds are filtered: its domains (or qualifiers) and one-hop.
  const beforeKinds = useMemo(() => {
    if (multiTab) return mergedByTabs;
    if (enabledEntityQualifiers.size === 0) return { entities: [], relations: [] };
    return filterGraphByEntityQuals(mergedByTabs, enabledEntityQualifiers, fallbackQual);
  }, [multiTab, mergedByTabs, enabledEntityQualifiers, fallbackQual]);

  // A table is on screen only when its domain (or qualifier) and its kind are both on.
  // A kind of change switched off hides its tables like any other filter (spec 038).
  const [offChangeList, setOffChangeList] = usePageSetting<string[]>("disabled_changes", []);
  const offChanges = useMemo(() => new Set(offChangeList), [offChangeList]);
  // The diagram's base: every table of the drawing that is open, before any filter. The filter rows come from it,
  // so a filter never adds or removes another filter's rows (spec 038).
  const baseGraph = useMemo(() => getMergedFromDomains(enriched, new Set(domainKeyList)), [enriched, domainKeyList]);
  const baseEntities = baseGraph.entities ?? [];
  // The own tables of the domains switched on, filtered; 1-hop then brings back the base's tables one line away from
  // those left — the neighbours from other domains, and any table a filter hid.
  const qualsOn = useMemo(() => domainsOn(bundle.domain_qualifiers, tabsOn), [bundle.domain_qualifiers, tabsOn]);
  const mergedData = useMemo(() => {
    const filtered = filterGraphByChanges(filterGraphByKinds(beforeKinds, disabledKinds), offChanges);
    return tablesToDraw(filtered, baseGraph, qualsOn, (entity) => readEntityQual(entity) ?? fallbackQual, includeOneHop);
  }, [beforeKinds, disabledKinds, offChanges, includeOneHop, baseGraph, qualsOn, fallbackQual]);

  const erdEmptyOverlay =
    mergedData.entities.length === 0 ? (
      <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
        {bundleEntityTotal === 0
          ? "No entities in this diagram."
          : "No entities for the selected domains."}
      </Typography>
    ) : null;

  // Each table carries its kind's display name for the header icon's tooltip.
  const labelledData = useMemo(() => {
    const labels = new Map((bundle.entity_kinds ?? []).map((row) => [row.entity_kind, row.label]));
    return {
      ...mergedData,
      entities: mergedData.entities.map((e) => ({ ...e, entity_kind_label: labels.get(e.entity_kind?.trim() || "unknown") })),
    };
  }, [mergedData, bundle.entity_kinds]);
  // In Diff the drawn diagram's counts go to the version button; when nothing on it changed it is drawn as One,
  // nothing faded (spec 038, FR-025, FR-026).
  const counts = useMemo(() => (bundle.diff ? diagramCounts(labelledData.entities, labelledData.relations ?? []) : null), [bundle.diff, labelledData]);
  const pairData = useMemo(() => (counts && nothingChanged(counts) ? unmarked({ ...labelledData, relations: labelledData.relations ?? [] }) : labelledData), [counts, labelledData]);
  const half = useHalf();
  // A half draws what its version has, in its own layout; the counts and the steps stay the pair's (spec 044).
  const drawnData = useMemo(() => (half ? erdOfSide(pairData, half.side) : pairData), [half, pairData]);
  const writesPair = writesForPair(half);
  useEffect(() => {
    if (writesPair) setDiffCounts(counts);
  }, [counts, writesPair]);
  // The steps through what the drawing marks (spec 040, FR-025e): the list follows the filters, as the counts do.
  // In a half each step points at that change's place on this half's own drawing; one that is not here has none.
  const changes = useMemo(() => {
    if (!counts || nothingChanged(counts)) return [];
    const pair = erdChanges(pairData.entities, pairData.relations ?? []);
    if (!half) return pair;
    const own = new Map(erdChanges(drawnData.entities, drawnData.relations ?? []).map((change) => [change.key, change.cell]));
    return pair.map((change) => ({ ...change, cell: own.get(change.key) ?? "" }));
  }, [counts, pairData, drawnData, half]);
  // A step opens its change's card (spec 038, FR-028); while it stands, a hover opens none (spec 043, FR-009).
  const { card, setCard } = useGraphvizChangeStepping({ changes, pannerRef, viewportRef, panZoom, svgMarkup, nodeKind: "table", portable });
  const hoverCard = useHoverCard<CardSubject>(card !== null);
  const { want: wantCard, wantNow: wantCardNow, close: closeCard, hold: holdCard, release: leaveCard } = hoverCard;
  // A cell's index means a table of the picture on screen, which lags the tables chosen while a new one is laid out.
  const drawnTables = useCallback(() => ({ entities: markupDataRef.current?.entities ?? [], relations: markupDataRef.current?.relations ?? [] }), []);
  const projection = useMemo<CardProjection>(() => {
    const frame = () => ({ picture: pannerRef.current!.getBoundingClientRect(), stage: viewportRef.current!.getBoundingClientRect(), scale: panZoom.getScale() });
    return {
      toDiagram: ({ x, y }) => {
        const { picture, stage, scale } = frame();
        return { x: (x + stage.left - picture.left) / scale, y: (y + stage.top - picture.top) / scale };
      },
      toStage: ({ x, y }) => {
        const { picture, stage, scale } = frame();
        return { x: x * scale + picture.left - stage.left, y: y * scale + picture.top - stage.top };
      },
    };
  }, [pannerRef, viewportRef, panZoom.getScale]);
  /** The card of ``ref``, placed beside its table, or ``null`` when it has none. */
  const subjectOf = useCallback(
    (ref: ElementRef, elements: readonly Element[], touch = false): CardSubject | null => {
      const panner = pannerRef.current;
      const stage = viewportRef.current?.getBoundingClientRect();
      const { entities, relations } = drawnTables();
      const named = fromAfar(ref, elements.at(-1), entities, touch);
      const facts = panner ? erdSubject(named, entities, panner, relations) : null;
      const [outer, inner] = [elements[0], named === ref ? elements.at(-1) : elements[0]];
      if (!facts || !stage || !outer || !inner) return null;
      // A line's box can span the screen: the card stands by its middle.
      const middle = (box: DOMRect) => ({ left: box.left + box.width / 2 - 4, top: box.top + box.height / 2 - 4, right: box.left + box.width / 2 + 4, bottom: box.top + box.height / 2 + 4 });
      const beside = named.kind === "edge" ? middle(outer.getBoundingClientRect()) : outer.getBoundingClientRect();
      const level = named.kind === "edge" ? beside : inner.getBoundingClientRect();
      const lit = litBy(named, entities, relations);
      const avoid = [
        ...lit.tables.flatMap((id) => elementsOf(panner!, { kind: "table", id }).slice(0, 1).map((table) => table.getBoundingClientRect())),
        ...lit.lines.flatMap((line) => {
          const edge = panner!.querySelector(`[id="${erdEdgeId(line)}"]`);
          return edge ? lineBoxes(edge) : [];
        }),
      ];
      return { ...facts, at: cardBeside(stage, beside, level), around: { beside, level, avoid }, project: projection };
    },
    [drawnTables, pannerRef, projection, viewportRef],
  );
  const hoverCards = useMemo<HoverCards>(
    () => ({
      has: (ref) => pannerRef.current !== null && erdSubject(ref, drawnTables().entities, pannerRef.current, drawnTables().relations) !== null,
      show: (ref, elements) => wantCard(ref ? subjectOf(ref, elements) : null),
      open: (ref, elements) => {
        const subject = subjectOf(ref, elements);
        if (subject) wantCardNow(subject);
      },
      close: closeCard,
    }),
    [closeCard, drawnTables, pannerRef, subjectOf, wantCard, wantCardNow],
  );
  // Hover and tooltip shared with followers, and the followed person's shown here (spec 029).
  useGraphvizFocus(pannerRef.current, svgMarkup, useCurrentPage(), "table", hoverCards, portable);
  // A card stands beside what it describes: a move or a new drawing takes that away, by whatever caused it.
  // For a follower it stays as long as the followed person holds it, and goes with the picture.
  const moveOrClose = useCallback(() => {
    const ref = isFollowing() ? mirroredFocus()?.panels.card?.ref : null;
    const panner = pannerRef.current;
    const subject = ref && panner ? subjectOf(ref, elementsOf(panner, ref)) : null;
    if (subject) wantCardNow(subject);
    else closeCard();
  }, [closeCard, pannerRef, subjectOf, wantCardNow]);
  useEffect(() => onTransform(moveOrClose), [moveOrClose, onTransform]);
  useEffect(() => moveOrClose(), [moveOrClose, svgMarkup]);
  // Tables collapsed to their keys (spec 043): one switch and the tables that differ from it, both page settings.
  const [fieldsCollapsed, setFieldsCollapsed] = usePageSetting<boolean>("fields_collapsed", false);
  const [fieldsExcept, setFieldsExcept] = usePageSetting<string[]>("fields_except", []);
  const selectedRow = useSelectedElement();
  const keptRow = selectedRow?.kind === "row" ? selectedRow.id : null;
  const folds = useMemo(() => erdFolds(drawnData.entities, drawnData.relations ?? [], fieldsCollapsed, new Set(fieldsExcept), keptRow), [drawnData, fieldsCollapsed, fieldsExcept, keptRow]);
  const foldedData = useMemo(() => ({ ...drawnData, folds }), [drawnData, folds]);
  const allCollapsed = fieldsCollapsed && fieldsExcept.length === 0;
  const canCollapse = useMemo(() => [...folds.values()].some((fold) => fold.hidden.size > 0), [folds]);
  /** Where the header of the table just toggled stood, so the new drawing keeps it there (FR-029). */
  const keptHeaderRef = useRef<{ table: number; left: number; top: number } | null>(null);
  const toggleFoldRef = useRef<(table: number, header: Element | null) => void>(() => undefined);
  toggleFoldRef.current = (table, header) => {
    const id = drawnTables().entities[table]?.id;
    if (!id) return;
    const box = header?.getBoundingClientRect();
    keptHeaderRef.current = box ? { table, left: box.left, top: box.top } : null;
    closeCard();
    setFieldsExcept(fieldsExcept.includes(id) ? fieldsExcept.filter((each) => each !== id) : [...fieldsExcept, id].sort());
  };
  // which filter section paints the headers in Diff, and the kinds of change switched off.
  // A kind's colour is its place in the model's list of kinds, not in this diagram's: the same kind is the same
  // colour on every diagram, for everyone.
  const kindPaint = useMemo(() => {
    const place = new Map((bundle.entity_kinds ?? []).map((row, index) => [row.entity_kind, index]));
    return Object.fromEntries(
      kindsOnDiagram(bundle.entity_kinds ?? [], baseEntities).map((row) => [row.entity_kind, ERD_KIND_PAINT_PALETTE[(place.get(row.entity_kind) ?? 0) % ERD_KIND_PAINT_PALETTE.length]]),
    );
  }, [bundle.entity_kinds, baseEntities]);
  // What paints the headers is a page setting, One's and Diff's apart: a room shares it, the address carries it.
  const diffDrawing = Boolean(bundle.diff);
  const [chosenPaint, setChosenPaint] = usePageSetting<PaintSection>(paintSettingName(diffDrawing), defaultPaint(diffDrawing));
  const paintSections: PaintSection[] = [
    "domains",
    ...(Object.keys(kindPaint).length > 1 ? (["kinds"] as const) : []),
    ...(diffDrawing && changesOnDiagram(baseEntities).length > 0 ? (["changes"] as const) : []),
  ];
  const paintSection = paintSource(paintSections, chosenPaint);
  const paintKey = `${paintSection}|${JSON.stringify(kindPaint)}`;
  const diffNames = useDiffNames();
  const ownBase = useMemo(() => (half ? erdOfSide({ ...baseGraph, entities: baseGraph.entities ?? [] }, half.side) : null), [half, baseGraph]);
  const halfNote = useHalfPicking({
    pannerRef,
    viewportRef,
    centreOnClient,
    drawing: svgMarkup,
    nodeKind: "table",
    holds: (ref) => (ownBase ? erdHolds(ownBase, ref) : false),
    portable,
  });
  useEffect(() => () => {
    if (writesPair) setDiffCounts(null);
  }, [writesPair]);

  // The text Graphviz is given carries the colours too: two tabs painting differently must not claim one input.
  const dot = useMemo(() => {
    setErdPaint(paintSection === "domains" ? "domain" : paintSection === "kinds" ? "kind" : "change", kindPaint);
    return buildDotSource(foldedData, layout);
  }, [foldedData, layout, paintSection, kindPaint]);
  // The picture's hash and the text Graphviz was given, hashed with it as one pair: the settings digest a room
  // compares layouts under (FR-093).
  const layoutPair = useSvgLayoutPair(rawSvg, `${erdGraphvizEngine(layout)}\n${dot}`);

  // Reset fit flag whenever the DOT source changes (new diagram, layout mode, or 1-hop toggle)
  // so the next SVG insertion always re-fits
  // A new drawing — other tables, another layout mode — fits again; new colours alone keep the view.
  const prevDrawingRef = useRef<{ data: unknown; layout: unknown } | null>(null);
  useLayoutEffect(() => {
    const previous = prevDrawingRef.current;
    if (!previous || previous.data !== drawnData || previous.layout !== layout) {
      prevDrawingRef.current = { data: drawnData, layout };
      resetFitFlag();
    }
  }, [drawnData, layout, resetFitFlag]);

  useEffect(() => {
    let cancelled = false;
    setGvBusy(true);
    setRenderError(null);
    setRawSvg("");
    const engine = erdGraphvizEngine(layout) as Engine;
    loadGraphvizWasm()
      .then((measurer) => {
        if (cancelled) return null;
        // Every table of a specialization block as wide as its widest table (spec 029): measured first, on the shared
        // instance. FDP depends on what ran before it in an instance, so the drawing itself is that instance's first layout.
        setErdPaint(paintSection === "domains" ? "domain" : paintSection === "kinds" ? "kind" : "change", kindPaint);
        const source = buildErdDot(foldedData, layout, (measureDot) => measurer.layout(measureDot, "svg", "dot"));
        return loadGraphvizWasmFor(engine).then((gv) => ({ gv, source }));
      })
      .then((prepared) => {
        if (cancelled || !prepared) return;
        const svg = prepared.gv.layout(prepared.source, "svg", engine);
        if (cancelled) return;
        setRawSvg(svg);
        // The renderer paints a card's band and row tints as rectangles inside a rounded outline;
        // this trims every fill to the contour before the markup reaches the page.
        markupDataRef.current = drawnData;
        setSvgMarkup(placeKindIcons(drawErdCards(containNodeFills(svg), ERD_CARD_RADIUS, ERD_CARD_STROKE, erdDiffMarks(drawnData.entities)), drawnData.entities, kindGlyphSvg, folds));
        setSvgRenderVersion((v) => v + 1);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dot, drawnData, layout, bundleVersion, resetFitFlag, paintKey]);

  useLayoutEffect(() => {
    if (!svgMarkup) return;
    const panner = pannerRef.current;
    if (!panner) return;
    // The tables changed and their new picture is still being laid out: the old one stays as it is, not placed again.
    if (markupDataRef.current !== drawnData) return;
    // The markup is placed here, not through ``dangerouslySetInnerHTML``: React re-applied that prop on
    // every render of the canvas (a zoom click is enough) and replaced the SVG, so the size, the table
    // hover and every listener bound below were lost on the drawing the user actually sees.
    panner.innerHTML = svgOfHalf(svgMarkup, half);

    const ac = new AbortController();
    const svg = panner.querySelector("svg");
    if (svg instanceof SVGSVGElement) {
      // Keep Graphviz as a real-size SVG canvas. If width/height are just removed,
      // browsers can fall back to a 300x150 SVG viewport and zoom math collapses.
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
      addEdgeHitAreas(svg);
      addEndLabelBadges(svg);
      bindLineHover(svg, drawnData.relations, drawnData.entities, ac.signal);
    }
    bindNameCopy(panner, setCopyMessage, ac.signal);
    let press: { x: number; y: number } | null = null;
    panner.addEventListener("pointerdown", (event) => void (press = { x: event.clientX, y: event.clientY }), { signal: ac.signal });
    const stayed = (event: MouseEvent) => press !== null && Math.hypot(event.clientX - press.x, event.clientY - press.y) <= COPY_CLICK_SLOP_PX;
    // On ``click``, not on the press's end: the new drawing rebinds the pan, and must not do so before ``mouseup`` has ended it.
    panner.addEventListener(
      "click",
      (event) => {
        const control = (event.target as Element | null)?.closest?.('g[id^="a_cl"]');
        if (!control || !stayed(event)) return;
        const table = Number(control.id.slice(4));
        toggleFoldRef.current(table, panner.querySelector(`[id="a_hd${table}"]`));
      },
      { signal: ac.signal },
    );
    // A tap has no hover to rest on: it opens the card, and the card's button copies (FR-008).
    panner.addEventListener(
      "pointerup",
      (event) => {
        const target = event.target as Element | null;
        if (event.pointerType !== "touch" || !target || !stayed(event) || target.closest?.('g[id^="a_cl"]')) return;
        const ref = elementRefOf(target, "table");
        const subject = ref ? subjectOf(ref, elementsOf(panner, ref), true) : null;
        if (!ref || !subject) return;
        reportHover(ref);
        wantCardNow(subject);
      },
      { signal: ac.signal },
    );

    const onEnter = (evt: Event) => {
      const el = evt.currentTarget as Element;
      focusTables(panner, new Set([el.querySelector("title")?.textContent?.trim() || ""]));
    };
    const onLeave = () => clearTableFocus(panner);

    panner.querySelectorAll("g.node").forEach((node) => {
      (node as HTMLElement).style.cursor = "pointer";
      node.addEventListener("mouseenter", onEnter, { signal: ac.signal });
      node.addEventListener("mouseleave", onLeave, { signal: ac.signal });
    });

    // A new drawing is fitted here, before the frame is painted, so no picture between the old view and the fitted one
    // ever shows; new colours alone keep the view. The triple rAF below fits again only if this one could not measure.
    if (needsFit()) fitToContainer();
    const kept = keptHeaderRef.current;
    keptHeaderRef.current = null;
    const header = kept ? panner.querySelector(`[id="a_hd${kept.table}"]`)?.getBoundingClientRect() : null;
    const stage = viewportRef.current?.getBoundingClientRect();
    if (kept && header && stage) centreOnClient(stage.left + stage.width / 2 + header.left - kept.left, stage.top + stage.height / 2 + header.top - kept.top);
    let unbindPan: (() => void) | undefined;
    let cancelled = false;

    const doFitAndBind = () => {
      if (cancelled) return;
      if (needsFit()) fitToContainer();
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
      ac.abort();
      unbindPan?.();
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      cancelAnimationFrame(raf3);
    };
  }, [svgMarkup, svgRenderVersion, fitToContainer, bindInteractions, drawnData, needsFit]);

  const tabAccents = (enriched.domain_accent_colors ?? {}) as Record<string, string>;

  const qualAccents = useMemo(() => {
    const out: Record<string, string> = {};
    const palette = bundle.domain_qualifier_colors;
    for (const q of entityQualList) {
      // A domain the palette does not list takes the first domain hue, never grey (grey is the kinds').
      out[q] = palette[q] ?? "#3b82f6";
    }
    return out;
  }, [entityQualList, bundle.domain_qualifier_colors]);

  const qualRowLabels = useMemo(() => {
    const byQual = bundle.domain_qualifier_labels ?? {};
    const out: Record<string, string> = {};
    for (const q of entityQualList) {
      const lbl = byQual[q]?.trim();
      if (lbl) out[q] = lbl;
    }
    return Object.keys(out).length > 0 ? out : undefined;
  }, [entityQualList, bundle.domain_qualifier_labels]);

  // Each change is sent as the whole new set, never as a toggle (FR-031).
  const toggleDomain = (key: string) => {
    const next = new Set(enabledDomains);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setChosenDomains([...next].sort());
  };

  const toggleKind = (kind: string) => {
    const next = new Set(disabledKinds);
    if (next.has(kind)) next.delete(kind);
    else next.add(kind);
    setDisabledKindList([...next].sort());
  };

  // a section that does not paint shows its disks grey — the colours on screen are one section's.
  const choosing = true;
  const domainsGrey = choosing && paintSection !== "domains";
  // One grey for every disk that does not paint: the domains' light grey.
  const IDLE_DISK = "#cbd5e1";
  const changesGrey = choosing && paintSection !== "changes";
  // The rows come from the base; a row with nothing of it on screen is dimmed, never switched on or off for it.
  const shown = onScreen(mergedData.entities, (entity) => readEntityQual(entity) ?? fallbackQual);
  // A domain is on screen by its own tables: a slice also carries its 1-hop neighbours from other domains.
  const tabShown = (key: string) => shown.domains.has(bundle.domain_qualifiers[key]?.trim() || null);
  const changeRows: ErdFilterRow[] = bundle.diff
    ? changesOnDiagram(baseEntities).map((status) => ({
        key: status,
        label: status.charAt(0).toUpperCase() + status.slice(1),
        iconSrc: changeDiskUri(status, !changesGrey),
        on: !offChanges.has(status),
        absent: !shown.changes.has(status),
      }))
    : [];
  const toggleChange = (status: string) => {
    const next = new Set(offChanges);
    if (next.has(status)) next.delete(status);
    else next.add(status);
    setOffChangeList([...next].sort());
  };

  const domainRows: ErdFilterRow[] = multiTab
    ? domainKeyList.map((key) => ({
        key,
        label: bundle.domain_tab_labels?.[key] ?? key,
        iconSrc: svgDataUriForInterchangeDomainLegend(domainsGrey ? "#cbd5e1" : tabAccents[key] || "#3b82f6"),
        on: enabledDomains.has(key),
        absent: !tabShown(key),
      }))
    : entityQualList.map((qual) => ({
        key: qual,
        label: qualRowLabels?.[qual] ?? qual,
        iconSrc: svgDataUriForInterchangeDomainLegend(domainsGrey ? "#cbd5e1" : qualAccents[qual] || "#3b82f6"),
        on: enabledEntityQualifiers.has(qual),
        absent: !shown.domains.has(qual),
      }));

  // Only the kinds this diagram has (spec 029, FR-044).
  const kindRows: ErdFilterRow[] = kindsOnDiagram(bundle.entity_kinds ?? [], baseEntities).map((row) => ({
    key: row.entity_kind,
    label: row.label,
    iconSrc: choosing ? kindLegendDiskUri(row.entity_kind, paintSection === "kinds" ? kindPaint[row.entity_kind] : IDLE_DISK) : kindLegendDiskUri(row.entity_kind),
    on: !disabledKinds.has(row.entity_kind),
    absent: !shown.kinds.has(row.entity_kind),
  }));


  const toggleEntityQual = (qual: string) => {
    const next = new Set(disabledEntityList);
    if (next.has(qual)) next.delete(qual);
    else next.add(qual);
    setDisabledEntityList([...next].sort());
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
        {domainRows.length > 0 && half?.side !== "b" && (
          <ErdFilterPanel
            domainRows={domainRows}
            kindRows={kindRows}
            onToggleDomain={multiTab ? toggleDomain : toggleEntityQual}
            onToggleKind={toggleKind}
            changeRows={changeRows}
            onToggleChange={toggleChange}
            paint={choosing ? { source: paintSection, onPaint: setChosenPaint } : null}
          />
        )}
        {erdEmptyOverlay}
        <HalfNote text={halfNote} />
        {half && !erdEmptyOverlay && drawnData.entities.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
            Not in {half.name}
          </Typography>
        )}
        <Snackbar
          open={copyMessage !== null}
          message={copyMessage ?? ""}
          autoHideDuration={1500}
          onClose={() => setCopyMessage(null)}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
          sx={{ position: "absolute", bottom: "64px !important" }}
        />

        <Box
          ref={viewportRef}
          data-layout-hash={layoutPair?.hash}
          data-layout-input={layoutPair?.digest}
          className="erd-svg-viewport"
          onPointerDownCapture={closeCard}
          sx={{
            position: "absolute",
            inset: 0,
            overflow: "hidden",
            cursor: "grab",
            touchAction: "none",
            zIndex: 1,
            "&.erd-panning": { cursor: "grabbing" },
            "&.erd-wheel-zooming .erd-svg-panner": { pointerEvents: "none" },
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
              display: "block",
              // A hovered line (or every line of a hovered row): thicker, a grey one darker, ends and roles following.
              ...erdLineHoverSx,
              // A line's end labels show only on hover, on a white plate (spec 029, FR-042).
              ...erdEndLabelSx,
              "@media (prefers-reduced-motion: reduce)": { "& g.edge path": { transition: "none" } },
              "& g[id^='a_cl'], & g[id^='a_cl'] text": { cursor: "pointer" },
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

        {card && <DiffCard target={card.target} newer={diffNames?.b ?? "B"} at={card.at} onClose={() => setCard(null)} />}
        {!card && hoverCard.shown && (
          <ElementCard
            key={hoverCard.shown.key}
            subject={hoverCard.shown}
            newer={diffNames?.b ?? "B"}
            onEnter={holdCard}
            onLeave={leaveCard}
            onClose={closeCard}
          />
        )}

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
            {LAYOUT_TOOLS.map(({ value, title, Glyph }) => (
              <ToggleButton key={value} value={value} aria-label={title}>
                <Tooltip title={title} placement="top">
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
                    <Glyph />
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
          <OneHopToggle checked={includeOneHop} onChange={onIncludeOneHopChange} />
          {canCollapse && (
            <CollapseAllButton
              collapsed={allCollapsed}
              onClick={() => {
                setFieldsCollapsed(!allCollapsed);
                setFieldsExcept([]);
              }}
            />
          )}
          <HoverCardsButton />
        </ZoomToolbar>
      </Box>
    </Box>
  );
}
