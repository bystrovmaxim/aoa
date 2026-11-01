// src/components/diagrams/MapViewer/mapEngine.ts
/**
 * The map on screen (spec 040): the areas on a canvas below, the nodes and links in Sigma with WebGL, and the tags on a
 * canvas above. Detail is read as it comes into view and let go when the browser holds too much, so no zoom needs the
 * whole graph. Loaded lazily, with Sigma, so that no other diagram carries its weight.
 */
import { layerBorder } from "@sigma/node-border";
import { layerImage } from "@sigma/node-image";
import Graph from "graphology";
import Sigma from "sigma";
import { extremityArrow, layerFill, layerPlain, pathLine, sdfCircle } from "sigma/rendering";

import { drawnOn, type Half, type Side } from "@/lib/half";
import { halfTracking, hoverAcross, pickedArea, pickedRatio, reportHalfHover, setPickedArea, setPickedRatio, subscribeHalfHover, TRACK_REST_MS, type Located } from "@/lib/halfPicking";
import { mapArea, type MapArea, type MapChange, type MapDetail, type MapLink, type MapMark, type MapNode, type MapOverview, type MapSketchCell } from "@/api/map";
import type { CardProjection, CardSubject } from "@/components/diagrams/ElementCard";
import { cardBeside } from "@/lib/cardPlace";
import type { DiagramCounts } from "@/lib/erdDiff";
import { MARK_LOOK, type CardTarget } from "@/lib/erdDiffCard";
import { svgDataUriForGraphNodeGlyphOnly } from "@/lib/icons";
import { changesByArea, firstChangeOf } from "@/lib/mapDiff";
import type { PaintSection } from "@/lib/erdPaint";
import { LEVEL_SCREEN_PX, LEVEL_THREE_BAND, LEVEL_TWO_BAND, levelAt, openingRatio, revealOf, widthAtRatio } from "@/lib/mapLevels";
import { WHEEL_CHUNK_PX, WHEEL_ZOOM_SENSITIVITY, isZoomWheel, wheelPan } from "@/lib/wheelGesture";
import { outlineOf, type FieldPoint, type OutlineLoop } from "@/lib/mapOutline";
import { areaHolds, areaLeft, bundleLeft, bundleSays, cellsLeft, mapFacts, nodeLeft, type MapFacts, type MapFilters } from "@/lib/mapVisibility";
import { registerDiagramSurface, type DiagramSurface } from "@/rooms/diagramSurface";
import { isFollowing, mirroredFocus, reportHover, subscribeFocus, type ElementRef } from "@/rooms/focusStore";

/** How many nodes the browser keeps, a phone fewer. */
const MOST_NODES = 3000;
const MOST_NODES_ON_A_PHONE = 1500;

const NODE_SIZE: Record<number, number> = { 2: 30, 3: 15 };
const DOMAIN_NODE_SIZE = 46;
const TYPE_COLOURS_FALLBACK = "#64748b";
const LINK_COLOUR = "#94a3b8";
const ICON_PIXELS = 128;
/** How long outlines may be drawn in one frame. */
const OUTLINE_SLICE_MS = 6;
/** The zoom a room shares, scaled up: the address keeps three decimals, and a map's own zoom is far below 1. */
const ROOM_ZOOM = 100;
/** The map zooms in continuous steps, so following matches it closely; one redraw moves everything at once. */
const ROOM_ZOOM_TOLERANCE = 0.001;
const OUTSIDE_ID = "(outside)";
const OUTSIDE_NAME = "Outside domains";
/** How close the map goes: nodes at about their full size, no closer. */
const CLOSEST_RATIO = 0.55;
const UNCHANGED_COLOUR = "#cbd5e1";
/** A domain where nothing changed: grey and dim, as an unchanged table on the ERD. */
const UNTOUCHED_AREA_COLOUR = "#94a3b8";
/** How much of itself what did not change keeps beside what did. */
const FADED_NODE = 0.42;
const FADED_LINK = 0.3;
const FADED_AREA = 0.45;
/** How wide a view a step arrives at, in map units, by the level of the change: wide enough to see what stands around it. */
const ARRIVAL_WIDTH: Record<number, number> = { 2: 3200, 3: 1500 };
const ARRIVAL_MS = 750;
/** How much wider than a link the view it arrives at is, so that both its ends show. */
const LINK_MARGIN = 1.3;
const LINK_HALO_PX = 12;
const CARD_WIDTH = 312;

/** What the viewer gives the engine to draw in. */
export type MapElements = { stage: HTMLElement; sigma: HTMLElement; under: HTMLCanvasElement; over: HTMLCanvasElement; label: HTMLElement };

/** The card of a marked node, and where it stands on the stage. */
export type MapCard = { target: CardTarget; at: { x: number; y: number } };

/** What the viewer hears from the engine. */
/** What the map tells a hover card, and whether it opens at once, as a tap does (spec 043). */
export type MapEvents = {
  onZoom: (zoom: number) => void;
  onCard: (card: MapCard | null) => void;
  onStep: (position: number | null) => void;
  onHoverElement: (subject: CardSubject | null, now?: boolean) => void;
  /** In Side by side, a click on a node, or on nothing (spec 044). */
  onPick?: (node: string | null) => void;
};

type Loaded = { detail: MapDetail; level: 2 | 3; usedAt: number };

/** What of an area stands on the map: its outline and what the name stands with, around what the filters leave. */
type AreaView = { path: Path2D; whole: Path2D | null; left: number; total: number; x: number; y: number; radius: number };

/** How far two zooms may stand apart, as a log of their ratio, and still count as one. */
const ZOOM_ALIKE = 0.05;

/** The map's view in map units, kept across versions: switching to another version moves nothing on screen. Each half keeps its own. */
const keptViews = new Map<Side | null, { x: number; y: number; zoom: number } | null>();

/** ``#rrggbb`` with an alpha. */
function faded(colour: string, alpha: number): string {
  const value = parseInt(colour.slice(1), 16);
  return `rgba(${value >> 16},${(value >> 8) & 255},${value & 255},${alpha})`;
}

/** Closed smooth paths through outlines, in map units. */
function pathOf(loops: OutlineLoop[]): Path2D {
  const path = new Path2D();
  for (const loop of loops) {
    loop.forEach((point, index) => {
      const after = loop[(index + 1) % loop.length];
      const [x, y] = [(point[0] + after[0]) / 2, (point[1] + after[1]) / 2];
      if (index === 0) path.moveTo(x, y);
      else path.quadraticCurveTo(point[0], point[1], x, y);
    });
    path.closePath();
  }
  return path;
}

/** An area before its outline is ready. */
function circleOf(area: MapArea): Path2D {
  const path = new Path2D();
  path.arc(area.x, area.y, area.radius * 0.8, 0, Math.PI * 2);
  return path;
}

/** An outline around cells of an area's sketch: every place a weighted point, however many types stand there. */
function sketchOutline(area: MapArea, cells: readonly MapSketchCell[]): OutlineLoop[] {
  if (!area.sketch) return outlineOf([[area.x, area.y]]);
  const { cell } = area.sketch;
  const weights = new Map<string, { x: number; y: number; weight: number }>();
  for (const [column, row, , count] of cells) {
    const place = `${column},${row}`;
    const held = weights.get(place) ?? { x: area.x + (column + 0.5) * cell, y: area.y + (row + 0.5) * cell, weight: 0 };
    held.weight += Math.min(3, 0.8 + count / 4);
    weights.set(place, held);
  }
  const points: FieldPoint[] = [...weights.values()].map(({ x, y, weight }) => [x, y, weight]);
  return outlineOf(points, Math.max(120, cell));
}

