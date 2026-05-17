// src/components/navigation/LeftSidebar/LeftSidebar.tsx
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import type { ListItemTextProps } from "@mui/material/ListItemText";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useEffect, useMemo, useState } from "react";
import type { DiagramSelection } from "@/model/diagramSelection";
import { prefetchInterchangeG6 } from "@/lib/prefetch/g6Prefetch";
import { prefetchErdGraphviz } from "@/lib/prefetch/erdGraphviz";
import { buildSidebarGroupedMaps, diagramSelectionForRow, sortNodes } from "@/lib/sidebarNavigation";
import { SIDEBAR_SURFACE } from "@/lib/layoutConstants";
import { useSidebarCollapse } from "@/components/layout/MainLayout/SidebarCollapseContext";
import { useSidebarPayload } from "./hooks/useSidebarPayload";
import { SidebarRowIcon } from "./SidebarRowIcon";
import { SidebarToggleIcon } from "./SidebarToggleIcon";

/** One readable palette for the whole sidebar (on ``SIDEBAR_SURFACE`` drawer). */
const SB = {
  text: "rgb(30, 41, 59)",
  textSecondary: "rgb(71, 85, 105)",
  icon: "rgb(100, 116, 139)",
  chevron: "rgb(100, 116, 139)",
  hover: "rgba(15, 23, 42, 0.07)",
  selected: "rgba(15, 23, 42, 0.09)",
} as const;

const ellipsisText = {
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
} as const;

const rowTypography = {
  variant: "body2" as const,
  sx: { fontSize: 13, lineHeight: 1.35, fontWeight: 400, color: SB.text, ...ellipsisText },
};

const tooltipSlotProps = {
  tooltip: {
    sx: {
      maxWidth: 640,
      whiteSpace: "normal",
      wordBreak: "break-word",
    },
  },
} as const;

function TruncatingListLabel({
  tooltipTitle,
  primary,
  primaryTypographyProps,
  disableTooltip = false,
}: {
  tooltipTitle: string;
  primary: string;
  primaryTypographyProps?: ListItemTextProps["primaryTypographyProps"];
  /** When true, render text only (parent may wrap the row in ``Tooltip`` — e.g. disabled ``ListItemButton``). */
  disableTooltip?: boolean;
}) {
  const inner = (
    <Box sx={{ flex: "1 1 auto", minWidth: 0, overflow: "hidden" }}>
      <ListItemText
        sx={{ m: 0 }}
        primary={primary}
        primaryTypographyProps={{
          noWrap: true,
          ...primaryTypographyProps,
          sx: {
            ...primaryTypographyProps?.sx,
            ...ellipsisText,
          },
        }}
      />
    </Box>
  );
  if (disableTooltip) {
    return inner;
  }
  return (
    <Tooltip title={tooltipTitle} placement="right" enterDelay={400} slotProps={tooltipSlotProps}>
      {inner}
    </Tooltip>
  );
}

type LeftSidebarProps = {
  diagram: DiagramSelection | null;
  onSelectDiagram: (sel: DiagramSelection) => void;
};

function selectionKey(sel: DiagramSelection): string {
  if (sel.kind === "interchange_graph") return "interchange_graph";
  if (sel.kind === "lifecycle_fsm") return `lifecycle_fsm:${sel.lifecycle_graph_node_id}`;
  return `erd:${sel.qualifier ?? "all"}`;
}

function prefetchDiagramModule(sel: DiagramSelection | null): void {
  if (sel?.kind === "erd") prefetchErdGraphviz();
  if (sel?.kind === "interchange_graph") prefetchInterchangeG6();
}

/** Avoid redundant long entity-domain diagram label when it mirrors the domain name. */
function erdRowLabelForDomainGroup(domainLabel: string, rowLabel: string): string {
  const d = domainLabel.trim();
  const r = rowLabel.trim();
  if (r === `Entity domain — ${d} view` || r === `Entity domain - ${d} view`) return "Entity domain view";
  return rowLabel;
}

