// src/components/navigation/LeftSidebar/SidebarRowIcon.tsx
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import SchemaOutlinedIcon from "@mui/icons-material/SchemaOutlined";
import type { ReactElement } from "react";
import type { NodeRow } from "@/model/sidebar";

/** Slightly smaller than MUI ``small`` so row text stays visually dominant. */
const ICON_SX = { fontSize: 16, opacity: 0.88 } as const;

/** MUI icon for one sidebar tree row by `NodeRow.type` — colocated with `LeftSidebar` only (§1). */
export function SidebarRowIcon({ row }: { row: NodeRow }): ReactElement {
  if (row.type === "graph") {
    return <HubOutlinedIcon sx={ICON_SX} />;
  }
  if (row.type === "erd_all" || row.type === "erd_domain") {
    return <SchemaOutlinedIcon sx={ICON_SX} />;
  }
  return <MenuBookOutlinedIcon sx={ICON_SX} />;
}
