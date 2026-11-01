// src/components/layout/MainLayout/SidebarCollapseContext.tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { readSidebarRail, writeSidebarRail } from "@/lib/sidebarMemory";

type SidebarCollapseContextValue = {
  collapsed: boolean;
  toggleCollapsed: () => void;
  setCollapsed: (collapsed: boolean) => void;
};

const SidebarCollapseContext = createContext<SidebarCollapseContextValue | null>(null);

export function SidebarCollapseProvider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(readSidebarRail);
  useEffect(() => writeSidebarRail(collapsed), [collapsed]);
  const toggleCollapsed = useCallback(() => {
    setCollapsed((c) => !c);
  }, []);
  const value = useMemo(
    () => ({
      collapsed,
      toggleCollapsed,
      setCollapsed,
    }),
    [collapsed, toggleCollapsed],
  );
  return <SidebarCollapseContext.Provider value={value}>{children}</SidebarCollapseContext.Provider>;
}

export function useSidebarCollapse(): SidebarCollapseContextValue {
  const ctx = useContext(SidebarCollapseContext);
  if (!ctx) {
    throw new Error("useSidebarCollapse must be used within SidebarCollapseProvider");
  }
  return ctx;
}
