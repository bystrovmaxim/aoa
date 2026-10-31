// src/lib/mapFilterRows.ts
/**
 * The filter panel's rows on the map (spec 040, FR-027, FR-028b, FR-028c, FR-030): a section that does not paint shows
 * grey disks, a row with nothing left under the other filters dims and knows what keeps it off the screen, and whether
 * it is on stays the person's.
 */
import type { MapMark, MapOverview } from "@/api/map";
import type { ErdFilterRow } from "@/components/ui/ErdFilterPanel";
import { svgDataUriForGraphNodeIcon, svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import { MARK_LOOK } from "@/lib/erdDiffCard";
import { CHANGE_ORDER, statusDiskUri } from "@/lib/erdFilterPresence";
import type { PaintSection } from "@/lib/erdPaint";
import { OUTSIDE_AREA, type HiddenBy, type MapFilters, type MapPresence, type RowLeft } from "@/lib/mapVisibility";

const IDLE_DISK = "#cbd5e1";
const CHANGE_NAMES: Record<string, string> = { added: "Added", removed: "Removed", changed: "Changed", unchanged: "Unchanged" };

/** The rows of the three sections. */
export type MapFilterRows = { domainRows: ErdFilterRow[]; typeRows: ErdFilterRow[]; changeRows: ErdFilterRow[] };

/** What the filter rows are drawn from. */
type Names = { areas: ReadonlyMap<string, { name: string; colour: string }>; typeColours: Readonly<Record<string, string>> };

/** A switched-off filter as a dimmed row's card shows it. */
function shownReason(reason: HiddenBy, names: Names): { key: string; label: string; iconSrc: string } {
  if (reason.section === "domains") {
    const area = names.areas.get(reason.key);
    return { key: reason.key, label: area?.name ?? reason.key, iconSrc: svgDataUriForInterchangeDomainLegend(area?.colour ?? IDLE_DISK) };
  }
  if (reason.section === "types") return { key: reason.key, label: reason.key, iconSrc: svgDataUriForGraphNodeIcon(names.typeColours[reason.key] ?? IDLE_DISK, reason.key) };
  const look = reason.key === "unchanged" ? null : MARK_LOOK[reason.key as MapMark];
  return { key: reason.key, label: CHANGE_NAMES[reason.key] ?? reason.key, iconSrc: statusDiskUri(look?.colour ?? IDLE_DISK, look?.sign ?? "") };
}

function rowState(on: boolean, row: RowLeft | undefined, names: Names, reveal: (reasons: readonly HiddenBy[]) => void): Pick<ErdFilterRow, "on" | "absent" | "hidden"> {
  const absent = on && row !== undefined && row.total > 0 && row.left === 0;
  const reasons = row?.hiddenBy ?? [];
  return { on, absent, hidden: absent && reasons.length > 0 ? { by: reasons.map((reason) => shownReason(reason, names)), onReveal: () => reveal(reasons) } : undefined };
}

/** The rows of the panel for what is switched off and what paints. */
export function mapFilterRows(overview: MapOverview, filters: MapFilters, rows: MapPresence, paint: PaintSection, comparing: boolean, reveal: (reasons: readonly HiddenBy[]) => void): MapFilterRows {
  const names: Names = { areas: new Map(overview.areas.map((area) => [area.id, area])), typeColours: overview.type_colours };
  const domainRows = overview.areas
    .filter((area) => area.id !== OUTSIDE_AREA)
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((area) => ({ key: area.id, label: area.name, iconSrc: svgDataUriForInterchangeDomainLegend(paint === "domains" ? area.colour : IDLE_DISK), ...rowState(!filters.domains.has(area.id), rows.domains.get(area.id), names, reveal) }));
  const typeRows = overview.types.map((type) => ({ key: type, label: type, iconSrc: svgDataUriForGraphNodeIcon(paint === "kinds" ? (overview.type_colours[type] ?? IDLE_DISK) : IDLE_DISK, type), ...rowState(!filters.types.has(type), rows.types.get(type), names, reveal) }));
  const changeRows = comparing
    ? CHANGE_ORDER.filter((status) => (rows.changes.get(status)?.total ?? 0) > 0).map((status) => {
        const look = status === "unchanged" ? null : MARK_LOOK[status];
        return { key: status, label: CHANGE_NAMES[status], iconSrc: statusDiskUri(look && paint === "changes" ? look.colour : IDLE_DISK, look?.sign ?? ""), ...rowState(!filters.changes.has(status), rows.changes.get(status), names, reveal) };
      })
    : [];
  return { domainRows, typeRows, changeRows };
}
