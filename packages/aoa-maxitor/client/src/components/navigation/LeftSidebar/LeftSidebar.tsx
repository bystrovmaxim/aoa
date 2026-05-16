// src/components/navigation/LeftSidebar/LeftSidebar.tsx
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { useEffect, useMemo, useState } from "react";
import type { DiagramSelection } from "@/model/diagramSelection";
import { prefetchInterchangeG6 } from "@/lib/prefetch/g6Prefetch";
import { prefetchErdGraphviz } from "@/lib/prefetch/erdGraphviz";
import { buildSidebarGroupedMaps, diagramSelectionForRow, sortNodes } from "@/lib/sidebarNavigation";
import { useSidebarPayload } from "./hooks/useSidebarPayload";
import { SidebarRowIcon } from "./SidebarRowIcon";

/** One readable palette for the whole sidebar (on ~#EBF2F5 drawer). */
const SB = {
  text: "rgb(30, 41, 59)",
  textSecondary: "rgb(71, 85, 105)",
  icon: "rgb(100, 116, 139)",
  chevron: "rgb(100, 116, 139)",
  hover: "rgba(255, 255, 255, 0.55)",
  selected: "rgba(255, 255, 255, 0.88)",
} as const;

const rowTypography = {
  variant: "body2" as const,
  sx: { fontSize: 13, lineHeight: 1.35, fontWeight: 400, color: SB.text },
};

type LeftSidebarProps = {
  diagram: DiagramSelection | null;
  onSelectDiagram: (sel: DiagramSelection) => void;
};

function selectionKey(sel: DiagramSelection): string {
  if (sel.kind === "interchange_graph") return "interchange_graph";
  return `erd:${sel.qualifier ?? "all"}`;
}

function prefetchDiagramModule(sel: DiagramSelection | null): void {
  if (sel?.kind === "erd") prefetchErdGraphviz();
  if (sel?.kind === "interchange_graph") prefetchInterchangeG6();
}

/** Avoid "DOMAIN Foo" + "ERD — Foo": under a domain heading, show a short ERD label when redundant. */
function erdRowLabelForDomainGroup(domainLabel: string, rowLabel: string): string {
  const d = domainLabel.trim();
  const r = rowLabel.trim();
  if (r === `ERD — ${d}` || r === `ERD - ${d}`) return "ERD";
  return rowLabel;
}