/** Every type's glyph, rasterized once: an SVG data address does not reach the image atlas. */
async function rasterIcons(types: readonly string[]): Promise<Record<string, string>> {
  const icons: Record<string, string> = {};
  await Promise.all(
    types.map(async (type) => {
      const image = new Image();
      image.src = svgDataUriForGraphNodeGlyphOnly(type);
      await image.decode();
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = ICON_PIXELS;
      canvas.getContext("2d")?.drawImage(image, 0, 0, ICON_PIXELS, ICON_PIXELS);
      icons[type] = canvas.toDataURL("image/png");
    }),
  );
  return icons;
}

/** The map on screen. */
export class MapEngine {
  private readonly graph = new Graph({ multi: true, type: "directed" });
  private readonly sigma: Sigma;
  private readonly areaIndex: Map<string, number>;
  private readonly views: AreaView[];
  private readonly facts: MapFacts;
  private filters: MapFilters = { types: new Set(), domains: new Set(), changes: new Set() };
  private paint: PaintSection;
  private readonly bundles: { key: string; bundle: MapOverview["bundles"][number] }[] = [];
  private bundlesLeft = new Map<string, number>();
  /** Which round of outlines is being drawn: a newer filter stops an older round. */
  private outlineRound = 0;
  private readonly loaded = new Map<number, Loaded>();
  private readonly reading = new Map<string, Promise<void>>();
  /** Drawn on the canvas above: WebGL has no dashes. */
  private removedNodes: MapNode[] = [];
  private removedLinks: MapLink[] = [];
  private retargeted: MapLink[] = [];
  /** Where a folded domain's count stands on the stage, for a click on it. */
  private badges: { x: number; y: number; width: number; height: number; area: string }[] = [];
  private marking = false;
  private areaCounts = new Map<string, DiagramCounts>();
  /** Whatever changed claims its tag first, then the larger areas. */
  private tagOrder: { area: MapArea; index: number }[] = [];
  private position: number | null = null;
  private flight = 0;
  private cardOpen = false;
  /** Wheel zoom left to apply, a chunk a frame, and the point it zooms around. */
  private wheelLeft = 0;
  private wheelPoint = { x: 0, y: 0 };
  private wheeling = false;
  private readonly listening = new AbortController();
  /** While following: the node whose card the followed person has open. */
  private mirroredCard: MapChange | null = null;
  private readonly mostNodes = window.matchMedia("(max-width: 600px)").matches ? MOST_NODES_ON_A_PHONE : MOST_NODES;
  private levelTwo = 0;
  private levelThree = 0;
  /** In a half: what the pair marks, by id: a version's own map carries no marks of its own. */
  private readonly marks: ReadonlyMap<string, MapMark>;
  /** In a half: the element selected, lit as a hover is. */
  private pinned: string | null = null;
  private unpaired = false;
  private trackTimer: ReturnType<typeof setTimeout> | undefined;
  private selectionUnpaired = false;
  private hovered: string | null = null;
  private hoveredLink: string | null = null;
  private onBundle = false;
  private near: Set<string> | null = null;
  private refreshing = false;
  private clock = 0;
  private killed = false;
  private readonly fitRatio: number;
  private readonly unregister: () => void;
  private readonly stopHearing: () => void;

  private constructor(
    private readonly overview: MapOverview,
    private changes: readonly MapChange[],
    private readonly icons: Record<string, string>,
    private readonly elements: MapElements,
    private readonly events: MapEvents,
    private readonly half: Half | null,
  ) {
    this.marks = new Map(half ? changes.map((change) => [change.id, change.status]) : []);
    this.areaIndex = new Map(overview.areas.map((area, index) => [area.id, index]));
    this.facts = mapFacts(overview);
    this.paint = overview.links_changed === undefined ? "domains" : "changes";
    this.views = overview.areas.map((area) => ({ path: circleOf(area), whole: null, left: 1, total: 1, x: area.x, y: area.y, radius: area.radius }));
    overview.areas.forEach((area, index) => this.graph.addNode(`@${index}`, { x: area.x, y: area.y, size: 0.1, area: index, centre: true, label: "" }));
    for (const bundle of overview.bundles) {
      const [one, other, count, , changed = {}] = bundle;
      const marked = Object.values(changed).reduce((sum, each) => sum + (each ?? 0), 0);
      this.bundles.push({ key: this.graph.addDirectedEdge(`@${this.areaIndex.get(one)}`, `@${this.areaIndex.get(other)}`, { bundle: true, count, changed: marked }), bundle });
    }
    this.measure();
    this.fitRatio = openingRatio(this.ratioToFit(), overview.areas.length);
    this.sigma = new Sigma(this.graph, elements.sigma, {
      primitives: {
        nodes: {
          shapes: [sdfCircle()],
          layers: [layerFill(), layerImage({ name: "icon", drawingMode: "image", padding: 0.16, imageAttribute: "image" }), layerBorder({ borders: [{ size: 0.13, color: { attribute: "ring", default: "#00000000" }, mode: "relative" }, { size: 0, color: "#00000000", fill: true }] })],
        },
        edges: { paths: [pathLine()], extremities: [extremityArrow({ lengthRatio: 3.6, widthRatio: 2.6 })], layers: [layerPlain()] },
      },
      styles: {
        nodes: { opacity: { attribute: "opacity", defaultValue: 1 }, visibility: { attribute: "visibility", defaultValue: "visible" }, labelVisibility: { attribute: "labelVisibility", defaultValue: "auto" }, labelSize: 12, labelColor: "#0f172a", labelFont: "system-ui", zIndex: { attribute: "zIndex", defaultValue: 0 } },
        edges: { opacity: { attribute: "opacity", defaultValue: 1 }, visibility: { attribute: "visibility", defaultValue: "visible" }, head: { attribute: "head", defaultValue: "arrow" } },
      },
      settings: { itemSizesReference: "positions", zoomToSizeRatioFunction: (ratio: number) => ratio, autoRescale: false, labelRenderedSizeThreshold: 11, minCameraRatio: CLOSEST_RATIO, maxCameraRatio: Math.max(40, this.fitRatio * 1.5), renderEdgeLabels: false, enableEdgeEvents: true, inertiaRatio: 0, doubleClickZoomingRatio: 1 },
      nodeReducer: (id: string, data: object, attributes: Record<string, unknown>) => ({ ...data, ...this.nodeLook(id, attributes) }),
      edgeReducer: (id: string, data: object, attributes: Record<string, unknown>) => ({ ...data, ...this.edgeLook(id, attributes) }),
    } as never);
    this.sigma.getCamera().on("updated", () => this.onCamera());
    // The stage takes the wheel before Sigma does: it moves and zooms as every other diagram (spec 029, FR-053).
    elements.stage.addEventListener("wheel", (event) => this.onWheel(event), { capture: true, passive: false, signal: this.listening.signal });
    this.sigma.on("afterRender", () => this.drawCanvases());
    this.sigma.on("enterNode", ({ node }) => this.onHover(node));
    this.sigma.on("leaveNode", () => this.onHover(null));
    this.sigma.on("clickStage", ({ event }) => this.onClickStage(event.x, event.y));
    this.sigma.on("clickNode", ({ node }) => this.onClickNode(node));
    this.sigma.on("enterEdge", ({ edge, event }) => this.onHoverBundle(edge, event.x, event.y));
    this.sigma.on("leaveEdge", () => this.onLeaveBundle());
    this.fit();
    this.restoreKeptView();
    this.unregister = registerDiagramSurface(this.surface(), half?.side ?? null);
    const stopFollowing = subscribeFocus(() => this.followHover());
    const stopAcross = subscribeHalfHover(() => this.hoverFromAcross());
    this.stopHearing = () => {
      stopFollowing();
      stopAcross();
    };
    this.setView({ filters: this.filters, paint: this.paint, changes });
  }

