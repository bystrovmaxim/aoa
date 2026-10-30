// src/lib/viewUrl.ts
/**
 * Everything that shapes the picture of a page travels in the address (spec 038): its filters, layout and modes, and
 * what paints the ERD's headers — so a reload shows the same view and a copied link opens it for someone else. Each
 * setting is a parameter of its own, readable in the address bar: a list is its values joined by commas (``domains=``
 * with nothing after it is an empty list), a switch is ``1`` or ``0``, a choice is its name.
 */

import type { SavedView } from "@/rooms/diagramSurface";

type Kind = "list" | "switch" | "choice";

/** Page setting → its parameter in the address and how its value is written. */
const SETTINGS: Readonly<Record<string, { param: string; kind: Kind }>> = {
  layout: { param: "layout", kind: "choice" },
  domains: { param: "domains", kind: "list" },
  disabled_entities: { param: "off_entities", kind: "list" },
  disabled_kinds: { param: "off_kinds", kind: "list" },
  disabled_changes: { param: "off_changes", kind: "list" },
  one_hop: { param: "one_hop", kind: "switch" },
  boundary: { param: "boundary", kind: "switch" },
  rankdir: { param: "rankdir", kind: "choice" },
  paint: { param: "paint", kind: "choice" },
  paint_diff: { param: "paint_diff", kind: "choice" },
};

/**
 * Where the diagram is looked at: ``zoom`` and the diagram point at the centre of the screen, ``at=x,y`` — in the
 * diagram's own coordinates, so the same picture opens on a screen of another size.
 */
export const ZOOM_PARAM = "zoom";
export const AT_PARAM = "at";

/** Every parameter this module writes: the address keeps the others as they are. */
export const VIEW_PARAMS: readonly string[] = [...Object.values(SETTINGS).map((setting) => setting.param), ZOOM_PARAM, AT_PARAM];

/** A view of the diagram as address parameters, rounded so the address stays short. */
export function cameraToParams(view: SavedView | null): Record<string, string> {
  if (!view || !(view.zoom > 0)) return {};
  const round = (value: number, places: number) => String(Number(value.toFixed(places)));
  return { [ZOOM_PARAM]: round(view.zoom, 3), [AT_PARAM]: `${round(view.x, 1)},${round(view.y, 1)}` };
}

/** The view of the diagram an address names, or ``null`` when it names none or one out of shape. */
export function paramsToCamera(params: URLSearchParams): SavedView | null {
  const zoom = Number(params.get(ZOOM_PARAM));
  const [x, y] = (params.get(AT_PARAM) ?? "").split(",").map(Number);
  return zoom > 0 && Number.isFinite(x) && Number.isFinite(y) && params.get(AT_PARAM)?.includes(",") ? { x, y, zoom } : null;
}

/** A page's settings — what paints among them — as address parameters; a setting nobody set is left out. */
export function viewToParams(settings: Readonly<Record<string, unknown>>): Record<string, string> {
  const params: Record<string, string> = {};
  for (const [name, value] of Object.entries(settings)) {
    const setting = SETTINGS[name];
    if (!setting || value === undefined || value === null) continue;
    if (setting.kind === "list" && Array.isArray(value)) params[setting.param] = value.map(String).join(",");
    else if (setting.kind === "switch" && typeof value === "boolean") params[setting.param] = value ? "1" : "0";
    else if (setting.kind === "choice" && typeof value === "string") params[setting.param] = value;
  }
  return params;
}

/** The page settings an address names; a parameter out of shape is ignored. */
export function paramsToView(params: URLSearchParams): { settings: Record<string, unknown> } {
  const settings: Record<string, unknown> = {};
  for (const [name, setting] of Object.entries(SETTINGS)) {
    const raw = params.get(setting.param);
    if (raw === null) continue;
    if (setting.kind === "list") settings[name] = raw === "" ? [] : raw.split(",");
    else if (setting.kind === "switch" && (raw === "1" || raw === "0")) settings[name] = raw === "1";
    else if (setting.kind === "choice" && raw !== "") settings[name] = raw;
  }
  return { settings };
}
