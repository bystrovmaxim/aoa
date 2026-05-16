// src/components/layout/MainLayout/MainLayout.tsx
import Drawer from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import type { ReactNode } from "react";
import { DRAWER_WIDTH, SIDEBAR_SURFACE } from "@/lib/layoutConstants";

type MainLayoutProps = {
  sidebar: ReactNode;
  children: ReactNode;
};

export function MainLayout({ sidebar, children }: MainLayoutProps) {
  return (
    <Box sx={{ display: "flex", height: "100%", minHeight: 0, minWidth: 0 }}>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
            borderRight: 1,
            borderColor: "rgba(15, 23, 42, 0.08)",
            bgcolor: SIDEBAR_SURFACE,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
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
  );
}