  /** What the filters leave of every area, and where its name stands: nothing here waits for an outline. */
  private measure(): void {
    this.overview.areas.forEach((area, index) => Object.assign(this.views[index], areaLeft(area, this.filters, this.facts)));
  }

  /** Redraw outlines a few at a time between frames: all at once would stop the page, and the picture does not wait for them. */
  private drawOutlines(round: number, from = 0): void {
    if (round !== this.outlineRound || this.killed) return;
    const start = performance.now();
    let index = from;
    for (; index < this.overview.areas.length && performance.now() - start < OUTLINE_SLICE_MS; index += 1) {
      const area = this.overview.areas[index];
      const view = this.views[index];
      if (view.left === view.total) {
        view.whole ??= pathOf(sketchOutline(area, area.sketch?.cells ?? []));
        view.path = view.whole;
      } else if (view.left > 0) {
        view.path = pathOf(sketchOutline(area, cellsLeft(area, this.filters, this.facts)));
      }
    }
    this.drawCanvases();
    if (index < this.overview.areas.length) requestAnimationFrame(() => this.drawOutlines(round, index));
  }

  /**
   * Apply what the page chose: what the filters leave, what paints, and the changes left to step through. Nothing moves:
   * only what is drawn changes (FR-028).
   */
  setView(view: { filters: MapFilters; paint: PaintSection; changes: readonly MapChange[] }): void {
    const stoodOn = this.position === null ? null : this.changes[this.position]?.id;
    this.filters = view.filters;
    this.paint = view.paint;
    this.changes = view.changes;
    this.marking = view.changes.length > 0;
    this.areaCounts = changesByArea(view.changes);
    this.tagOrder = this.overview.areas.map((area, index) => ({ area, index })).sort((a, b) => Number(this.areaCounts.has(b.area.id)) - Number(this.areaCounts.has(a.area.id)) || b.area.radius - a.area.radius);
    this.bundlesLeft = new Map(this.bundles.map(({ key, bundle }) => [key, bundleLeft(bundle, view.filters)]));
    this.measure();
    this.collectStruck();
    this.outlineRound += 1;
    const round = this.outlineRound;
    requestAnimationFrame(() => this.drawOutlines(round));
    const position = stoodOn === undefined || stoodOn === null ? -1 : view.changes.findIndex((change) => change.id === stoodOn);
    this.position = position >= 0 ? position : null;
    if (position < 0 && this.cardOpen) this.closeCard();
    this.events.onStep(this.position);
    this.sigma.refresh({ skipIndexation: true });
  }

  private get fading(): boolean {
    return this.marking && this.paint === "changes";
  }

  /** Make the map; loads the icons first, so that no node is drawn without one. */
  static async create(overview: MapOverview, changes: readonly MapChange[], elements: MapElements, events: MapEvents, half: Half | null = null): Promise<MapEngine> {
    return new MapEngine(overview, changes, await rasterIcons(overview.types), elements, events, half);
  }

  /** Stay where the last map stood, when that place is on this one. */
  private restoreKeptView(): void {
    const view = keptViews.get(this.half?.side ?? null);
    if (view && this.overview.areas.some((area) => Math.hypot(area.x - view.x, area.y - view.y) < area.radius)) this.surface().restore(view);
  }

  /** Let go of everything. */
  destroy(): void {
    this.killed = true;
    keptViews.set(this.half?.side ?? null, this.surface().view());
    this.listening.abort();
    this.stopHearing();
    this.unregister();
    this.sigma.kill();
  }

  /** The room's view of the map: positions in map units, as every participant's picture shares them. */
  private surface(): DiagramSurface {
    const { stage } = this.elements;
    const camera = this.sigma.getCamera();
    const middle = () => this.sigma.viewportToGraph({ x: stage.clientWidth / 2, y: stage.clientHeight / 2 });
    return {
      element: stage,
      toDiagram: (client) => {
        const box = stage.getBoundingClientRect();
        return this.sigma.viewportToGraph({ x: client.x - box.left, y: client.y - box.top });
      },
      toClient: (point) => {
        const box = stage.getBoundingClientRect();
        const place = this.sigma.graphToViewport(point);
        return { x: place.x + box.left, y: place.y + box.top };
      },
      subscribe: (listener) => {
        camera.on("updated", listener);
        return () => {
          camera.off("updated", listener);
        };
      },
      centreOn: (point) => {
        const framed = this.sigma.viewportToFramedGraph(this.sigma.graphToViewport(point));
        camera.setState({ x: framed.x, y: framed.y });
      },
      zoomTolerance: ROOM_ZOOM_TOLERANCE,
      view: () => ({ ...middle(), zoom: ROOM_ZOOM / camera.ratio }),
      restore: (view) => {
        camera.setState({ ratio: ROOM_ZOOM / view.zoom });
        const framed = this.sigma.viewportToFramedGraph(this.sigma.graphToViewport(view));
        camera.setState({ x: framed.x, y: framed.y });
      },
    };
  }

  /** A swipe or a plain wheel moves the picture; a pinch or Ctrl / ⌘ + wheel zooms it around the pointer. */
  private onWheel(event: WheelEvent): void {
    // Over a panel on the stage the wheel is the panel's own.
    if (!(event.target instanceof Node) || !this.elements.sigma.contains(event.target)) return;
    event.preventDefault();
    event.stopPropagation();
    const { stage } = this.elements;
    if (!isZoomWheel(event)) {
      const { dx, dy } = wheelPan(event, stage.clientHeight);
      const camera = this.sigma.getCamera();
      const from = this.sigma.viewportToFramedGraph({ x: 0, y: 0 });
      const to = this.sigma.viewportToFramedGraph({ x: dx, y: dy });
      camera.setState({ x: camera.x + to.x - from.x, y: camera.y + to.y - from.y });
      return;
    }
    const box = stage.getBoundingClientRect();
    this.wheelPoint = { x: event.clientX - box.left, y: event.clientY - box.top };
    this.wheelLeft += event.deltaY;
    if (this.wheeling) return;
    this.wheeling = true;
    requestAnimationFrame(() => this.applyWheel());
  }

  private applyWheel(): void {
    this.wheeling = false;
    if (this.killed) return;
    const chunk = Math.max(-WHEEL_CHUNK_PX, Math.min(WHEEL_CHUNK_PX, this.wheelLeft));
    this.wheelLeft -= chunk;
    const camera = this.sigma.getCamera();
    camera.setState(this.sigma.getViewportZoomedState(this.wheelPoint, camera.getBoundedRatio(camera.ratio * Math.exp(chunk * WHEEL_ZOOM_SENSITIVITY))));
    if (Math.abs(this.wheelLeft) <= 0.5) return;
    this.wheeling = true;
    requestAnimationFrame(() => this.applyWheel());
  }

  /** The zoom of the toolbar: 1 shows the whole map. */
  zoom(): number {
    return this.fitRatio / this.sigma.getCamera().ratio;
  }

  /** Zoom by ``factor``, around the middle. */
  zoomBy(factor: number): void {
    const camera = this.sigma.getCamera();
    void camera.animate({ ratio: camera.ratio / factor }, { duration: 200 });
  }

