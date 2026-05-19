// src/components/layout/MainLayout/MainLayout.tsx
import Drawer from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import type { ReactNode } from "react";
import { DRAWER_WIDTH, DRAWER_WIDTH_COLLAPSED, SIDEBAR_SURFACE } from "@/lib/layoutConstants";
import { SidebarCollapseProvider, useSidebarCollapse } from "./SidebarCollapseContext";

type MainLayoutProps = {
  sidebar: ReactNode;
  children: ReactNode;
};

function MainLayoutBody({ sidebar, children }: MainLayoutProps) {
  const { collapsed } = useSidebarCollapse();
  const drawerWidth = collapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH;

  return (
    <Box sx={{ display: "flex", height: "100%", minHeight: 0, minWidth: 0 }}>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          transition: "none",
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: "border-box",
            borderRight: 1,
            borderColor: "rgba(15, 23, 42, 0.08)",
            bgcolor: SIDEBAR_SURFACE,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            transition: "none",
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

export function MainLayout({ sidebar, children }: MainLayoutProps) {
  return (
    <SidebarCollapseProvider>
      <MainLayoutBody sidebar={sidebar}>{children}</MainLayoutBody>
    </SidebarCollapseProvider>
  );
}
