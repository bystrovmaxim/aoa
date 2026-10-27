// src/rooms/PointerLayer/PointerLayer.tsx
import Box from "@mui/material/Box";
import { useEffect, useReducer } from "react";
import { createPortal } from "react-dom";
import { Avatar } from "@/rooms/Circles/Avatar";
import type { DiagramSurface } from "@/rooms/diagramSurface";
import { inkOn } from "@/rooms/initials";
import { currentPointers, subscribePointers, type RemotePointer } from "@/rooms/pointerStore";
import type { Participant } from "@/rooms/protocol";

export type PointerLayerProps = {
  surface: DiagramSurface;
  /** The participants whose pointers may be drawn: others on this page, connected. */
  participants: Participant[];
};

/** A touch shows as a ring for about this long (FR-041). */
export const TOUCH_MS = 1_000;
/** Distance of an edge arrow from the viewer's edge, in pixels. */
const EDGE_INSET = 20;

type Placed =
  | { kind: "inside"; x: number; y: number }
  | { kind: "edge"; x: number; y: number; angle: number };

/** Where a pointer at client ``(cx, cy)`` goes in a ``w`` × ``h`` viewer: on it, or as an arrow at its edge. */
export function place(cx: number, cy: number, w: number, h: number): Placed {
  if (cx >= 0 && cy >= 0 && cx <= w && cy <= h) return { kind: "inside", x: cx, y: cy };
  const mx = w / 2;
  const my = h / 2;
  const dx = cx - mx;
  const dy = cy - my;
  const s = Math.min((mx - EDGE_INSET) / Math.abs(dx || 1e-6), (my - EDGE_INSET) / Math.abs(dy || 1e-6));
  return { kind: "edge", x: mx + dx * s, y: my + dy * s, angle: (Math.atan2(dy, dx) * 180) / Math.PI };
}

/**
 * Whether a pointer is still shown at ``now``: a mouse pointer always — it shows for as long as its
 * person is in the room and on this page (spec 029, FR-020) — and a tap for a moment.
 */
export function pointerVisible(pointer: RemotePointer, now: number): boolean {
  return pointer.kind === "mouse" || now - pointer.at < TOUCH_MS;
}

function Arrow({ colour }: { colour: string }) {
  return (
    <svg width="18" height="22" viewBox="0 0 18 22" style={{ display: "block", filter: "drop-shadow(0 1px 1px rgba(0,0,0,.25))" }}>
      <path d="M2 2v16l4.4-4.1 3 6.6 2.9-1.3-3-6.5H16z" fill={colour} stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

function NameTag({ participant, left, top }: { participant: Participant; left: number; top: number }) {
  return (
    <Box
      component="span"
      sx={{
        position: "absolute",
        left,
        top,
        px: "7px",
        py: "2px",
        borderRadius: "9px",
        fontSize: 11,
        fontWeight: 600,
        whiteSpace: "nowrap",
        boxShadow: "0 1px 2px rgba(0,0,0,.15)",
        bgcolor: participant.colour,
        color: inkOn(participant.colour),
      }}
    >
      {participant.name}
    </Box>
  );
}

/**
 * Everyone else's pointer, drawn over the diagram at the diagram point it is on, re-projected on every
 * pan and zoom (FR-040 … FR-044; mockup screens 6 and 8). A pointer outside the view is an arrow at
 * the edge with the person's initials; a click on it centres the view there at the same zoom.
 */
export function PointerLayer({ surface, participants }: PointerLayerProps) {
  const [, redraw] = useReducer((n: number) => n + 1, 0);

  useEffect(() => {
    let frame: number | null = null;
    const schedule = () => {
      if (frame === null) frame = requestAnimationFrame(() => {
        frame = null;
        redraw();
      });
    };
    const unsubscribePointers = subscribePointers(schedule);
    const unsubscribeSurface = surface.subscribe(schedule);
    // A tap's ring fades by time.
    const tick = setInterval(schedule, 500);
    return () => {
      unsubscribePointers();
      unsubscribeSurface();
      clearInterval(tick);
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [surface]);

  const rect = surface.element.getBoundingClientRect();
  const now = Date.now();
  const pointers = currentPointers();
  const drawn = participants.flatMap((participant) => {
    const pointer = pointers.get(participant.id);
    if (!pointer || !pointerVisible(pointer, now)) return [];
    const client = surface.toClient(pointer);
    if (!client) return [];
    return [{ participant, pointer, at: place(client.x - rect.left, client.y - rect.top, rect.width, rect.height) }];
  });

  return createPortal(
    <Box aria-hidden sx={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 50, overflow: "hidden" }}>
      {drawn.map(({ participant, pointer, at }) => {
        if (at.kind === "edge") {
          return (
            <Box
              key={participant.id}
              data-participant={participant.id}
              title={`${participant.name} — show`}
              onClick={() => surface.centreOn(pointer)}
              sx={{ position: "absolute", left: at.x, top: at.y, width: 30, height: 30, ml: "-15px", mt: "-15px", pointerEvents: "auto", cursor: "pointer" }}
            >
              <Box
                component="span"
                sx={{
                  position: "absolute",
                  left: "50%",
                  top: "50%",
                  width: 0,
                  height: 0,
                  transformOrigin: "0 0",
                  transform: `rotate(${at.angle}deg)`,
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    left: 14,
                    top: -6,
                    borderLeft: `8px solid ${participant.colour}`,
                    borderTop: "6px solid transparent",
                    borderBottom: "6px solid transparent",
                  },
                }}
              />
              <Box component="span" sx={{ position: "absolute", left: 2, top: 2, borderRadius: "50%", boxShadow: "0 1px 4px rgba(0,0,0,.25)" }}>
                <Avatar participant={participant} size={26} surface="transparent" />
              </Box>
            </Box>
          );
        }
        if (pointer.kind === "touch") {
          return (
            <Box
              key={participant.id}
              data-participant={participant.id}
              sx={{
                position: "absolute",
                left: at.x,
                top: at.y,
                width: 34,
                height: 34,
                ml: "-17px",
                mt: "-17px",
                borderRadius: "50%",
                border: `3px solid ${participant.colour}`,
                bgcolor: `${participant.colour}2e`,
              }}
            >
              <NameTag participant={participant} left={30} top={22} />
            </Box>
          );
        }
        return (
          <Box key={participant.id} data-participant={participant.id} sx={{ position: "absolute", left: at.x - 2, top: at.y - 2 }}>
            <Arrow colour={participant.colour} />
            <NameTag participant={participant} left={14} top={16} />
          </Box>
        );
      })}
    </Box>,
    surface.element,
  );
}