  /** Show the whole map. */
  fit(): void {
    this.sigma.getCamera().setState({ x: 0, y: 0, ratio: this.fitRatio });
    this.centreOnMap();
  }

  private centreOnMap(): void {
    const { areas } = this.overview;
    const left = Math.min(...areas.map((area) => area.x - area.radius));
    const right = Math.max(...areas.map((area) => area.x + area.radius));
    const top = Math.min(...areas.map((area) => area.y - area.radius));
    const bottom = Math.max(...areas.map((area) => area.y + area.radius));
    const middle = this.sigma.viewportToFramedGraph(this.sigma.graphToViewport({ x: (left + right) / 2, y: (top + bottom) / 2 }));
    this.sigma.getCamera().setState({ x: middle.x, y: middle.y, ratio: this.fitRatio });
  }

  private ratioToFit(): number {
    const { areas } = this.overview;
    const { clientWidth, clientHeight } = this.elements.stage;
    const width = Math.max(...areas.map((area) => area.x + area.radius)) - Math.min(...areas.map((area) => area.x - area.radius));
    const height = Math.max(...areas.map((area) => area.y + area.radius)) - Math.min(...areas.map((area) => area.y - area.radius));
    return Math.max(width / Math.max(1, clientWidth - 40), height / Math.max(1, clientHeight - 40));
  }

  private areasInView(): MapArea[] {
    const { clientWidth, clientHeight } = this.elements.stage;
    const a = this.sigma.viewportToGraph({ x: 0, y: 0 });
    const b = this.sigma.viewportToGraph({ x: clientWidth, y: clientHeight });
    const [left, right] = [Math.min(a.x, b.x), Math.max(a.x, b.x)];
    const [top, bottom] = [Math.min(a.y, b.y), Math.max(a.y, b.y)];
    return this.overview.areas.filter((area) => area.x + area.radius > left && area.x - area.radius < right && area.y + area.radius > top && area.y - area.radius < bottom);
  }

  private onCamera(): void {
    const width = widthAtRatio(this.sigma.getCamera().ratio);
    const two = revealOf(width, LEVEL_TWO_BAND);
    const three = revealOf(width, LEVEL_THREE_BAND);
    const changed = two !== this.levelTwo || three !== this.levelThree;
    this.levelTwo = two;
    this.levelThree = three;
    this.elements.stage.style.backgroundPosition = `${-this.sigma.getCamera().x * 2000}px ${this.sigma.getCamera().y * 2000}px`;
    this.events.onZoom(this.zoom());
    if (this.mirroredCard) this.openCard(this.mirroredCard);
    else if (this.cardOpen) this.closeCard();
    const level = levelAt(width);
    if (level >= 2) this.readInView(level as 2 | 3);
    if (changed) this.refreshSoon();
  }

  private refreshSoon(): void {
    if (this.refreshing) return;
    this.refreshing = true;
    requestAnimationFrame(() => {
      this.refreshing = false;
      this.sigma.refresh({ skipIndexation: true });
    });
  }

  private readInView(level: 2 | 3): void {
    for (const area of this.areasInView()) {
      const held = this.loaded.get(this.areaIndex.get(area.id)!);
      if (held) held.usedAt = (this.clock += 1);
      if ((held && held.level >= level) || this.reading.has(area.id) || area.failed) continue;
      void this.read(area.id, level);
    }
  }

  /** A version's own detail with the pair's marks: everything that draws a change, struck nodes too, reads them there. */
  private marked(detail: MapDetail): MapDetail {
    if (!this.half) return detail;
    const mark = <T extends { id: string; diff?: MapMark }>(each: T): T => ({ ...each, diff: each.diff ?? this.marks.get(each.id) });
    return { nodes: detail.nodes.map(mark), edges: detail.edges.map(mark), across: detail.across.map(mark) };
  }

  /** Read one area up to a level, once however many ask. */
  private read(area: string, level: 2 | 3): Promise<void> {
    const running = this.reading.get(area);
    if (running) return running;
    const reading = mapArea(area, level, this.half?.read)
      .then((detail) => this.take(this.areaIndex.get(area)!, this.marked(detail), level))
      .catch(() => undefined)
      .finally(() => this.reading.delete(area));
    this.reading.set(area, reading);
    return reading;
  }

  /** Have an area on the map up to a level, whatever is being read: what a step arrives at may not have been read yet. */
  private async ensure(area: string, level: 2 | 3): Promise<void> {
    await this.reading.get(area);
    if ((this.loaded.get(this.areaIndex.get(area)!)?.level ?? 0) < level) await this.read(area, level);
  }

  /** Put one area's detail on the map, and let go of what is furthest from use. */
  private take(index: number, detail: MapDetail, level: 2 | 3): void {
    for (const node of detail.nodes) this.addNode(node, index);
    this.loaded.set(index, { detail, level, usedAt: (this.clock += 1) });
    this.addLinks(index);
    for (const [other, held] of this.loaded) if (other !== index) this.addAcross(held.detail.across, other);
    this.letGo();
    this.collectStruck();
    this.sigma.scheduleRefresh();
  }

  /** What the canvas above draws dashed, from what is loaded. */
  private collectStruck(): void {
    if (!this.marking) return;
    const details = [...this.loaded.values()].map((entry) => entry.detail);
    const links = details.flatMap((detail) => [...detail.edges, ...detail.across]);
    this.removedNodes = details.flatMap((detail) => detail.nodes.filter((node) => node.diff === "removed"));
    this.removedLinks = links.filter((link) => link.diff === "removed");
    this.retargeted = links.filter((link) => link.was);
  }

  private addNode(node: MapNode, area: number): void {
    if (this.graph.hasNode(node.id)) return;
    this.graph.addNode(node.id, { x: node.x, y: node.y, size: node.type === "Domain" ? DOMAIN_NODE_SIZE : NODE_SIZE[node.level], label: node.label, type2: node.type, level: node.level, area, image: this.icons[node.type], diff: node.diff ?? this.marks.get(node.id), chain: node.chain ?? 0, status: node.diff ?? this.marks.get(node.id) ?? node.glance ?? "unchanged" });
  }

  private addLinks(index: number): void {
    const held = this.loaded.get(index)!;
    for (const link of held.detail.edges) this.addLink(link);
    this.addAcross(held.detail.across, index);
  }

  private addAcross(links: readonly MapLink[], _index: number): void {
    for (const link of links) this.addLink(link);
  }

  private addLink(link: MapLink): void {
    if (this.graph.hasEdge(link.id) || !this.graph.hasNode(link.source) || !this.graph.hasNode(link.target)) return;
    this.graph.addDirectedEdgeWithKey(link.id, link.source, link.target, { level: link.level, diff: link.diff ?? this.marks.get(link.id) });
  }

  private letGo(): void {
    let held = [...this.loaded.values()].reduce((sum, entry) => sum + entry.detail.nodes.length, 0);
    const oldestFirst = [...this.loaded.entries()].sort((a, b) => a[1].usedAt - b[1].usedAt);
    const inView = new Set(this.areasInView().map((area) => this.areaIndex.get(area.id)));
    for (const [index, entry] of oldestFirst) {
      if (held <= this.mostNodes) return;
      if (inView.has(index)) continue;
      for (const node of entry.detail.nodes) if (this.graph.hasNode(node.id)) this.graph.dropNode(node.id);
      this.loaded.delete(index);
      held -= entry.detail.nodes.length;
    }
  }