export function LeftSidebar({ diagram, onSelectDiagram }: LeftSidebarProps) {
  const { collapsed, toggleCollapsed } = useSidebarCollapse();
  const { sidebar, error } = useSidebarPayload();
  const group = useMemo(() => (sidebar ? buildSidebarGroupedMaps(sidebar) : null), [sidebar]);
  /** Root ids (e.g. `domains_root`) and graph node ids (e.g. domain rows) share one expand map — ids do not collide. */
  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!diagram) return;
    setExpandedById((prev) => {
      const next = { ...prev };
      if (diagram.kind === "interchange_graph") {
        next.applications_root = true;
      }
      if (diagram.kind === "erd") {
        next.domains_root = true;
        if (diagram.qualifier) {
          next[diagram.qualifier] = true;
        }
      }
      if (diagram.kind === "lifecycle_fsm") {
        next.entities_root = true;
        next[diagram.host_entity_interchange_id] = true;
      }
      return next;
    });
  }, [diagram]);

  return (
    <Box
      sx={{
        flex: "1 1 0%",
        minHeight: 0,
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Box
        component="header"
        sx={{
          flexShrink: 0,
          flexGrow: 0,
          overflow: "visible",
          pt: 0.5,
          pb: 0.25,
          px: 1,
          bgcolor: SIDEBAR_SURFACE,
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "flex-start",
        }}
      >
        <IconButton
          type="button"
          onClick={toggleCollapsed}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          disableRipple
          disableFocusRipple
          sx={{
            m: 0,
            p: 0,
            width: 32,
            minWidth: 32,
            height: 32,
            position: "relative",
            boxSizing: "border-box",
            overflow: "visible",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            color: SB.icon,
            borderRadius: 1.5,
            "&:hover": { bgcolor: SB.hover },
          }}
        >
          <SidebarToggleIcon
            sx={{
              fontSize: 17.6,
              position: "absolute",
              left: "50%",
              top: "50%",
              transform: "translate(-50%, -50%)",
            }}
          />
        </IconButton>
      </Box>

      <Box
        component="nav"
        aria-label="Diagram tree"
        sx={{
          flex: "1 1 0%",
          minHeight: 0,
          minWidth: 0,
          overflowY: "auto",
          overflowX: "hidden",
          WebkitOverflowScrolling: "touch",
          px: 1,
          pt: 0.5,
          pb: 1,
          bgcolor: SIDEBAR_SURFACE,
          ...(collapsed ? { display: "none" } : {}),
        }}
      >
        {error && (
          <Typography variant="body2" color="error" sx={{ display: "block", px: 0.5, py: 0.5, fontSize: 13 }}>
            Failed to load sidebar: {error}
          </Typography>
        )}
        {!sidebar && !error && (
          <Typography variant="body2" sx={{ display: "block", px: 0.5, py: 0.5, fontSize: 13, color: SB.textSecondary }}>
            Loading…
          </Typography>
        )}
        {/* Level-1: preserve API order (_ROOT_SECTIONS on the server). */}
        {sidebar &&
          group &&
          sidebar.level1_nodes.map((root) => {
            const open = Boolean(expandedById[root.id]);
            const directDiagrams = sortNodes(group.diagramsByParent.get(root.id) ?? []);
            const childNodes = sortNodes(group.l2ByParent.get(root.id) ?? []);
            return (
              <Box key={root.id} sx={{ mb: 0.5, minWidth: 0 }}>
                <ListItemButton
                  dense
                  onClick={() =>
                    setExpandedById((prev) => ({
                      ...prev,
                      [root.id]: !prev[root.id],
                    }))
                  }
                  aria-expanded={open}
                  sx={{
                    borderRadius: 1.5,
                    py: 0.45,
                    minHeight: 36,
                    minWidth: 0,
                    color: SB.text,
                    "&:hover": { bgcolor: SB.hover },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 32, color: SB.chevron }}>
                    {open ? <ExpandMoreIcon sx={{ fontSize: 20 }} /> : <ChevronRightIcon sx={{ fontSize: 20 }} />}
                  </ListItemIcon>
                  <TruncatingListLabel
                    tooltipTitle={root.label}
                    primary={root.label}
                    primaryTypographyProps={{
                      variant: "body2",
                      sx: { fontWeight: 600, fontSize: 13, letterSpacing: "-0.01em", color: SB.text },
                    }}
                  />
                </ListItemButton>
                {open ? (
                  <List dense disablePadding sx={{ pt: 0.25, pb: 0.25 }}>
                    {directDiagrams.map((node) => {
                      const sel = diagramSelectionForRow(node);
                      return (
                        <Tooltip
                          key={node.id}
                          title={node.label}
                          placement="right"
                          enterDelay={400}
                          slotProps={tooltipSlotProps}
                        >
                          <Box component="span" sx={{ display: "block", width: "100%", minWidth: 0 }}>
                            <ListItemButton
                              disabled={!sel}
                              selected={sel !== null && diagram !== null && selectionKey(diagram) === selectionKey(sel)}
                              onMouseEnter={() => prefetchDiagramModule(sel)}
                              onClick={() => sel && onSelectDiagram(sel)}
                              sx={{
                                borderRadius: 1.5,
                                pl: 4,
                                py: 0.35,
                                minHeight: 32,
                                minWidth: 0,
                                width: "100%",
                                color: SB.text,
                                "& .MuiListItemText-primary": { fontWeight: 400 },
                                "&.Mui-selected": {
                                  bgcolor: SB.selected,
                                  "&:hover": { bgcolor: SB.selected },
                                  "& .MuiListItemText-primary": { fontWeight: 400 },
                                },
                                "&:hover": { bgcolor: SB.hover },
                              }}
                            >
                              <ListItemIcon sx={{ minWidth: 32, color: SB.icon }}>
                                <SidebarRowIcon row={node} />
                              </ListItemIcon>
                              <TruncatingListLabel
                                disableTooltip
                                tooltipTitle={node.label}
                                primary={node.label}
                                primaryTypographyProps={rowTypography}
                              />
                            </ListItemButton>
                          </Box>
                        </Tooltip>
                      );
                    })}
                    {childNodes.map((cnode) => {
                      const erdRows = sortNodes(group.l3ByParent.get(cnode.id) ?? []);
                      const hasChildren = erdRows.length > 0;
                      const childOpen = Boolean(expandedById[cnode.id]);
                      return (
                        <Box key={cnode.id}>
                          {hasChildren ? (
                            <>
                              <ListItemButton
                                dense
                                onClick={() =>
                                  setExpandedById((prev) => ({
                                    ...prev,
                                    [cnode.id]: !prev[cnode.id],
                                  }))
                                }
                                aria-expanded={childOpen}
                                sx={{
                                  borderRadius: 1.5,
                                  pl: 4,
                                  py: 0.35,
                                  minHeight: 32,
                                  minWidth: 0,
                                  color: SB.textSecondary,
                                  "& .MuiListItemText-primary": { fontWeight: 400 },
                                  "&:hover": { bgcolor: SB.hover },
                                }}
                              >
                                <ListItemIcon sx={{ minWidth: 32, color: SB.chevron }}>
                                  {childOpen ? (
                                    <ExpandMoreIcon sx={{ fontSize: 20 }} />
                                  ) : (
                                    <ChevronRightIcon sx={{ fontSize: 20 }} />
                                  )}
                                </ListItemIcon>
                                <TruncatingListLabel
                                  tooltipTitle={cnode.label}
                                  primary={cnode.label}
                                  primaryTypographyProps={{
                                    variant: "body2",
                                    sx: {
                                      fontWeight: 400,
                                      fontSize: 13,
                                      letterSpacing: "-0.01em",
                                      color: SB.textSecondary,
                                    },
                                  }}
                                />
                              </ListItemButton>
                              {childOpen ? (
                                <List
                                  dense
                                  disablePadding
                                  sx={{
                                    pl: 0,
                                    ml: 0,
                                    pb: 0.25,
                                  }}
                                >
                                  {erdRows.map((e) => {
                                    const sel = diagramSelectionForRow(e);
                                    const primary = erdRowLabelForDomainGroup(cnode.label, e.label);
                                    return (
                                      <Tooltip
                                        key={`${e.type}:${e.id}`}
                                        title={e.label}
                                        placement="right"
                                        enterDelay={400}
                                        slotProps={tooltipSlotProps}
                                      >
                                        <Box component="span" sx={{ display: "block", width: "100%", minWidth: 0 }}>
                                          <ListItemButton
                                            disabled={!sel}
                                            selected={
                                              sel !== null &&
                                              diagram !== null &&
                                              selectionKey(diagram) === selectionKey(sel)
                                            }
                                            onMouseEnter={() => prefetchDiagramModule(sel)}
                                            onClick={() => sel && onSelectDiagram(sel)}
                                            sx={{
                                              borderRadius: 1.5,
                                              pl: 6,
                                              py: 0.3,
                                              minHeight: 32,
                                              minWidth: 0,
                                              width: "100%",
                                              color: SB.text,
                                              "& .MuiListItemText-primary": { fontWeight: 400 },
                                              "&.Mui-selected": {
                                                bgcolor: SB.selected,
                                                "&:hover": { bgcolor: SB.selected },
                                                "& .MuiListItemText-primary": { fontWeight: 400 },
                                              },
                                              "&:hover": { bgcolor: SB.hover },
                                            }}
                                          >
                                            <ListItemIcon sx={{ minWidth: 32, color: SB.icon }}>
                                              <SidebarRowIcon row={e} />
                                            </ListItemIcon>
                                            <TruncatingListLabel
                                              disableTooltip
                                              tooltipTitle={e.label}
                                              primary={primary}
                                              primaryTypographyProps={rowTypography}
                                            />
                                          </ListItemButton>
                                        </Box>
                                      </Tooltip>
                                    );
                                  })}
                                </List>
                              ) : null}
                            </>
                          ) : (
                            <Box
                              sx={{
                                pl: 4,
                                py: 0.35,
                                minHeight: 32,
                                display: "flex",
                                alignItems: "center",
                                minWidth: 0,
                                pr: 0.5,
                              }}
                            >
                              <Tooltip title={cnode.label} placement="right" enterDelay={400} slotProps={tooltipSlotProps}>
                                <Typography
                                  component="div"
                                  variant="body2"
                                  noWrap
                                  sx={{
                                    fontSize: 13,
                                    fontWeight: 400,
                                    color: SB.textSecondary,
                                    lineHeight: 1.35,
                                    letterSpacing: "-0.01em",
                                    pl: 3.5,
                                    flex: "1 1 auto",
                                    minWidth: 0,
                                    ...ellipsisText,
                                  }}
                                >
                                  {cnode.label}
                                </Typography>
                              </Tooltip>
                            </Box>
                          )}
                        </Box>
                      );
                    })}
                  </List>
                ) : null}
              </Box>
            );
          })}
      </Box>

      <Box
        component="footer"
        sx={{
          flexShrink: 0,
          flexGrow: 0,
          overflow: "hidden",
          px: 1.25,
          py: 1,
          bgcolor: SIDEBAR_SURFACE,
          display: collapsed ? "none" : "block",
        }}
      />
    </Box>
  );
}
