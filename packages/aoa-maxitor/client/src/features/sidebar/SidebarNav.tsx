// packages/aoa-maxitor/client/src/features/sidebar/SidebarNav.tsx
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import ListSubheader from "@mui/material/ListSubheader";
import Typography from "@mui/material/Typography";
import { DiagramListIcon } from "./DiagramListIcon";
import { diagramRouteForRow, sortNodes } from "./model";
import type { SidebarGroupedMaps, SidebarPayload } from "./types";

type SidebarNavProps = {
  sidebar: SidebarPayload | null;
  group: SidebarGroupedMaps | null;
  error: string | null;
  diagramUrl: string | null;
  onSelectDiagram: (url: string) => void;
};

export function SidebarNav({ sidebar, group, error, diagramUrl, onSelectDiagram }: SidebarNavProps) {
  return (
    <Box sx={{ overflow: "auto", px: 0.5, pt: 1, pb: 2 }}>
      {error && (
        <Typography variant="caption" color="error" sx={{ display: "block", px: 2, py: 1 }}>
          Failed to load sidebar: {error}
        </Typography>
      )}
      {!sidebar && !error && (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", px: 2, py: 1 }}>
          Loading…
        </Typography>
      )}
      {sidebar &&
        group &&
        sortNodes(sidebar.level1_nodes).map((root) => {
          const directDiagrams = sortNodes(group.diagramsByParent.get(root.id) ?? []);
          const childNodes = sortNodes(group.l2ByParent.get(root.id) ?? []);
          return (
            <List
              key={root.id}
              dense
              disablePadding
              subheader={
                <ListSubheader component="div" disableSticky sx={{ bgcolor: "background.paper", lineHeight: 2 }}>
                  {root.label}
                </ListSubheader>
              }
            >
              {directDiagrams.map((node) => {
                const dp = diagramRouteForRow(node);
                return (
                  <ListItemButton
                    key={node.id}
                    disabled={!dp}
                    selected={dp !== null && diagramUrl === dp}
                    onClick={() => dp && onSelectDiagram(dp)}
                    sx={{ pl: 2, py: 0.5 }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <DiagramListIcon row={node} />
                    </ListItemIcon>
                    <ListItemText primary={node.label} primaryTypographyProps={{ variant: "body2" }} />
                  </ListItemButton>
                );
              })}
              {childNodes.map((cnode) => {
                const erdRows = sortNodes(group.l3ByParent.get(cnode.id) ?? []);
                return (
                  <Box key={cnode.id}>
                    <ListItemButton disabled sx={{ pl: 2, py: 0.5, alignItems: "flex-start" }}>
                      <ListItemText
                        primary={
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                            <Chip label={cnode.type} size="small" variant="outlined" sx={{ height: 22 }} />
                            <Typography variant="body2" component="span">
                              {cnode.label}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItemButton>
                    <List dense disablePadding sx={{ pl: 3, borderLeft: 1, borderColor: "divider", ml: 2, mr: 0.5 }}>
                      {erdRows.map((e) => {
                        const dp = diagramRouteForRow(e);
                        return (
                          <ListItemButton
                            key={e.id}
                            disabled={!dp}
                            selected={dp !== null && diagramUrl === dp}
                            onClick={() => dp && onSelectDiagram(dp)}
                            sx={{ pl: 1, py: 0.25 }}
                          >
                            <ListItemIcon sx={{ minWidth: 32 }}>
                              <DiagramListIcon row={e} />
                            </ListItemIcon>
                            <ListItemText primary={e.label} primaryTypographyProps={{ variant: "body2" }} />
                          </ListItemButton>
                        );
                      })}
                    </List>
                  </Box>
                );
              })}
            </List>
          );
        })}
    </Box>
  );
}