  private nodeLook(id: string, node: Record<string, unknown>): Record<string, unknown> {
    if (node.centre) return { opacity: 0, size: 0.1, label: "", visibility: "visible" };
    const reveal = node.level === 2 ? this.levelTwo : this.levelThree;
    if (reveal <= 0.01) return { visibility: "hidden", label: "" };
    if (!this.stays(id, node)) return { visibility: "hidden", label: "" };
    const area = this.overview.areas[node.area as number];
    const mark = this.marking ? (node.diff as MapMark | undefined) : undefined;
    let opacity = reveal;
    if (this.fading && !mark) opacity *= FADED_NODE;
    if (this.near && !this.near.has(id)) opacity *= 0.25;
    const named = id === this.hovered ? "visible" : this.levelTwo < 0.9 ? "hidden" : node.level === 2 || this.levelThree > 0.9 ? "auto" : "hidden";
    return { ...node, color: this.nodeColour(area, node.type2 as string, mark), ring: mark && mark !== "removed" ? MARK_LOOK[mark].colour : "#00000000", opacity, size: (node.size as number) * (0.7 + 0.3 * reveal), visibility: "visible", labelVisibility: named, zIndex: mark ? 2 : 1 };
  }

  private stays(id: string, node: Record<string, unknown>): boolean {
    return nodeLeft(this.filters, this.facts, id, this.overview.areas[node.area as number]?.id ?? "", node.type2 as string, node.chain as number, node.status as string);
  }

  private nodeColour(area: MapArea | undefined, type: string, mark: MapMark | undefined): string {
    if (mark === "removed") return "#ffffff";
    if (this.paint === "kinds") return this.overview.type_colours[type] ?? TYPE_COLOURS_FALLBACK;
    if (!this.fading) return area?.colour ?? TYPE_COLOURS_FALLBACK;
    return mark ? MARK_LOOK[mark].colour : UNCHANGED_COLOUR;
  }

  private edgeLook(id: string, edge: Record<string, unknown>): Record<string, unknown> {
    const ratio = this.sigma ? this.sigma.getCamera().ratio : 1;
    if (edge.bundle) {
      const fading = 1 - this.levelTwo;
      if (fading <= 0.01) return { visibility: "hidden" };
      const left = this.bundlesLeft.get(id) ?? 0;
      if (left === 0) return { visibility: "hidden" };
      const marked = this.marking && (edge.changed as number) > 0;
      return { color: marked ? MARK_LOOK.changed.colour : LINK_COLOUR, size: Math.min(13, 2 + Math.log2(left) * 1.5) * ratio, opacity: (marked ? 0.7 : this.fading ? 0.4 * FADED_AREA : 0.4) * fading, head: "none" };
    }
    const [source, target] = this.graph.extremities(id);
    const reveal = edge.level === 2 ? this.levelTwo : this.levelThree;
    if (reveal <= 0.01 || this.filters.changes.has((edge.diff as string | undefined) ?? "unchanged")) return { visibility: "hidden" };
    if (!this.stays(source, this.graph.getNodeAttributes(source)) || !this.stays(target, this.graph.getNodeAttributes(target))) return { visibility: "hidden" };
    const mark = this.marking ? (edge.diff as MapMark | undefined) : undefined;
    if (mark === "removed") return { visibility: "hidden" };
    const lit = this.near !== null && (source === this.hovered || target === this.hovered);
    const fade = this.fading && !mark ? FADED_LINK : 1;
    return { color: mark ? MARK_LOOK[mark].colour : lit ? "#475569" : LINK_COLOUR, size: (mark ? 4 : lit ? 3.6 : 2.2) * ratio, opacity: reveal * fade * (this.near && !lit ? 0.1 : 0.65) };
  }

  /** The pointer came onto a node or left it: a person following shows what the followed person hovers instead. */
  private onHover(node: string | null): void {
    if (isFollowing()) return;
    const real = node !== null && !this.graph.getNodeAttribute(node, "centre");
    reportHover(real ? { kind: "node", id: node } : null);
    if (this.half) {
      setPickedRatio(this.sigma.getCamera().ratio);
      if (real) setPickedArea(this.overview.areas[this.graph.getNodeAttribute(node, "area") as number]?.id ?? null);
      reportHalfHover(this.half.side, real ? { kind: "node", id: node } : null);
    }
    this.showHover(node ?? this.pinned);
  }

  /** The other half's hover lights the same node here, by identity; its card stands there (spec 044, FR-010). */
  private hoverFromAcross(): void {
    if (!this.half) return;
    const hover = hoverAcross(this.half.side);
    const node = hover?.kind === "node" && this.graph.hasNode(hover.id) ? hover.id : this.pinned;
    const mark = hover ? this.marks.get(hover.id) : undefined;
    this.unpaired = this.selectionUnpaired || (mark !== undefined && !drawnOn(this.half.side, mark));
    if (node !== this.hovered || this.unpaired !== (this.near?.size === 0)) this.showHover(this.unpaired ? null : node, true);
    clearTimeout(this.trackTimer);
    if (hover?.kind === "node") this.trackTimer = setTimeout(() => void this.trackTo(hover.id), TRACK_REST_MS);
  }

  /**
   * Tracking: what the pointer rests on across is brought into view here at that half's zoom (spec 044). What a map draws
   * depends on its zoom, so at another zoom the same node may not show at all; one in view at that zoom moves nothing.
   */
  private async trackTo(node: string): Promise<void> {
    if (!halfTracking()) return;
    // What is rested on across may stand in an area this half, at its zoom, has not read yet.
    const area = pickedArea();
    if (!this.graph.hasNode(node) && area && this.areaIndex.has(area)) await this.ensure(area, 3);
    if (this.killed || !this.graph.hasNode(node)) return;
    const attributes = this.graph.getNodeAttributes(node);
    const place = this.sigma.graphToViewport({ x: attributes.x as number, y: attributes.y as number });
    const { clientWidth, clientHeight } = this.elements.stage;
    const ratio = pickedRatio() ?? this.sigma.getCamera().ratio;
    const sameZoom = Math.abs(Math.log(this.sigma.getCamera().ratio / ratio)) < ZOOM_ALIKE;
    if (sameZoom && place.x >= 0 && place.y >= 0 && place.x <= clientWidth && place.y <= clientHeight) return;
    const target = this.sigma.viewportToFramedGraph(place);
    void this.sigma.getCamera().animate({ x: target.x, y: target.y, ratio }, { duration: ARRIVAL_MS, easing: "cubicInOut" });
  }

  /**
   * Bring a selected node into view, keeping the zoom, or say why not (spec 044). The half that was clicked says which
   * area holds it, so this one can read that area first; without that, a node not read yet stays where it is.
   */
  async locate(node: string | null): Promise<Located> {
    this.pinned = node;
    this.selectionUnpaired = false;
    this.unpaired = false;
    this.showHover(node, true);
    if (node === null) return "in_view";
    const area = pickedArea();
    if (!this.graph.hasNode(node) && area && this.areaIndex.has(area)) await this.ensure(area, 3);
    if (this.killed) return "in_view";
    const mark = this.marks.get(node);
    if (!this.graph.hasNode(node) || (this.half && mark && !drawnOn(this.half.side, mark))) {
      this.pinned = null;
      this.selectionUnpaired = true;
      this.unpaired = true;
      this.showHover(null, true);
      return "absent";
    }
    this.pinned = node;
    this.showHover(node, true);
    const attributes = this.graph.getNodeAttributes(node);
    if (!this.stays(node, attributes)) return "hidden";
    const place = this.sigma.graphToViewport({ x: attributes.x as number, y: attributes.y as number });
    const { clientWidth, clientHeight } = this.elements.stage;
    if (!this.half?.phone && place.x >= 0 && place.y >= 0 && place.x <= clientWidth && place.y <= clientHeight) return "in_view";
    const target = this.sigma.viewportToFramedGraph(place);
    await this.sigma.getCamera().animate({ x: target.x, y: target.y }, { duration: ARRIVAL_MS, easing: "cubicInOut" });
    return "moved";
  }

