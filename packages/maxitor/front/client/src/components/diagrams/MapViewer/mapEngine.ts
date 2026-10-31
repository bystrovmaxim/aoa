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

import { mapArea, type MapArea, type MapDetail, type MapLink, type MapNode, type MapOverview } from "@/api/map";
import { svgDataUriForGraphNodeGlyphOnly } from "@/lib/icons";
import { LEVEL_THREE_BAND, LEVEL_TWO_BAND, levelAt, revealOf } from "@/lib/mapLevels";
import { outlineOf, type FieldPoint, type OutlineLoop } from "@/lib/mapOutline";
import { registerDiagramSurface, type DiagramSurface } from "@/rooms/diagramSurface";

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

/** What the viewer gives the engine to draw in. */
export type MapElements = { stage: HTMLElement; sigma: HTMLElement; under: HTMLCanvasElement; over: HTMLCanvasElement; label: HTMLElement };

/** What the viewer hears from the engine. */
export type MapEvents = { onZoom: (zoom: number) => void };

type Loaded = { detail: MapDetail; level: 2 | 3; usedAt: number };

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

/** An area's outline from its sketch: every cell a weighted point. */
function sketchOutline(area: MapArea): OutlineLoop[] {
  if (!area.sketch) return outlineOf([[area.x, area.y]]);
  const { cell, cells } = area.sketch;
  const points: FieldPoint[] = cells.map(([column, row, , count]) => [area.x + (column + 0.5) * cell, area.y + (row + 0.5) * cell, Math.min(3, 0.8 + count / 4)]);
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
  private readonly outlines: Path2D[];
  private readonly loaded = new Map<number, Loaded>();
  private readonly reading = new Set<string>();
  private readonly mostNodes = window.matchMedia("(max-width: 600px)").matches ? MOST_NODES_ON_A_PHONE : MOST_NODES;
  private levelTwo = 0;
  private levelThree = 0;
  private hovered: string | null = null;
  private near: Set<string> | null = null;
  private refreshing = false;
  private clock = 0;
  private killed = false;
  private readonly fitRatio: number;
  private readonly unregister: () => void;

  private constructor(
    private readonly overview: MapOverview,
    private readonly icons: Record<string, string>,
    private readonly elements: MapElements,
    private readonly events: MapEvents,
  ) {
    this.areaIndex = new Map(overview.areas.map((area, index) => [area.id, index]));
    this.outlines = overview.areas.map(circleOf);
    overview.areas.forEach((area, index) => this.graph.addNode(`@${index}`, { x: area.x, y: area.y, size: 0.1, area: index, centre: true, label: "" }));
    for (const [one, other, count] of overview.bundles) this.graph.addDirectedEdge(`@${this.areaIndex.get(one)}`, `@${this.areaIndex.get(other)}`, { bundle: true, count });
    this.fitRatio = this.ratioToFit();
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
      settings: { itemSizesReference: "positions", zoomToSizeRatioFunction: (ratio: number) => ratio, autoRescale: false, labelRenderedSizeThreshold: 11, minCameraRatio: CLOSEST_RATIO, maxCameraRatio: Math.max(40, this.fitRatio * 1.5), renderEdgeLabels: false, enableEdgeEvents: false },
      nodeReducer: (id: string, data: object, attributes: Record<string, unknown>) => ({ ...data, ...this.nodeLook(id, attributes) }),
      edgeReducer: (id: string, data: object, attributes: Record<string, unknown>) => ({ ...data, ...this.edgeLook(id, attributes) }),
    } as never);
    this.sigma.getCamera().on("updated", () => this.onCamera());
    this.sigma.on("afterRender", () => this.drawCanvases());
    this.sigma.on("enterNode", ({ node }) => this.onHover(node));
    this.sigma.on("leaveNode", () => this.onHover(null));
    this.sigma.on("clickStage", ({ event }) => this.flyToAreaAt(event.x, event.y));
    this.fit();
    this.unregister = registerDiagramSurface(this.surface());
    this.drawOutlines(0);
  }

  /** Replace the first circles by outlines a few at a time between frames: all at once would stop the page. */
  private drawOutlines(from: number): void {
    const start = performance.now();
    let index = from;
    for (; index < this.overview.areas.length && performance.now() - start < OUTLINE_SLICE_MS; index += 1) {
      this.outlines[index] = pathOf(sketchOutline(this.overview.areas[index]));
    }
    this.drawCanvases();
    if (index < this.overview.areas.length && !this.killed) requestAnimationFrame(() => this.drawOutlines(index));
  }

  /** Make the map; loads the icons first, so that no node is drawn without one. */
  static async create(overview: MapOverview, elements: MapElements, events: MapEvents): Promise<MapEngine> {
    return new MapEngine(overview, await rasterIcons(overview.types), elements, events);
  }

  /** Let go of everything. */
  destroy(): void {
    this.killed = true;
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

  private viewWidth(): number {
    const left = this.sigma.viewportToGraph({ x: 0, y: 0 });
    const right = this.sigma.viewportToGraph({ x: this.elements.stage.clientWidth, y: 0 });
    return Math.abs(right.x - left.x);
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
    const width = this.viewWidth();
    const two = revealOf(width, LEVEL_TWO_BAND);
    const three = revealOf(width, LEVEL_THREE_BAND);
    const changed = two !== this.levelTwo || three !== this.levelThree;
    this.levelTwo = two;
    this.levelThree = three;
    this.elements.stage.style.backgroundPosition = `${-this.sigma.getCamera().x * 2000}px ${this.sigma.getCamera().y * 2000}px`;
    this.events.onZoom(this.zoom());
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
      const index = this.areaIndex.get(area.id)!;
      const held = this.loaded.get(index);
      if (held) held.usedAt = (this.clock += 1);
      if ((held && held.level >= level) || this.reading.has(area.id) || area.failed) continue;
      this.reading.add(area.id);
      void mapArea(area.id, level)
        .then((detail) => this.take(index, detail, level))
        .catch(() => undefined)
        .finally(() => this.reading.delete(area.id));
    }
  }

  /** Put one area's detail on the map, and let go of what is furthest from use. */
  private take(index: number, detail: MapDetail, level: 2 | 3): void {
    for (const node of detail.nodes) this.addNode(node, index);
    this.loaded.set(index, { detail, level, usedAt: (this.clock += 1) });
    this.addLinks(index);
    for (const [other, held] of this.loaded) if (other !== index) this.addAcross(held.detail.across, other);
    this.letGo();
    this.sigma.scheduleRefresh();
  }

  private addNode(node: MapNode, area: number): void {
    if (this.graph.hasNode(node.id)) return;
    this.graph.addNode(node.id, { x: node.x, y: node.y, size: node.type === "Domain" ? DOMAIN_NODE_SIZE : NODE_SIZE[node.level], label: node.label, type2: node.type, level: node.level, area, image: this.icons[node.type] });
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
    this.graph.addDirectedEdgeWithKey(link.id, link.source, link.target, { level: link.level });
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
    const area = this.overview.areas[node.area as number];
    let opacity = reveal;
    if (this.near && !this.near.has(id)) opacity *= 0.25;
    const named = id === this.hovered ? "visible" : this.levelTwo < 0.9 ? "hidden" : node.level === 2 || this.levelThree > 0.9 ? "auto" : "hidden";
    return { ...node, color: area?.colour ?? TYPE_COLOURS_FALLBACK, opacity, size: (node.size as number) * (0.7 + 0.3 * reveal), visibility: "visible", labelVisibility: named, zIndex: 1 };
  }

  private edgeLook(id: string, edge: Record<string, unknown>): Record<string, unknown> {
    const ratio = this.sigma ? this.sigma.getCamera().ratio : 1;
    if (edge.bundle) {
      const fading = 1 - this.levelTwo;
      if (fading <= 0.01) return { visibility: "hidden" };
      return { color: LINK_COLOUR, size: Math.min(13, 2 + Math.log2(edge.count as number) * 1.5) * ratio, opacity: 0.4 * fading, head: "none" };
    }
    const [source, target] = this.graph.extremities(id);
    const reveal = edge.level === 2 ? this.levelTwo : this.levelThree;
    if (reveal <= 0.01) return { visibility: "hidden" };
    const lit = this.near !== null && (source === this.hovered || target === this.hovered);
    return { color: lit ? "#475569" : LINK_COLOUR, size: (lit ? 3.6 : 2.2) * ratio, opacity: reveal * (this.near && !lit ? 0.1 : 0.65) };
  }

  private onHover(node: string | null): void {
    const { label } = this.elements;
    const attributes = node ? this.graph.getNodeAttributes(node) : null;
    if (!node || !attributes || attributes.centre) {
      this.hovered = null;
      this.near = null;
      label.style.display = "none";
    } else {
      this.hovered = node;
      this.near = new Set([node, ...this.graph.neighbors(node)]);
      const place = this.sigma.graphToViewport(attributes as never);
      label.textContent = attributes.label as string;
      label.style.display = "block";
      label.style.left = `${place.x}px`;
      label.style.top = `${place.y + this.sigma.scaleSize(attributes.size as number) + 6}px`;
      label.style.borderLeftColor = this.overview.areas[attributes.area as number]?.colour ?? LINK_COLOUR;
    }
    this.sigma.refresh({ skipIndexation: true });
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
    void this.sigma.getCamera().animate({ x: target.x, y: target.y, ratio: Math.min(ratio, (LEVEL_THREE_BAND[0] * 1.6) / width) }, { duration: 650, easing: "cubicInOut" });
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
    const biggestFirst = this.overview.areas.map((area, index) => ({ area, index })).sort((a, b) => b.area.radius - a.area.radius);
    for (const { area, index } of biggestFirst) {
      const [cx, cy] = [m[0] * area.x + m[2] * area.y + m[4], m[1] * area.x + m[3] * area.y + m[5]];
      const radius = area.radius * scale;
      if (cx + radius < 0 || cx - radius > width || cy + radius < 0 || cy - radius > height) continue;
      below.setTransform(ratio * m[0], ratio * m[1], ratio * m[2], ratio * m[3], ratio * m[4], ratio * m[5]);
      below.fillStyle = faded(area.colour, 0.1 + 0.13 * folded);
      below.fill(this.outlines[index]);
      below.strokeStyle = faded(area.colour, 0.5);
      below.lineWidth = 1.4 / scale;
      below.stroke(this.outlines[index]);
      this.drawTag(above, area, cx, cy, radius, folded, tags, ratio);
    }
  }

  private drawTag(canvas: CanvasRenderingContext2D, area: MapArea, cx: number, cy: number, radius: number, folded: number, tags: [number, number, number, number][], ratio: number): void {
    if (radius < 14) return;
    const { clientWidth: width, clientHeight: height } = this.elements.stage;
    if (this.levelTwo > 0.5 && Math.hypot(Math.min(Math.max(cx, 0), width) - width / 2, Math.min(Math.max(cy, 0), height) - height / 2) > radius + Math.min(width, height) * 0.42) return;
    const size = 11 + 3 * folded;
    canvas.setTransform(ratio, 0, 0, ratio, 0, 0);
    canvas.font = `600 ${size}px system-ui`;
    const name = area.id === OUTSIDE_ID ? OUTSIDE_NAME : area.name;
    const text = canvas.measureText(name).width;
    const x = Math.min(Math.max(cx - text / 2, 8), width - text - 16);
    const y = folded > 0.5 ? cy - size : Math.min(Math.max(cy - radius * 0.98, 12), height - 40);
    const box: [number, number, number, number] = [x - 10, y - 5, text + 20, size + 12 + (folded > 0.25 ? 22 : 0)];
    if (tags.some((tag) => box[0] < tag[0] + tag[2] && tag[0] < box[0] + box[2] && box[1] < tag[1] + tag[3] && tag[1] < box[1] + box[3])) return;
    tags.push(box);
    canvas.fillStyle = area.colour;
    canvas.beginPath();
    canvas.roundRect(x - 8, y - 3, text + 16, size + 8, 6);
    canvas.fill();
    canvas.fillStyle = "#fff";
    canvas.textBaseline = "top";
    canvas.fillText(name, x, y + 1);
    if (folded <= 0.25) return;
    const entities = area.counts.Entity ?? 0;
    const actions = area.counts.Action ?? 0;
    const total = Object.values(area.counts).reduce((sum, count) => sum + count, 0);
    const says = [entities && `${entities} ${entities === 1 ? "entity" : "entities"}`, actions && `${actions} ${actions === 1 ? "action" : "actions"}`].filter(Boolean).join(" · ") || `${total} ${total === 1 ? "element" : "elements"}`;
    canvas.globalAlpha = folded;
    canvas.font = "11px system-ui";
    canvas.fillStyle = "#475569";
    canvas.fillText(says, cx - canvas.measureText(says).width / 2, cy + 14);
    canvas.globalAlpha = 1;
  }
}
