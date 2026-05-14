// src/components/navigation/LeftSidebar/SidebarRowIcon.tsx
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import SchemaOutlinedIcon from "@mui/icons-material/SchemaOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import type { ReactElement } from "react";
import type { NodeRow } from "@/model/sidebar";

/** MUI icon for one sidebar tree row by `NodeRow.type` — colocated with `LeftSidebar` only (§1). */
export function SidebarRowIcon({ row }: { row: NodeRow }): ReactElement {
  if (row.type === "graph") {
    return <AccountTreeOutlinedIcon fontSize="small" />;
  }
  if (row.type === "erd_all" || row.type === "erd_domain") {
    return <SchemaOutlinedIcon fontSize="small" />;
  }
  return <MenuBookOutlinedIcon fontSize="small" />;
}
