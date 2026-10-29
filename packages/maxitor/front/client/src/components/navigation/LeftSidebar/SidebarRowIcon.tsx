// src/components/navigation/LeftSidebar/SidebarRowIcon.tsx
import DeviceHubOutlinedIcon from "@mui/icons-material/DeviceHubOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import SchemaOutlinedIcon from "@mui/icons-material/SchemaOutlined";
import TableChartOutlinedIcon from "@mui/icons-material/TableChartOutlined";
import type { ReactElement } from "react";
import type { NodeRow } from "@/model/sidebar";

/** Slightly smaller than MUI ``small`` so row text stays visually dominant. */
const ICON_SX = { fontSize: 16, opacity: 0.88 } as const;

/** MUI icon for one sidebar tree row by `NodeRow.type` — colocated with `LeftSidebar` only. */
export function SidebarRowIcon({ row }: { row: NodeRow }): ReactElement {
  if (row.type === "graph") {
    return <HubOutlinedIcon sx={ICON_SX} />;
  }
  if (row.type === "erd_all" || row.type === "erd_domain" || row.type === "entity_class_diagram") {
    return <TableChartOutlinedIcon sx={ICON_SX} />;
  }
  if (row.type === "use_case_domain") {
    /** MUI Outlined — same stroke weight as ``TableChartOutlined``; hub = actors / use cases + links. */
    return <DeviceHubOutlinedIcon sx={ICON_SX} />;
  }
  if (row.type === "lifecycle_state_diagram") {
    return <SchemaOutlinedIcon sx={ICON_SX} />;
  }
  return <MenuBookOutlinedIcon sx={ICON_SX} />;
}
