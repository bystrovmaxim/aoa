// src/components/diagrams/ElementCard/ElementCard.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Paper from "@mui/material/Paper";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { getActiveBase } from "@/api/client";
import { fetchElementCard, type ElementCardRead } from "@/api/elementCard";
import { DiffBody, StatusIcon } from "@/components/history/DiffCard";
import { cardFieldsOpen, rememberCardFieldsOpen } from "@/lib/cardFieldsOpen";
import { placeCard, type CardAround } from "@/lib/cardPlace";
import { MARK_LOOK, type CardTarget } from "@/lib/erdDiffCard";
import { isFollowing, reportPanels, useShownPanel, type CardPanel, type ElementRef } from "@/rooms/focusStore";
import { LifecycleMiniature } from "./LifecycleMiniature";

export type CardProjection = { toDiagram: (point: Point) => Point; toStage: (point: Point) => Point };

/** One row of a table's card. */
export type CardField = {
  name: string;
  type?: string;
  key?: "PK" | "FK";
  description?: string | null;
  /** What happened to it in Diff, when something did. */
  status?: keyof typeof MARK_LOOK;
  /** Its type in A, when it differs. */
  previousType?: string;
  /** The lifecycle it is, when it is one. */
  lifecycleId?: string | null;
};

/** What a card is about and what the diagram already knows of it. */
export type CardSubject = {
  key: string;
  ref: ElementRef;
  title: string;
  /** Its type or what it is, as the diagram holds it. */
  detail: string;
  /** A description the diagram already holds; else it is read. */
  description?: string | null;
  /** The node the server is asked about; a line's card asks nothing. */
  nodeId: string | null;
  /** What the comparison says of it, in Diff, when it changed. */
  change: CardTarget | null;
  /** The lifecycles it is or holds, each drawn small. */
  lifecycleIds?: readonly string[];
  fields?: readonly CardField[];
  /** A name to copy; a phone has no click on it. */
  copy?: string;
  at: { x: number; y: number };
  /** What it stands beside, to place it round: without it, it stays at ``at``, lifted to fit. */
  around?: CardAround;
  /** Between the stage and the diagram: a card's place is said on the diagram, so a follower sets it on the same spot. */
  project?: CardProjection;
};

export type ElementCardProps = {
  subject: CardSubject;
  /** The newer version's name: what an element was added or removed in. */
  newer: string;
  onEnter: () => void;
  onLeave: () => void;
  onClose: () => void;
};

const UNCHANGED_COLOUR = "#94a3b8";
/** The field under the pointer: its type and description stand below. */
const POINTED_COLOUR = "#1d4ed8";

/** A touch screen has no pointer to rest or click with. */
function onTouchScreen(): boolean {
  return globalThis.matchMedia?.("(pointer: coarse)").matches ?? false;
}

function CopyName({ name }: { name: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <ButtonBase
      data-testid="card-copy"
      onClick={() => void navigator.clipboard?.writeText(name).then(() => setCopied(true))}
      sx={{ mt: "6px", height: 26, px: 1, borderRadius: "6px", fontSize: 12, fontWeight: 600, color: "#0f172a", bgcolor: "rgba(15, 23, 42, 0.05)" }}
    >
      {copied ? "Copied" : "Copy name"}
    </ButtonBase>
  );
}

/** The longest a card stays unseen waiting for what it reads; then it shows what it has. */
const CARD_WAIT_MS = 500;
type Point = { x: number; y: number };

/** The narrowest drawn width that fills a card: a short lifecycle is not blown up past it. */
const MINIATURE_FULL_WIDTH = 420;
/** The gap a card keeps from the stage's edge. */
const CARD_EDGE_PX = 8;

/**
 * A table's fields by name, what a table is made of; the type and description of the one under the pointer or finger stand
 * at the card's foot, a changed type with what it was, so the list stays quiet and nothing above it moves (spec 043, FR-006).
 */
