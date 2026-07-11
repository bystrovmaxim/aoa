// src/components/layout/MainLayout/MainLayout.tsx
import Drawer from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import MenuIcon from "@mui/icons-material/Menu";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import type { ReactNode } from "react";
import { DRAWER_WIDTH, DRAWER_WIDTH_COLLAPSED, SIDEBAR_SURFACE } from "@/lib/layoutConstants";
import { SidebarCollapseProvider, useSidebarCollapse } from "./SidebarCollapseContext";

type MainLayoutProps = {
  sidebar: ReactNode;
  children: ReactNode;
};

const PAPER_BASE_SX = {
  boxSizing: "border-box" as const,
  borderRight: 1,
  borderColor: "rgba(15, 23, 42, 0.08)",
  bgcolor: SIDEBAR_SURFACE,
  display: "flex",
  flexDirection: "column" as const,
  overflow: "hidden",
};

function MainLayoutBody({ sidebar, children }: MainLayoutProps) {
  const { collapsed, setCollapsed } = useSidebarCollapse();
  const theme = useTheme();
  // Below `sm` a permanent drawer has no room to share with content — it becomes an overlay instead.
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  return (
    <Box sx={{ display: "flex", height: "100%", minHeight: 0, minWidth: 0 }}>
      {isMobile ? (
        <Drawer
          variant="temporary"
          open={!collapsed}
          onClose={() => setCollapsed(true)}
          ModalProps={{ keepMounted: true }}
          sx={{ [`& .MuiDrawer-paper`]: { ...PAPER_BASE_SX, width: DRAWER_WIDTH } }}
        >
          {sidebar}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          sx={{
            width: collapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH,
            flexShrink: 0,
            transition: "none",
            [`& .MuiDrawer-paper`]: {
              ...PAPER_BASE_SX,
              width: collapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH,
              transition: "none",
            },
          }}
        >
          {sidebar}
        </Drawer>
      )}
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
        {isMobile && (
          <Box
            sx={{
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              height: 44,
              px: 0.5,
              borderBottom: 1,
              borderColor: "rgba(15, 23, 42, 0.08)",
              bgcolor: SIDEBAR_SURFACE,
            }}
          >
            <IconButton onClick={() => setCollapsed(false)} aria-label="Open sidebar" size="medium">
              <MenuIcon fontSize="small" />
            </IconButton>
          </Box>
        )}
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
