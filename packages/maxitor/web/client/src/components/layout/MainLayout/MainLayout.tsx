// src/components/layout/MainLayout/MainLayout.tsx
import Drawer from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import MenuIcon from "@mui/icons-material/Menu";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { DRAWER_WIDTH, DRAWER_WIDTH_COLLAPSED, SIDEBAR_SURFACE } from "@/lib/layoutConstants";
import { SidebarCollapseProvider, useSidebarCollapse } from "./SidebarCollapseContext";

/** Height of the row above the workspace: the left panel's header row, so the two lines meet. */
const TOP_ROW_HEIGHT = 38;
/** Below this width the top row is compact, as on a phone: the room keeps its circles and a menu, no worded buttons. */
export const TOP_ROW_COMPACT_BELOW = 1000;
const WORKSPACE_SURFACE = "#f4f5f7";

type MainLayoutProps = {
  sidebar: ReactNode;
  children: ReactNode;
  /**
   * Controls at the right of the row above the workspace — a 38 px row on the workspace surface on a
   * desktop, the existing 44 px bar on a phone. Told which, so it can lay itself out for it.
   */
  topRow?: (compact: boolean) => ReactNode;
  /** Laid over the top of the workspace, under the row (room notices). */
  overlay?: ReactNode;
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

function MainLayoutBody({ sidebar, children, topRow, overlay }: MainLayoutProps) {
  const { collapsed, setCollapsed } = useSidebarCollapse();
  const theme = useTheme();
  // Below `sm` a permanent drawer has no room to share with content — it becomes an overlay instead.
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // The row measures itself: a narrow window — or a wide sidebar — leaves it too little room for every word.
  const topRowRef = useRef<HTMLDivElement | null>(null);
  const [narrowRow, setNarrowRow] = useState(false);
  useEffect(() => {
    const row = topRowRef.current;
    if (!row || typeof ResizeObserver === "undefined") return undefined;
    const watch = new ResizeObserver(([entry]) => setNarrowRow(entry.contentRect.width < TOP_ROW_COMPACT_BELOW));
    watch.observe(row);
    return () => watch.disconnect();
  }, [isMobile]);

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
          position: "relative",
        }}
      >
        {!isMobile && topRow && (
          <Box
            ref={topRowRef}
            sx={{
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              minWidth: 0,
              height: TOP_ROW_HEIGHT,
              px: "10px",
              bgcolor: WORKSPACE_SURFACE,
              borderBottom: "1px solid rgba(15, 23, 42, 0.06)",
              position: "relative",
              zIndex: 60,
            }}
          >
            {topRow(narrowRow)}
          </Box>
        )}
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
            <Box sx={{ flex: 1 }} />
            {topRow?.(true)}
          </Box>
        )}
        <Box sx={{ flex: 1, minHeight: 0, minWidth: 0, display: "flex", flexDirection: "column", position: "relative" }}>
          {overlay}
          {children}
        </Box>
      </Box>
    </Box>
  );
}

export function MainLayout({ sidebar, children, topRow, overlay }: MainLayoutProps) {
  return (
    <SidebarCollapseProvider>
      <MainLayoutBody sidebar={sidebar} topRow={topRow} overlay={overlay}>
        {children}
      </MainLayoutBody>
    </SidebarCollapseProvider>
  );
}