function FieldList({ fields, open, pointed, onOpen, onPoint }: { fields: readonly CardField[]; open: boolean; pointed: number | null; onOpen: () => void; onPoint: (row: number | null) => void }) {
  const rows = open ? fields.map((field, row) => ({ field, row })) : [];
  // Hidden, the list still says what changed in it: that is what a card from afar is for. Where every row changed, as in a
  // table that came or went whole, the card itself has said so.
  const counts = (["added", "removed", "changed"] as const).flatMap((status) => {
    const count = fields.filter((field) => field.status === status).length;
    return count > 0 && count < fields.length ? [{ status, count }] : [];
  });
  const shown = pointed === null ? undefined : fields[pointed];
  return (
    <Box sx={{ mt: "6px", borderTop: "1px solid rgba(15, 23, 42, 0.06)", pt: "4px" }}>
      <ButtonBase
        data-testid="card-fields-toggle"
        aria-expanded={open}
        onClick={onOpen}
        sx={{ display: "flex", alignItems: "center", gap: "4px", width: "100%", justifyContent: "flex-start", fontSize: 12, fontWeight: 600, color: "#475569", py: "1px" }}
      >
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden style={{ transform: open ? "rotate(180deg)" : "none" }}>
          <path d="M2 3.5 L5 6.5 L8 3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {fields.length} field{fields.length === 1 ? "" : "s"}
        {counts.map(({ status, count }) => (
          <span key={status} data-testid="card-fields-count" style={{ color: MARK_LOOK[status].colour }}>
            {MARK_LOOK[status].sign}
            {count}
          </span>
        ))}
      </ButtonBase>
      <Box data-testid="card-fields" onMouseLeave={() => onPoint(null)}>
        {rows.map(({ field, row }) => (
          <Box key={row} data-testid="card-field" onMouseEnter={() => onPoint(row)} onClick={() => onPoint(row)} sx={{ display: "grid", gridTemplateColumns: "20px minmax(0, 1fr)", gap: "6px" }}>
            <Box sx={{ color: "#94a3b8", fontSize: 10, fontWeight: 700, lineHeight: "17px" }}>{field.key}</Box>
            <Box data-testid="card-field-name" sx={{ overflowWrap: "anywhere", ...(pointed === row && { fontWeight: 600, color: POINTED_COLOUR }) }}>
              {field.status && <span style={{ color: MARK_LOOK[field.status].colour }}>{MARK_LOOK[field.status].sign} </span>}
              {field.name}
            </Box>
          </Box>
        ))}
      </Box>
      {rows.length > 0 && (
        <Box data-testid="card-field-hint" sx={{ mt: "4px", pt: "4px", borderTop: "1px solid rgba(15, 23, 42, 0.06)", color: "#64748b", wordBreak: "break-word" }}>
          {shown ? (
            <>
              <Box sx={{ color: "#0f172a" }}>
                {shown.previousType !== undefined && (
                  <>
                    <s>{shown.previousType}</s> →{" "}
                  </>
                )}
                {shown.type}
              </Box>
              <Box>{shown.description}</Box>
            </>
          ) : (
            <Box sx={{ color: UNCHANGED_COLOUR }}>{onTouchScreen() ? "Tap a field" : "Hover a field"}</Box>
          )}
        </Box>
      )}
    </Box>
  );
}

/**
 * The one card of Maxitor (spec 043, FR-001): what an element is, its description, what changed in it in Diff, a table's
 * fields and a lifecycle's picture. The diagram's own knowledge shows at once; a read that fails takes nothing away.
 */
