// src/rooms/Circles/Circles.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Popover from "@mui/material/Popover";
import { useCallback, useEffect, useRef, useState } from "react";
import { Avatar, ringedBox } from "@/rooms/Circles/Avatar";
import { ParticipantCard, type FollowChoice } from "@/rooms/ParticipantCard";
import { followsYou, wouldCloseCircle } from "@/rooms/followCircle";
import type { FollowLinks, Participant } from "@/rooms/protocol";
import { CARD_PAPER_SX, HINT_SX, WORKSPACE_SURFACE } from "@/rooms/roomStyles";
import { setParticipantCardOpen } from "@/rooms/participantCardOpen";

export type CirclesProps = {
  /** You first, then the others in the order they joined. */
  participants: Participant[];
  youId: string;
  /** The page you are on, so circles of people elsewhere get a grey dot. */
  yourPage: string | null;
  pageLabel: (page: string | null) => string;
  /** The names of those who follow a participant directly; their number is the badge on your own circle. */
  followers: (id: string) => string[];
  onRename: () => void;
  /** Go to a participant: their page, centred on them, at your zoom (FR-050). */
  onGoTo: (participant: Participant) => void;
  /** Who follows whom in the room. */
  follows: FollowLinks;
  onFollow: (participant: string) => void;
  onStopFollowing: () => void;
  /** On a phone three circles fit, on a desktop five (FR-020). */
  compact: boolean;
  surface?: string;
};

const HOVER_OPEN_MS = 350;
const HOVER_CLOSE_MS = 200;
const LONG_PRESS_MS = 500;

/** How many circles show before the rest collapse into +N. */
export function visibleCount(total: number, compact: boolean): number {
  const limit = compact ? 3 : 5;
  return total > limit ? limit - 1 : total;
}

/**
 * A circle per participant, yours first and ringed; beyond the limit the rest collapse into **+N**,
 * which opens the list. A click on someone's circle goes to them; hover, Enter and a long press open
 * the card. Each circle is a button labelled with the full name and page, so it is reached with Tab
 * and opened with Enter (FR-020 … FR-022, FR-028, FR-050).
 */