export function LeftSidebar({ diagram, onSelectDiagram }: LeftSidebarProps) {
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
      return next;
    });
  }, [diagram]);

  return (
    <Box
      sx={{
        overflow: "auto",
        px: 1,
        pt: 1,
        pb: 1.5,
        minHeight: 0,
        flex: 1,
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
            <Box key={root.id} sx={{ mb: 0.5 }}>
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
                  borderRadius: 1,
                  py: 0.5,
                  minHeight: 36,
                  color: SB.text,
                  "&:hover": { bgcolor: SB.hover },
                }}
              >
                <ListItemIcon sx={{ minWidth: 28, color: SB.chevron }}>
                  {open ? <ExpandMoreIcon sx={{ fontSize: 20 }} /> : <ChevronRightIcon sx={{ fontSize: 20 }} />}
                </ListItemIcon>
                <ListItemText
                  primary={root.label}
                  primaryTypographyProps={{
                    variant: "body2",
                    sx: { fontWeight: 600, fontSize: 13, letterSpacing: "-0.01em", color: SB.text },
                  }}
                />
              </ListItemButton>
              <Collapse in={open} timeout="auto" unmountOnExit>
                <List dense disablePadding sx={{ pt: 0.25, pb: 0.25 }}>
                  {directDiagrams.map((node) => {
                    const sel = diagramSelectionForRow(node);
                    return (
                      <ListItemButton
                        key={node.id}
                        disabled={!sel}
                        selected={sel !== null && diagram !== null && selectionKey(diagram) === selectionKey(sel)}
                        onMouseEnter={() => prefetchDiagramModule(sel)}
                        onClick={() => sel && onSelectDiagram(sel)}
                        sx={{
                          borderRadius: 1,
                          pl: 3.25,
                          py: 0.35,
                          minHeight: 32,
                          color: SB.text,
                          "& .MuiListItemText-primary": { fontWeight: 400 },
                          "&.Mui-selected": {
                            bgcolor: SB.selected,
                            "&:hover": { bgcolor: "rgba(255, 255, 255, 0.95)" },
                            "& .MuiListItemText-primary": { fontWeight: 400 },
                          },
                          "&:hover": { bgcolor: SB.hover },
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 28, color: SB.icon }}>
                          <SidebarRowIcon row={node} />
                        </ListItemIcon>
                        <ListItemText primary={node.label} primaryTypographyProps={rowTypography} />
                      </ListItemButton>
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
                                borderRadius: 1,
                                pl: 3.25,
                                py: 0.35,
                                minHeight: 32,
                                color: SB.textSecondary,
                                "& .MuiListItemText-primary": { fontWeight: 400 },
                                "&:hover": { bgcolor: SB.hover },
                              }}
                            >
                              <ListItemIcon sx={{ minWidth: 28, color: SB.chevron }}>
                                {childOpen ? (
                                  <ExpandMoreIcon sx={{ fontSize: 20 }} />
                                ) : (
                                  <ChevronRightIcon sx={{ fontSize: 20 }} />
                                )}
                              </ListItemIcon>
                              <ListItemText
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
                            <Collapse in={childOpen} timeout="auto" unmountOnExit>
                              <List
                                dense
                                disablePadding
                                sx={{
                                  pl: 1.5,
                                  ml: 3.25,
                                  pb: 0.25,
                                }}
                              >
                                {erdRows.map((e) => {
                                  const sel = diagramSelectionForRow(e);
                                  const primary = erdRowLabelForDomainGroup(cnode.label, e.label);
                                  return (
                                    <ListItemButton
                                      key={e.id}
                                      disabled={!sel}
                                      selected={
                                        sel !== null &&
                                        diagram !== null &&
                                        selectionKey(diagram) === selectionKey(sel)
                                      }
                                      onMouseEnter={() => prefetchDiagramModule(sel)}
                                      onClick={() => sel && onSelectDiagram(sel)}
                                      sx={{
                                        borderRadius: 1,
                                        pl: 1,
                                        py: 0.3,
                                        minHeight: 30,
                                        color: SB.text,
                                        "& .MuiListItemText-primary": { fontWeight: 400 },
                                        "&.Mui-selected": {
                                          bgcolor: SB.selected,
                                          "&:hover": { bgcolor: "rgba(255, 255, 255, 0.95)" },
                                          "& .MuiListItemText-primary": { fontWeight: 400 },
                                        },
                                        "&:hover": { bgcolor: SB.hover },
                                      }}
                                    >
                                      <ListItemIcon sx={{ minWidth: 26, color: SB.icon }}>
                                        <SidebarRowIcon row={e} />
                                      </ListItemIcon>
                                      <ListItemText primary={primary} primaryTypographyProps={rowTypography} />
                                    </ListItemButton>
                                  );
                                })}
                              </List>
                            </Collapse>
                          </>
                        ) : (
                          <Box sx={{ pl: 3.25, py: 0.35, minHeight: 32, display: "flex", alignItems: "center" }}>
                            <Typography
                              component="div"
                              variant="body2"
                              sx={{
                                fontSize: 13,
                                fontWeight: 400,
                                color: SB.textSecondary,
                                lineHeight: 1.35,
                                letterSpacing: "-0.01em",
                                pl: 3.5,
                              }}
                            >
                              {cnode.label}
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    );
                  })}
                </List>
              </Collapse>
            </Box>
          );
        })}
    </Box>
  );
}