export function ElementCard({ subject, newer, onEnter, onLeave, onClose }: ElementCardProps) {
  const [read, setRead] = useState<ElementCardRead | null>(null);
  const [failed, setFailed] = useState(false);
  const [answered, setAnswered] = useState(subject.nodeId === null);
  const [drawn, setDrawn] = useState<Readonly<Record<string, number>>>({});
  const [waited, setWaited] = useState(false);
  const [ownInside, setOwnInside] = useState<CardPanel>(() => ({ ref: subject.ref, fields: cardFieldsOpen(), field: null, scroll: 0, at: null }));
  // A follower sees inside the card too: the list, the field pointed at and the scroll (FR-010).
  const inside = useShownPanel<CardPanel>(ownInside, setOwnInside, (panels) => panels.card ?? ownInside, (value) => ({ card: value }));
  useEffect(() => () => reportPanels({ card: null }), []);
  const cardRef = useRef<HTMLDivElement>(null);
  const { nodeId, change, title, detail, fields, copy, at, around, project } = subject;
  // In a comparison every card wears a status: an unchanged element says so where a changed one says what happened.
  const unchanged = change === null && getActiveBase() !== null;
  const lifecycleIds = subject.lifecycleIds?.length ? subject.lifecycleIds : read?.lifecycle_id ? [read.lifecycle_id] : [];

  useEffect(() => {
    let live = true;
    setRead(null);
    setFailed(false);
    setAnswered(nodeId === null);
    if (nodeId)
      fetchElementCard(nodeId)
        .then(
          (answer) => live && setRead(answer),
          () => live && setFailed(true),
        )
        .finally(() => live && setAnswered(true));
    return () => {
      live = false;
    };
  }, [nodeId]);

  const fullWidth = Math.max(MINIATURE_FULL_WIDTH, ...Object.values(drawn));
  /** The lifecycle whose field is pointed at: its picture stays bright, the others dim. */
  const litLifecycle = (inside.field === null ? null : fields?.[inside.field]?.lifecycleId) ?? null;

  useEffect(() => {
    if (isFollowing() && cardRef.current) cardRef.current.scrollTop = inside.scroll;
  }, [inside.scroll]);

  // Unseen until what it reads has come, so it opens once, whole, where it will stay.
  useEffect(() => {
    const timer = setTimeout(() => setWaited(true), CARD_WAIT_MS);
    return () => clearTimeout(timer);
  }, []);
  const said = isFollowing() ? inside.at : null;
  const ready = waited || (answered && lifecycleIds.every((id) => id in drawn) && (!isFollowing() || said !== null));

  // Placed before the frame is painted, knowing its size; what grows later scrolls inside it.
  useLayoutEffect(() => {
    const card = cardRef.current;
    const stage = card?.offsetParent;
    if (!card || !stage || !ready) return;
    const size = { width: card.offsetWidth, height: card.offsetHeight };
    const onStage = (point: Point) => ({
      x: Math.max(CARD_EDGE_PX, Math.min(point.x, stage.clientWidth - size.width - CARD_EDGE_PX)),
      y: Math.max(CARD_EDGE_PX, Math.min(point.y, stage.clientHeight - size.height - CARD_EDGE_PX)),
    });
    const place = said && project ? onStage(project.toStage(said)) : around ? placeCard(stage.getBoundingClientRect(), size, around) : onStage(at);
    card.style.left = `${place.x}px`;
    card.style.top = `${place.y}px`;
    card.style.maxHeight = `${stage.clientHeight - place.y - CARD_EDGE_PX}px`;
    if (isFollowing() || !project) return;
    const onDiagram = project.toDiagram(place);
    const spot = { x: Math.round(onDiagram.x * 1000) / 1000, y: Math.round(onDiagram.y * 1000) / 1000 };
    setOwnInside((now) => (now.at?.x === spot.x && now.at?.y === spot.y ? now : { ...now, at: spot }));
  }, [around, at, project, ready, said, subject]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <Paper
      role="dialog"
      aria-label={`About ${title}`}
      elevation={0}
      data-testid="element-card"
      ref={cardRef}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onScroll={(event) => {
        const scroll = Math.round(event.currentTarget.scrollTop);
        setOwnInside((now) => (now.scroll === scroll ? now : { ...now, scroll }));
      }}
      sx={{
        position: "absolute",
        visibility: ready ? "visible" : "hidden",
        // A follower's card is the followed person's: their own pointer must not hold it open.
        pointerEvents: isFollowing() ? "none" : "auto",
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
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, fontWeight: 600, color: "#0f172a" }}>
        <span style={{ minWidth: 0, overflowWrap: "anywhere" }}>{title}</span>
        {change && <StatusIcon status={change.status} />}
        {unchanged && <StatusIcon status="unchanged" />}
      </Box>
      {detail && (
        <Box data-testid="card-detail" sx={{ color: "#64748b", whiteSpace: "pre-line", wordBreak: "break-word" }}>
          {detail}
        </Box>
      )}
      {(subject.description ?? read?.description) && (
        <Box data-testid="card-description" sx={{ mt: "4px", color: "#0f172a" }}>
          {subject.description ?? read?.description}
        </Box>
      )}
      {failed && (
        <Box data-testid="card-unread" sx={{ mt: "4px", color: "#64748b" }}>
          The rest could not be read.
        </Box>
      )}
      {change && <DiffBody target={change} newer={newer} />}
      {lifecycleIds.map((id) => (
        <LifecycleMiniature
          key={id}
          lifecycleId={id}
          fullWidth={fullWidth}
          dimmed={litLifecycle !== null && litLifecycle !== id}
          onSettled={(width) => setDrawn((known) => ({ ...known, [id]: width }))}
        />
      ))}
      {fields && (
        <FieldList
          fields={fields}
          open={inside.fields}
          pointed={inside.field}
          onOpen={() => {
            rememberCardFieldsOpen(!inside.fields);
            setOwnInside((now) => ({ ...now, fields: !now.fields }));
          }}
          onPoint={(row) => setOwnInside((now) => ({ ...now, field: row }))}
        />
      )}
      {copy && onTouchScreen() && <CopyName name={copy} />}
    </Paper>
  );
}