  private followHover(): void {
    if (!isFollowing()) return;
    const hover = mirroredFocus()?.hover;
    const node = hover?.kind === "node" && this.graph.hasNode(hover.id) ? hover.id : null;
    if (node !== this.hovered) this.showHover(node);
  }

  /** Between the stage and the map: a card's place is said on the map, so a follower sets it on the same spot. */
  private readonly projection: CardProjection = {
    toDiagram: (point) => this.sigma.viewportToGraph(point),
    toStage: (point) => this.sigma.graphToViewport(point),
  };

  /** The card of what a followed person holds a card on, when this view has it. */
  cardSubject(ref: ElementRef): CardSubject | null {
    if (ref.kind === "node" && this.graph.hasNode(ref.id)) return this.nodeSubject(ref.id);
    if (ref.kind === "edge" && this.graph.hasEdge(ref.id)) return this.linkSubject(ref.id);
    return null;
  }

  /** The card's place beside a point of the stage. */
  private cardAt(x: number, y: number, reach: number): { x: number; y: number } {
    const { clientWidth, clientHeight } = this.elements.stage;
    const box = { left: x - reach, top: y - reach, right: x + reach, bottom: y + reach };
    return cardBeside({ left: 0, top: 0, right: clientWidth, bottom: clientHeight }, box, box);
  }

  /** A node's card: its name and type at once, the rest read when it opens (spec 043, FR-001). */
  private nodeSubject(node: string): CardSubject {
    const attributes = this.graph.getNodeAttributes(node);
    const place = this.sigma.graphToViewport(attributes as never);
    const mark = this.marking ? (attributes.diff as MapMark | undefined) : undefined;
    const title = attributes.label as string;
    return {
      key: `node:${node}`,
      ref: { kind: "node", id: node },
      title,
      detail: attributes.type as string,
      nodeId: node,
      change: mark ? { title, status: mark, elements: [{ kind: "node", id: node }] } : null,
      copy: title,
      at: this.cardAt(place.x, place.y, this.sigma.scaleSize(attributes.size as number)),
      project: this.projection,
    };
  }

  /** A link's card: the map holds its ends, and in Diff the comparison holds its changes. */
  private linkSubject(edge: string, x?: number, y?: number): CardSubject {
    const [source, target] = this.graph.extremities(edge) as [string, string];
    const name = (node: string) => this.graph.getNodeAttribute(node, "label") as string;
    const [from, to] = [this.sigma.graphToViewport(this.graph.getNodeAttributes(source) as never), this.sigma.graphToViewport(this.graph.getNodeAttributes(target) as never)];
    const mark = this.marking ? (this.graph.getEdgeAttribute(edge, "diff") as MapMark | undefined) : undefined;
    const title = `${name(source)} → ${name(target)}`;
    return {
      key: `edge:${edge}`,
      ref: { kind: "edge", id: edge },
      title,
      detail: "Link",
      nodeId: null,
      change: mark ? { title, status: mark, elements: [{ kind: "edge", id: edge }] } : null,
      at: this.cardAt(x ?? (from.x + to.x) / 2, y ?? (from.y + to.y) / 2, 8),
      project: this.projection,
    };
  }

  /** The pointer came onto a real link: bundles keep their label. */
  private onHoverLink(edge: string, x: number, y: number): void {
    if (isFollowing()) return;
    this.hoveredLink = edge;
    reportHover({ kind: "edge", id: edge });
    this.events.onHoverElement(this.linkSubject(edge, x, y));
  }

  private showHover(node: string | null, quiet = false): void {
    const { label, stage } = this.elements;
    // A node selected across may not have been read here yet, and one read earlier may have been let go.
    const attributes = node && this.graph.hasNode(node) ? this.graph.getNodeAttributes(node) : null;
    stage.style.cursor = attributes && !attributes.centre ? "pointer" : "";
    if (!node || !attributes || attributes.centre) {
      this.hovered = null;
      // An empty set puts everything out: what the other half points at has no pair here (spec 044).
      this.near = this.unpaired ? new Set() : null;
      label.style.display = "none";
      if (!isFollowing() && !quiet) this.events.onHoverElement(null);
    } else {
      this.hovered = node;
      this.near = new Set([node, ...this.graph.neighbors(node)]);
      if (!isFollowing() && !quiet) this.events.onHoverElement(this.nodeSubject(node));
    }
    this.sigma.refresh({ skipIndexation: true });
  }

  /** A bundle says how many links it holds and how many of them changed (FR-005, FR-023). */
  private onHoverBundle(edge: string, x: number, y: number): void {
    const { bundle, changed } = this.graph.getEdgeAttributes(edge);
    const left = this.bundlesLeft.get(edge) ?? 0;
    if (!bundle) {
      this.onHoverLink(edge, x, y);
      return;
    }
    if (left === 0 || isFollowing()) return;
    const marked = this.marking ? (changed as number) : 0;
    const { label } = this.elements;
    this.onBundle = true;
    label.textContent = bundleSays(left, marked);
    label.style.display = "block";
    label.style.left = `${x}px`;
    label.style.top = `${y + 12}px`;
    label.style.borderLeftColor = marked ? MARK_LOOK.changed.colour : LINK_COLOUR;
  }

  private onLeaveBundle(): void {
    if (this.hoveredLink !== null && !isFollowing()) {
      this.hoveredLink = null;
      reportHover(null);
      this.events.onHoverElement(null);
    }
    if (!this.onBundle) return;
    this.onBundle = false;
    this.elements.label.style.display = "none";
  }

  /** A click on a domain's count goes to its first change; on a folded domain, flies to it. */
  private onClickStage(x: number, y: number): void {
    this.closeCard();
    const badge = this.badges.find((each) => x >= each.x && x <= each.x + each.width && y >= each.y && y <= each.y + each.height);
    const first = badge ? firstChangeOf(this.changes, badge.area) : -1;
    if (!badge) this.events.onPick?.(null);
    if (first >= 0) this.goTo(first);
    else this.flyToAreaAt(x, y);
  }

  private onClickNode(node: string): void {
    const attributes = this.graph.getNodeAttributes(node);
    if (!attributes.centre) {
      setPickedArea(this.overview.areas[attributes.area as number]?.id ?? null);
      this.events.onPick?.(node);
    }
    const position = this.marking && attributes.diff ? this.changes.findIndex((change) => change.id === node) : -1;
    if (position < 0) {
      this.closeCard();
      // A tap has no hover to rest on: it opens the card (spec 043, FR-008).
      if (window.matchMedia("(pointer: coarse)").matches && !attributes.centre) this.events.onHoverElement(this.nodeSubject(node), true);
      return;
    }
    this.position = position;
    this.events.onStep(this.position);
    this.sigma.scheduleRefresh();
    this.openCard(this.changes[this.position]);
  }

