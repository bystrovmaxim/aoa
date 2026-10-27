// src/rooms/RoomBar/RoomBar.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import LinkIcon from "@mui/icons-material/Link";
import LogoutIcon from "@mui/icons-material/Logout";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import NearMeDisabledOutlinedIcon from "@mui/icons-material/NearMeDisabledOutlined";
import NearMeOutlinedIcon from "@mui/icons-material/NearMeOutlined";
import { useEffect, useRef, useState } from "react";
import { roomLink } from "@/lib/urlState";
import { SIDEBAR_SURFACE } from "@/lib/layoutConstants";
import { Circles } from "@/rooms/Circles";
import { InviteCard, copyRoomLink } from "@/rooms/InviteCard";
import { followerCount, youFirst } from "@/rooms/roomStore";
import { ROW_BUTTON_PRIMARY_SX, ROW_BUTTON_SX, WORKSPACE_SURFACE } from "@/rooms/roomStyles";
import type { RoomSession } from "@/rooms/useRoomSession";

export type RoomBarProps = {
  session: RoomSession;
  /** The page this tab shows, for the grey dot on circles of people elsewhere. */
  page: string | null;
  pageLabel: (page: string | null) => string;
  /** A room needs an open service. */
  canOpen: boolean;
  /** The phone layout: the controls sit in the existing 44 px bar. */
  compact: boolean;
  /** Go to a participant (FR-050). */
  onGoTo: (participant: string, page: string | null) => void;
  /** Follow a participant, or stop (FR-051, FR-053). */
  onFollow: (participant: string) => void;
  onStopFollowing: () => void;
};

/** The quiet line of state in the row: *Reconnecting…*, or the latest *Boris joined*. */
function StatusText({ session }: { session: RoomSession }) {
  const text =
    session.connection?.kind === "reconnecting"
      ? "Reconnecting…"
      : session.connection?.kind === "connecting"
        ? "Connecting…"
        : (session.room?.notices.at(-1)?.text ?? null);
  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{ fontSize: 12, color: "#64748b", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", minWidth: 0 }}
    >
      {text}
    </Box>
  );
}

/**
 * The room controls (spec 028, FR-019 … FR-028; mockup screens 1, 3, 5, 14). Outside a room: **Open
 * room**. Inside: the circles, **Copy link**, **Hide pointers** and **Leave room** on a desktop; on a
 * phone the circles and one ⋮ menu that says the same in words.
 */
export function RoomBar({ session, page, pageLabel, canOpen, compact, onGoTo, onFollow, onStopFollowing }: RoomBarProps) {
  const copyButton = useRef<HTMLButtonElement | null>(null);
  const [inviteAnchor, setInviteAnchor] = useState<HTMLElement | null>(null);
  const [inviteCopies, setInviteCopies] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const room = session.room;

  // A newly opened room greets its creator with the invite card.
  useEffect(() => {
    if (session.inviteOpen && copyButton.current) {
      setInviteCopies(false);
      setInviteAnchor(copyButton.current);
    }
    if (!session.inviteOpen) setInviteAnchor(null);
  }, [session.inviteOpen]);

  const link = room ? roomLink(window.location.href, room.roomId) : "";

  if (!room) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
        <StatusText session={session} />
        <Button
          sx={ROW_BUTTON_PRIMARY_SX}
          startIcon={<GroupsOutlinedIcon />}
          disabled={!canOpen || session.connection?.kind === "connecting"}
          onClick={session.requestOpen}
        >
          Open room
        </Button>
      </Box>
    );
  }

  const participants = youFirst(room);
  const circles = (
    <Circles
      participants={participants}
      youId={room.youId}
      yourPage={page}
      pageLabel={pageLabel}
      followers={(id) => followerCount(room, id)}
      onRename={session.requestRename}
      onGoTo={(participant) => onGoTo(participant.id, participant.page)}
      follows={room.follows}
      onFollow={onFollow}
      onStopFollowing={onStopFollowing}
      compact={compact}
      surface={compact ? SIDEBAR_SURFACE : WORKSPACE_SURFACE}
    />
  );

  if (compact) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: "2px", minWidth: 0 }}>
        {circles}
        <IconButton
          ref={copyButton}
          aria-label="Room"
          aria-haspopup="menu"
          onClick={(event) => setMenuAnchor(event.currentTarget)}
          sx={{ width: 32, height: 32, borderRadius: "8px", color: "rgb(100, 116, 139)", bgcolor: menuAnchor ? "rgba(15, 23, 42, 0.08)" : undefined }}
        >
          <MoreVertIcon sx={{ fontSize: 18 }} />
        </IconButton>
        <Menu anchorEl={menuAnchor} open={menuAnchor !== null} onClose={() => setMenuAnchor(null)}>
          <MenuItem
            onClick={() => {
              setMenuAnchor(null);
              void copyRoomLink(link);
            }}
          >
            <LinkIcon sx={{ fontSize: 16, mr: "10px", color: "rgb(100, 116, 139)" }} />
            Copy room link
          </MenuItem>
          <MenuItem
            onClick={() => {
              setMenuAnchor(null);
              session.toggleHidePointers();
            }}
          >
            {session.hidePointers ? (
              <NearMeOutlinedIcon sx={{ fontSize: 16, mr: "10px", color: "rgb(100, 116, 139)" }} />
            ) : (
              <NearMeDisabledOutlinedIcon sx={{ fontSize: 16, mr: "10px", color: "rgb(100, 116, 139)" }} />
            )}
            {session.hidePointers ? "Show pointers" : "Hide pointers"}
          </MenuItem>
          <MenuItem
            onClick={() => {
              setMenuAnchor(null);
              session.leave();
            }}
          >
            <LogoutIcon sx={{ fontSize: 16, mr: "10px", color: "rgb(100, 116, 139)" }} />
            Leave room
          </MenuItem>
        </Menu>
        <InviteCard anchor={inviteAnchor} link={link} copyOnOpen={false} onClose={session.closeInvite} />
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0 }}>
      <StatusText session={session} />
      {circles}
      <Box sx={{ width: "1px", height: 18, bgcolor: "rgba(15, 23, 42, 0.12)", mx: "2px", flexShrink: 0 }} />
      <Button
        ref={copyButton}
        sx={ROW_BUTTON_SX}
        startIcon={<LinkIcon />}
        onClick={(event) => {
          setInviteCopies(true);
          setInviteAnchor(event.currentTarget);
        }}
      >
        Copy link
      </Button>
      <Button
        sx={ROW_BUTTON_SX}
        startIcon={session.hidePointers ? <NearMeOutlinedIcon /> : <NearMeDisabledOutlinedIcon />}
        aria-pressed={session.hidePointers}
        onClick={session.toggleHidePointers}
      >
        {session.hidePointers ? "Show pointers" : "Hide pointers"}
      </Button>
      <Button sx={ROW_BUTTON_SX} startIcon={<LogoutIcon />} onClick={session.leave}>
        Leave room
      </Button>
      <InviteCard
        anchor={inviteAnchor}
        link={link}
        copyOnOpen={inviteCopies}
        onClose={() => {
          setInviteAnchor(null);
          session.closeInvite();
        }}
      />
    </Box>
  );
}
