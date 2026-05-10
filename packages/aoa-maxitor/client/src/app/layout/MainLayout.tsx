// packages/aoa-maxitor/client/src/app/layout/MainLayout.tsx
import Drawer from "@mui/material/Drawer";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import { DRAWER_WIDTH } from "../../shared/constants/layout";

type MainLayoutProps = {
  sidebar: ReactNode;
  children: ReactNode;
};

export function MainLayout({ sidebar, children }: MainLayoutProps) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <AppBar
        position="static"
        color="default"
        elevation={0}
        sx={{ borderBottom: 1, borderColor: "divider", flexShrink: 0 }}
      >
        <Toolbar variant="dense" sx={{ gap: 1, minHeight: 44 }}>
          <Typography variant="body2" color="text.secondary" component="div">
            Maxitor shell (React + MUI). Interchange graph loads as iframe HTML from{" "}
            <Box component="code" sx={{ fontSize: "0.85em" }}>
              /api/diagrams/graph
            </Box>
            ; ERD uses JSON from{" "}
            <Box component="code" sx={{ fontSize: "0.85em" }}>
              /api/v1/erd/*
            </Box>{" "}
            and the viewer shell bundled in the SPA. Sidebar from{" "}
            <Box component="code" sx={{ fontSize: "0.85em" }}>
              GET /api/sidebar
            </Box>
            .
          </Typography>
        </Toolbar>
      </AppBar>

      <Box sx={{ flex: 1, minHeight: 0, minWidth: 0, display: "flex" }}>
        <Drawer
          variant="permanent"
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            [`& .MuiDrawer-paper`]: {
              width: DRAWER_WIDTH,
              boxSizing: "border-box",
              borderRight: 1,
              borderColor: "divider",
            },
          }}
        >
          {sidebar}
        </Drawer>
        <Box
          component="main"
          sx={{
            flex: 1,
            minWidth: 0,
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