  /** Where a change stands on this map: a half's own drawing has its own places, a link stands between its ends. */
  private placeOf(change: MapChange): { x: number; y: number } {
    if (!this.half) return change;
    if (this.graph.hasNode(change.id)) {
      const { x, y } = this.graph.getNodeAttributes(change.id);
      return { x: x as number, y: y as number };
    }
    if (this.graph.hasEdge(change.id)) {
      const [source, target] = this.graph.extremities(change.id).map((end) => this.graph.getNodeAttributes(end));
      return { x: ((source.x as number) + (target.x as number)) / 2, y: ((source.y as number) + (target.y as number)) / 2 };
    }
    const area = this.overview.areas.find((each) => each.id === change.area);
    return area ? { x: area.x, y: area.y } : change;
  }

  private openCard(change: MapChange): void {
    const place = this.sigma.graphToViewport(this.placeOf(change));
    const at = { x: Math.max(8, Math.min(place.x + 24, this.elements.stage.clientWidth - CARD_WIDTH)), y: Math.max(8, place.y + 18) };
    this.cardOpen = true;
    this.events.onCard({ target: { title: change.label, status: change.status, elements: [{ kind: change.span === undefined ? "node" : "edge", id: change.id }] }, at });
  }

  private closeCard(): void {
    this.cardOpen = false;
    this.events.onCard(null);
  }

  /** Show what a followed person stands on: the mark and the card, where following has brought the view (FR-025f). */
  mirror(position: number | null, card: boolean): void {
    const change = position === null ? null : (this.changes[position] ?? null);
    this.position = position;
    this.events.onStep(position);
    this.mirroredCard = card ? change : null;
    if (!this.mirroredCard && this.cardOpen) this.closeCard();
    this.sigma.scheduleRefresh();
    if (!change) return;
    void this.ensure(change.area, change.level as 2 | 3).then(() => {
      if (this.mirroredCard) this.openCard(this.mirroredCard);
      this.sigma.scheduleRefresh();
    });
  }

  /** Go to a change. */
  goTo(position: number): void {
    void this.flyTo(position);
  }

  /** Go to a change by its id: a half's list holds only what its version has, and a change it lacks moves nothing. */
  goToChange(id: string): void {
    const position = this.changes.findIndex((change) => change.id === id);
    if (position >= 0) void this.flyTo(position);
    else this.closeCard();
  }

  /** Fly to a change, read what it stands in if that has not been read, and open its card (FR-025a, FR-025c). */
  private async flyTo(position: number): Promise<void> {
    const change = this.changes[position];
    if (!change) return;
    const level = change.level as 2 | 3;
    this.position = position;
    this.flight += 1;
    const flight = this.flight;
    this.closeCard();
    this.events.onStep(position);
    // A change's place is the pair's drawing; a half stands it where its own version has it.
    if (this.half) await this.ensure(change.area, level);
    const place = this.placeOf(change);
    const target = this.sigma.viewportToFramedGraph(this.sigma.graphToViewport(place));
    const { clientWidth, clientHeight } = this.elements.stage;
    const ratio = Math.max(CLOSEST_RATIO, ARRIVAL_WIDTH[level] / LEVEL_SCREEN_PX, ((change.span ?? 0) * LINK_MARGIN) / Math.min(clientWidth, clientHeight));
    await Promise.all([this.sigma.getCamera().animate({ x: target.x, y: target.y, ratio }, { duration: ARRIVAL_MS, easing: "cubicInOut" }), this.ensure(change.area, level)]);
    if (flight !== this.flight || this.killed) return;
    this.sigma.scheduleRefresh();
    // A step is a click: it selects in both, and the half with no pair goes out (spec 044, FR-014).
    if (this.half && change.span === undefined) {
      setPickedArea(change.area);
      this.events.onPick?.(change.id);
    }
    if (this.half?.side !== "a" || change.status === "removed") this.openCard(change);
  }

  /** A click on a folded domain flies to it (FR-007). */
  private flyToAreaAt(x: number, y: number): void {
    if (this.levelTwo > 0.5) return;
    const point = this.sigma.viewportToGraph({ x, y });
    const area = this.overview.areas.find((each) => Math.hypot(each.x - point.x, each.y - point.y) < each.radius);
    if (!area) return;
    const target = this.sigma.viewportToFramedGraph(this.sigma.graphToViewport({ x: area.x, y: area.y }));
    const width = this.elements.stage.clientWidth;
    const ratio = Math.min(this.sigma.getCamera().ratio, ((area.radius * 2.6) / width) * 1);
    void this.sigma.getCamera().animate({ x: target.x, y: target.y, ratio: Math.min(ratio, (LEVEL_THREE_BAND[0] * 1.6) / LEVEL_SCREEN_PX) }, { duration: 650, easing: "cubicInOut" });
  }