export function Circles({
  participants,
  youId,
  yourPage,
  pageLabel,
  followers,
  onRename,
  onGoTo,
  follows,
  onFollow,
  onStopFollowing,
  compact,
  surface = WORKSPACE_SURFACE,
}: CirclesProps) {
  const nameOf = (id: string) => participants.find((p) => p.id === id)?.name ?? id;
  /** What **Follow** can do for ``id``: the circle rule as the server applies it (FR-054). */
  const followChoice = (id: string): FollowChoice => {
    if (follows[youId] === id) return { kind: "following" };
    if (wouldCloseCircle(follows, youId, id)) {
      const how = followsYou(follows, youId, id);
      return { kind: "circle", through: how && how !== "direct" ? nameOf(how) : null };
    }
    return follows[youId] ? { kind: "instead" } : { kind: "follow" };
  };
  const followsYouOf = (id: string) => {
    const how = followsYou(follows, youId, id);
    return how === null ? null : { through: how === "direct" ? null : nameOf(how) };
  };
  // A card opened by a click, Enter or a long press stays; one opened by hover goes with the pointer.
  const [card, setCard] = useState<{ id: string; anchor: HTMLElement; pinned: boolean } | null>(null);
  const [moreAnchor, setMoreAnchor] = useState<HTMLElement | null>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearHover = () => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    hoverTimer.current = null;
  };
  const closeCard = useCallback(() => {
    clearHover();
    setCard(null);
  }, []);

  // The follow pill steps aside while a card or the list is open.
  const anyCardOpen = card !== null || moreAnchor !== null;
  useEffect(() => {
    setParticipantCardOpen(anyCardOpen);
    return () => setParticipantCardOpen(false);
  }, [anyCardOpen]);

  const shown = visibleCount(participants.length, compact);
  const rest = participants.slice(shown);
  /** Every circle of the row is 22 px in a box that holds its ring (spec 029, FR-050, FR-051). */
  const size = 22;
  const box = ringedBox(size);
  const cardParticipant = card ? participants.find((p) => p.id === card.id) : undefined;

  function circle(participant: Participant) {
    const label = `${participant.name}${participant.id === youId ? " (you)" : ""} — ${pageLabel(participant.page)}`;
    const count = participant.id === youId ? followers(youId).length : 0;
    return (
      <ButtonBase
        key={participant.id}
        aria-label={label}
        aria-haspopup="dialog"
        onClick={(event) => {
          // A pointer click goes to them; Enter (a click with no pointer, detail 0) opens the card.
          if (event.detail > 0 && participant.id !== youId) {
            closeCard();
            onGoTo(participant);
          } else setCard({ id: participant.id, anchor: event.currentTarget, pinned: true });
        }}
        onMouseEnter={(event) => {
          const anchor = event.currentTarget;
          clearHover();
          hoverTimer.current = setTimeout(() => setCard((open) => open ?? { id: participant.id, anchor, pinned: false }), HOVER_OPEN_MS);
        }}
        onMouseLeave={() => {
          clearHover();
          hoverTimer.current = setTimeout(() => setCard((open) => (open?.pinned ? open : null)), HOVER_CLOSE_MS);
        }}
        onPointerDown={(event) => {
          if (event.pointerType !== "touch") return;
          const anchor = event.currentTarget;
          pressTimer.current = setTimeout(() => setCard({ id: participant.id, anchor, pinned: true }), LONG_PRESS_MS);
        }}
        onPointerUp={() => pressTimer.current && clearTimeout(pressTimer.current)}
        sx={{
          width: box,
          height: box,
          borderRadius: "50%",
          position: "relative",
          flexShrink: 0,
          // The focus ring is drawn inside the box, over the ring's place, never outside it.
          "&:focus-visible": { outline: "2px solid #0f172a", outlineOffset: -2 },
        }}
      >
        <Avatar
          participant={participant}
          size={size}
          ringed={participant.id === youId}
          boxed
          surface={surface}
          pale={!participant.visible || participant.away}
          elsewhere={participant.id !== youId && participant.page !== null && participant.page !== yourPage}
        />
        {count > 0 && (
          <Box
            component="span"
            aria-label={`${count} following you`}
            sx={{
              position: "absolute",
              // Kept within the circle's box sideways, so it never reaches the neighbour.
              top: -4,
              right: 0,
              minWidth: 14,
              height: 14,
              px: "3px",
              borderRadius: "8px",
              bgcolor: "#0f172a",
              color: "#fff",
              fontSize: 9.5,
              fontWeight: 700,
              lineHeight: "14px",
              textAlign: "center",
              border: `1.5px solid ${surface}`,
            }}
          >
            {count}
          </Box>
        )}
      </ButtonBase>
    );
  }

  return (
    <Box component="span" sx={{ display: "flex", alignItems: "center", gap: "4px" }} role="group" aria-label="People in this room">
      {participants.slice(0, shown).map(circle)}
      {rest.length > 0 && (
        <ButtonBase
          aria-label={`${rest.length} more in this room`}
          aria-haspopup="dialog"
          onClick={(event) => setMoreAnchor(event.currentTarget)}
          sx={{
            width: box,
            height: box,
            borderRadius: "50%",
            flexShrink: 0,
            "&:focus-visible": { outline: "2px solid #0f172a", outlineOffset: -2 },
          }}
        >
          <Box
            component="span"
            sx={{ width: size, height: size, borderRadius: "50%", display: "inline-flex", alignItems: "center", justifyContent: "center", bgcolor: "#e2e8f0", color: "#334155", fontSize: 10, fontWeight: 600 }}
          >
            +{rest.length}
          </Box>
        </ButtonBase>
      )}
      <Popover
        open={moreAnchor !== null}
        anchorEl={moreAnchor}
        onClose={() => setMoreAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{ paper: { sx: { ...CARD_PAPER_SX, width: 280, p: "8px", mt: "6px" } } }}
      >
        <Box sx={{ ...HINT_SX, p: "2px 4px 6px" }}>{rest.length} more in this room</Box>
        {rest.map((participant) => (
          <ButtonBase
            key={participant.id}
            aria-label={`${participant.name} — ${pageLabel(participant.page)}`}
            onClick={(event) => {
              const anchor = moreAnchor ?? event.currentTarget;
              setMoreAnchor(null);
              setCard({ id: participant.id, anchor, pinned: true });
            }}
            sx={{ display: "flex", width: "100%", alignItems: "center", gap: "9px", p: "6px 4px", borderRadius: "6px", justifyContent: "flex-start", "&:hover": { bgcolor: "rgba(15, 23, 42, 0.05)" } }}
          >
            <Avatar participant={participant} size={20} surface="#fff" pale={!participant.visible || participant.away} />
            <Box component="span" sx={{ fontSize: 12.5, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {participant.name}
            </Box>
            <Box component="span" sx={{ ml: "auto", fontSize: 11.5, color: "rgb(100, 116, 139)", whiteSpace: "nowrap" }}>
              {pageLabel(participant.page)}
            </Box>
          </ButtonBase>
        ))}
      </Popover>
      {card && cardParticipant && (
        <ParticipantCard
          participant={cardParticipant}
          anchor={card.anchor}
          pageLabel={pageLabel(cardParticipant.page)}
          isYou={cardParticipant.id === youId}
          followers={followers(cardParticipant.id)}
          onClose={closeCard}
          onRename={onRename}
          onGoTo={() => onGoTo(cardParticipant)}
          followChoice={followChoice(cardParticipant.id)}
          followsYou={followsYouOf(cardParticipant.id)}
          onFollow={() => onFollow(cardParticipant.id)}
          onStopFollowing={onStopFollowing}
          onHover={(inside) => {
            clearHover();
            if (!inside) hoverTimer.current = setTimeout(() => setCard((open) => (open?.pinned ? open : null)), HOVER_CLOSE_MS);
          }}
        />
      )}
    </Box>
  );
}
