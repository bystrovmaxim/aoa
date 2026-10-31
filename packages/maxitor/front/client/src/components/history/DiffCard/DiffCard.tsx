// src/components/history/DiffCard/DiffCard.tsx
import Box from "@mui/material/Box";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Paper from "@mui/material/Paper";
import { useEffect, useState } from "react";
import { compareElement, type ChangedPart, type ElementDifference } from "@/api/compare";
import { MARK_LOOK, type CardTarget } from "@/lib/erdDiffCard";

export type DiffCardProps = {
  target: CardTarget;
  /** The newer version's name: what an element was added or removed in. */
  newer: string;
  /** Where the card stands, in its container's pixels. */
  at: { x: number; y: number };
  onClose: () => void;
};

/** A value as the card writes it: text as it is, anything else as JSON — never as markup. */
export function shownValue(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

/** Every difference of the elements a card reads; an element neither version has is left out. */
async function differencesOf(target: CardTarget): Promise<ElementDifference[]> {
  const answers = await Promise.all(target.elements.map((element) => compareElement(element.kind, element.id).catch(() => null)));
  const seen = new Set<string>();
  return answers
    .flatMap((answer) => answer?.differences ?? [])
    .filter((difference) => {
      const key = `${difference.path.join(".")}|${shownValue(difference.before)}|${shownValue(difference.after)}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

/** One property that changed: its path, and its value in A and in B. */
function DifferenceRow({ difference }: { difference: ElementDifference }) {
  return (
    <Box data-testid="diff-row" sx={{ display: "grid", gridTemplateColumns: "minmax(70px, auto) 1fr", gap: "6px", py: "4px", borderTop: "1px solid rgba(15, 23, 42, 0.06)" }}>
      <Box sx={{ color: "#64748b", wordBreak: "break-all" }}>{difference.path.join(".")}</Box>
      <Box sx={{ wordBreak: "break-word" }}>
        {difference.change === "added" ? (
          <>added: {shownValue(difference.after)}</>
        ) : difference.change === "removed" ? (
          <>removed: {shownValue(difference.before)}</>
        ) : (
          <>
            <s>{shownValue(difference.before)}</s> → {shownValue(difference.after)}
          </>
        )}
      </Box>
    </Box>
  );
}

/** The parts by the group they belong to, in the order they came. */
function groupedParts(parts: readonly ChangedPart[]): [string, ChangedPart[]][] {
  const groups = new Map<string, ChangedPart[]>();
  for (const part of parts) groups.set(part.group, [...(groups.get(part.group) ?? []), part]);
  return [...groups];
}

/**
 * The card of a changed table or row in Diff (spec 038, FR-028, FR-029): every property that changed, by its path,
 * before and after; an added or removed element says so in one line. Parts changed inside an element come below,
 * by group (spec 041, FR-012). Values are text. A click outside or Escape closes it.
 */
export function DiffCard({ target, newer, at, onClose }: DiffCardProps) {
  const [differences, setDifferences] = useState<ElementDifference[] | null>(null);
  const look = MARK_LOOK[target.status];
  const inside = Boolean(target.parts?.length);
  const groups = groupedParts(target.parts ?? []);

  useEffect(() => {
    let live = true;
    setDifferences(null);
    if (target.status === "changed") void differencesOf(target).then((found) => live && setDifferences(found));
    return () => {
      live = false;
    };
  }, [target]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <ClickAwayListener onClickAway={onClose}>
      <Paper
        role="dialog"
        aria-label={`What changed in ${target.title}`}
        elevation={0}
        data-testid="diff-card"
        sx={{
          position: "absolute",
          left: at.x,
          top: at.y,
          zIndex: 60,
          width: 300,
          maxHeight: `calc(100% - ${at.y + 8}px)`,
          boxSizing: "border-box",
          overflowY: "auto",
          p: "10px 12px",
          fontSize: 12,
          lineHeight: 1.45,
          bgcolor: "#fff",
          border: "1px solid rgba(15, 23, 42, 0.1)",
          borderRadius: "8px",
          boxShadow: "0 8px 30px rgba(15, 23, 42, 0.14), 0 1px 2px rgba(15, 23, 42, 0.06)",
        }}
      >
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, fontWeight: 600, color: "#0f172a", mb: "4px" }}>
          <span>
            <span style={{ color: look.colour }}>{look.sign}</span> {target.title}
          </span>
          <span style={{ color: look.colour, fontWeight: 500 }}>{target.status}</span>
        </Box>
        {target.status === "added" && <Box>{`Added in ${newer}`}</Box>}
        {target.status === "removed" && <Box>{`Removed in ${newer}`}</Box>}
        {target.status === "changed" && differences === null && <Box sx={{ color: "#64748b" }}>Reading…</Box>}
        {target.status === "changed" && !inside && differences?.length === 0 && <Box sx={{ color: "#64748b" }}>No property differs.</Box>}
        {differences?.map((difference) => <DifferenceRow key={difference.path.join(".")} difference={difference} />)}
        {inside && differences?.length === 0 && <Box data-testid="diff-inside">The action is the same; its parts changed.</Box>}
        {groups.map(([group, parts]) => (
          <Box key={group} data-testid="diff-part-group" sx={{ mt: "6px" }}>
            <Box sx={{ fontWeight: 600, color: "#475569" }}>{group}</Box>
            {parts.map((part) => (
              <Box key={`${part.kind}|${part.id}`} data-testid="diff-part">
                <span style={{ color: MARK_LOOK[part.status].colour }}>{MARK_LOOK[part.status].sign}</span> {part.label}
                {part.differences.map((difference) => <DifferenceRow key={difference.path.join(".")} difference={difference} />)}
              </Box>
            ))}
          </Box>
        ))}
      </Paper>
    </ClickAwayListener>
  );
}