  private drawCanvases(): void {
    const { stage, under, over } = this.elements;
    const ratio = window.devicePixelRatio;
    const [width, height] = [stage.clientWidth, stage.clientHeight];
    for (const canvas of [under, over]) {
      if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
        canvas.width = width * ratio;
        canvas.height = height * ratio;
      }
    }
    const below = under.getContext("2d");
    const above = over.getContext("2d");
    if (!below || !above) return;
    below.setTransform(1, 0, 0, 1, 0, 0);
    below.clearRect(0, 0, under.width, under.height);
    above.setTransform(1, 0, 0, 1, 0, 0);
    above.clearRect(0, 0, over.width, over.height);
    const origin = this.sigma.graphToViewport({ x: 0, y: 0 });
    const alongX = this.sigma.graphToViewport({ x: 1000, y: 0 });
    const alongY = this.sigma.graphToViewport({ x: 0, y: 1000 });
    const m = [(alongX.x - origin.x) / 1000, (alongX.y - origin.y) / 1000, (alongY.x - origin.x) / 1000, (alongY.y - origin.y) / 1000, origin.x, origin.y];
    const scale = Math.hypot(m[0], m[1]);
    const folded = 1 - this.levelTwo;
    const tags: [number, number, number, number][] = [];
    this.badges = [];
    for (const { area, index } of this.tagOrder) {
      const view = this.views[index];
      if (view.left === 0) continue;
      const [cx, cy] = [m[0] * view.x + m[2] * view.y + m[4], m[1] * view.x + m[3] * view.y + m[5]];
      const radius = view.radius * scale;
      if (cx + radius < 0 || cx - radius > width || cy + radius < 0 || cy - radius > height) continue;
      below.setTransform(ratio * m[0], ratio * m[1], ratio * m[2], ratio * m[3], ratio * m[4], ratio * m[5]);
      const untouched = this.fading && !this.areaCounts.has(area.id);
      const fade = untouched ? FADED_AREA : 1;
      const colour = untouched ? UNTOUCHED_AREA_COLOUR : this.fading && area.status ? MARK_LOOK[area.status].colour : area.colour;
      below.fillStyle = faded(colour, (0.1 + 0.13 * folded) * fade);
      below.fill(view.path);
      below.strokeStyle = faded(colour, 0.5 * fade);
      below.lineWidth = 1.4 / scale;
      below.setLineDash(this.marking && area.status === "removed" ? [8 / scale, 6 / scale] : []);
      below.stroke(view.path);
      this.drawTag(above, area, view, colour, fade, cx, cy, radius, folded, tags, ratio);
    }
    below.setLineDash([]);
    if (this.marking && this.levelTwo > 0.2) this.drawStruck(above, ratio);
    this.drawHalo(above, ratio);
  }

  private shows(node: string): boolean {
    if (!this.graph.hasNode(node)) return false;
    const attributes = this.graph.getNodeAttributes(node);
    return (attributes.level === 2 ? this.levelTwo : this.levelThree) >= 0.5 && this.stays(node, attributes);
  }

  /** A dashed line between two nodes on the map. */
  private drawDashed(canvas: CanvasRenderingContext2D, source: string, target: string): void {
    if (!this.shows(source) || !this.shows(target)) return;
    const from = this.sigma.graphToViewport(this.graph.getNodeAttributes(source) as never);
    const to = this.sigma.graphToViewport(this.graph.getNodeAttributes(target) as never);
    canvas.beginPath();
    canvas.moveTo(from.x, from.y);
    canvas.lineTo(to.x, to.y);
    canvas.stroke();
  }

  /** What was removed is dashed and red; a relation that points elsewhere now has a thin line to its target in A (FR-022). */
  private drawStruck(canvas: CanvasRenderingContext2D, ratio: number): void {
    canvas.setTransform(ratio, 0, 0, ratio, 0, 0);
    canvas.strokeStyle = MARK_LOOK.removed.colour;
    canvas.lineWidth = 2;
    canvas.setLineDash([6, 5]);
    if (!this.filters.changes.has("removed")) for (const link of this.removedLinks) this.drawDashed(canvas, link.source, link.target);
    canvas.strokeStyle = MARK_LOOK.changed.colour;
    canvas.lineWidth = 1;
    canvas.setLineDash([3, 3]);
    if (!this.filters.changes.has("changed")) for (const link of this.retargeted) this.drawDashed(canvas, link.source, link.was!);
    canvas.strokeStyle = MARK_LOOK.removed.colour;
    canvas.lineWidth = 1.8;
    canvas.setLineDash([3, 2.4]);
    for (const node of this.removedNodes) {
      if (!this.shows(node.id)) continue;
      const place = this.sigma.graphToViewport(node);
      canvas.beginPath();
      canvas.arc(place.x, place.y, this.sigma.scaleSize(this.graph.getNodeAttribute(node.id, "size") as number), 0, Math.PI * 2);
      canvas.stroke();
    }
    canvas.setLineDash([]);
  }

  /** The change a step arrived at wears a soft halo. */
  private drawHalo(canvas: CanvasRenderingContext2D, ratio: number): void {
    const change = this.position === null ? null : this.changes[this.position];
    const link = change?.span !== undefined;
    if (!change || (link ? !this.graph.hasEdge(change.id) : !this.shows(change.id))) return;
    const place = this.sigma.graphToViewport(change);
    canvas.setTransform(ratio, 0, 0, ratio, 0, 0);
    canvas.strokeStyle = MARK_LOOK[change.status].colour;
    canvas.globalAlpha = 0.28;
    canvas.lineWidth = 9;
    canvas.beginPath();
    canvas.arc(place.x, place.y, link ? LINK_HALO_PX : this.sigma.scaleSize(this.graph.getNodeAttribute(change.id, "size") as number) + 8, 0, Math.PI * 2);
    canvas.stroke();
    canvas.globalAlpha = 1;
  }

  private drawTag(canvas: CanvasRenderingContext2D, area: MapArea, view: AreaView, colour: string, fade: number, cx: number, cy: number, radius: number, folded: number, tags: [number, number, number, number][], ratio: number): void {
    if (radius < 14 && !this.areaCounts.has(area.id)) return;
    const { clientWidth: width, clientHeight: height } = this.elements.stage;
    if (this.levelTwo > 0.5 && Math.hypot(Math.min(Math.max(cx, 0), width) - width / 2, Math.min(Math.max(cy, 0), height) - height / 2) > radius + Math.min(width, height) * 0.42) return;
    const size = 11 + 3 * folded;
    canvas.setTransform(ratio, 0, 0, ratio, 0, 0);
    canvas.font = `600 ${size}px system-ui`;
    const name = area.id === OUTSIDE_ID ? OUTSIDE_NAME : area.name;
    const text = canvas.measureText(name).width;
    const x = Math.min(Math.max(cx - text / 2, 8), width - text - 16);
    const y = folded > 0.5 ? cy - size : Math.min(Math.max(cy - radius * 0.98, 12), height - 40);
    const cut = view.left < view.total ? `${view.left} of ${view.total} left` : null;
    const box: [number, number, number, number] = [x - 10, y - 5, text + 20, size + 12 + (folded > 0.25 ? 22 : cut ? 16 : 0)];
    if (tags.some((tag) => box[0] < tag[0] + tag[2] && tag[0] < box[0] + box[2] && box[1] < tag[1] + tag[3] && tag[1] < box[1] + box[3])) return;
    tags.push(box);
    canvas.globalAlpha = fade;
    canvas.fillStyle = colour;
    canvas.beginPath();
    canvas.roundRect(x - 8, y - 3, text + 16, size + 8, 6);
    canvas.fill();
    canvas.fillStyle = "#fff";
    canvas.textBaseline = "top";
    canvas.fillText(name, x, y + 1);
    canvas.globalAlpha = 1;
    if (folded <= 0.25) {
      if (cut) this.drawCut(canvas, cut, x + text / 2, y + size + 9, 1);
      return;
    }
    const counted = this.areaCounts.get(area.id);
    if (counted) {
      const parts = (["added", "removed", "changed"] as const).filter((status) => counted[status] > 0);
      this.drawBadges(canvas, area.id, cx, cy + 12, parts.map((status) => ({ status, text: `${MARK_LOOK[status].sign}${counted[status]}` })), folded);
      if (cut) this.drawCut(canvas, cut, cx, cy + 36, folded);
      return;
    }
    if (cut) {
      this.drawCut(canvas, cut, cx, cy + 14, folded * fade);
      return;
    }
    const says = areaHolds(area);
    canvas.globalAlpha = folded * fade;
    canvas.font = "11px system-ui";
    canvas.fillStyle = "#475569";
    canvas.fillText(says, cx - canvas.measureText(says).width / 2, cy + 14);
    canvas.globalAlpha = 1;
  }

  /** How much of an area the filters left, so that a filter's cut can be read (FR-029a). */
  private drawCut(canvas: CanvasRenderingContext2D, says: string, cx: number, y: number, alpha: number): void {
    canvas.globalAlpha = alpha;
    canvas.font = "600 11px system-ui";
    canvas.fillStyle = "#334155";
    canvas.fillText(says, cx - canvas.measureText(says).width / 2, y);
    canvas.globalAlpha = 1;
  }

  /** A folded domain's count of its changes by status, as pills a click takes to its first change. */
  private drawBadges(canvas: CanvasRenderingContext2D, area: string, cx: number, y: number, parts: { status: MapMark; text: string }[], alpha: number): void {
    canvas.font = "700 12px system-ui";
    canvas.globalAlpha = alpha;
    const widths = parts.map((part) => canvas.measureText(part.text).width + 12);
    const total = widths.reduce((sum, width) => sum + width + 4, -4);
    let x = cx - total / 2;
    this.badges.push({ x, y, width: total, height: 20, area });
    parts.forEach((part, index) => {
      const { colour } = MARK_LOOK[part.status];
      canvas.fillStyle = "#fff";
      canvas.beginPath();
      canvas.roundRect(x, y, widths[index], 20, 10);
      canvas.fill();
      canvas.strokeStyle = colour;
      canvas.lineWidth = 1.2;
      canvas.stroke();
      canvas.fillStyle = colour;
      canvas.fillText(part.text, x + 6, y + 4);
      x += widths[index] + 4;
    });
    canvas.globalAlpha = 1;
  }
}
