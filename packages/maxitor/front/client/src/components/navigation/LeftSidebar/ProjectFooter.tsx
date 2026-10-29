// src/components/navigation/LeftSidebar/ProjectFooter.tsx
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import GitHubIcon from "@mui/icons-material/GitHub";
import { useEffect, useState } from "react";
import { getAppInfo } from "@/api/appInfo";

/** Where the project lives: the package's folder in the AOA repository. */
export const PROJECT_URL = "https://github.com/bystrovmaxim/aoa/tree/main/packages/maxitor";

export type ProjectFooterProps = {
  /** The panel is the narrow rail: only the mark, with its tooltip. */
  collapsed: boolean;
};

/**
 * The bottom of the left panel (spec 028, FR-100 … FR-102; mockup screen 20): the GitHub mark linking to
 * the project, then **Maxitor** and the running version, centred, with no divider and no copyright. The
 * version is the one the server reports (``/api/meta/app-info``), never written into the client; while it
 * is unknown only the name shows. On the rail only the mark remains.
 */
export function ProjectFooter({ collapsed }: ProjectFooterProps) {
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAppInfo()
      .then((info) => {
        if (!cancelled) setVersion(info.version);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const mark = (
    <Box
      component="a"
      href={PROJECT_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Maxitor on GitHub"
      sx={{ display: "inline-flex", width: 20, height: 20, alignItems: "center", justifyContent: "center", color: "rgb(71, 85, 105)", "&:hover": { color: "rgb(15, 23, 42)" } }}
    >
      <GitHubIcon sx={{ fontSize: 16 }} />
    </Box>
  );

  return (
    <Box
      aria-label="About Maxitor"
      sx={{
        mt: "auto",
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "8px",
        p: collapsed ? "10px 0 12px" : "10px 14px 12px",
        fontSize: 11.5,
        color: "rgb(100, 116, 139)",
        whiteSpace: "nowrap",
      }}
    >
      {collapsed ? (
        <Tooltip title="Maxitor on GitHub" placement="right">
          {mark}
        </Tooltip>
      ) : (
        <>
          {mark}
          <Box component="span" sx={{ fontWeight: 600, color: "rgb(30, 41, 59)" }}>
            Maxitor
          </Box>
          {version && <span>{version}</span>}
        </>
      )}
    </Box>
  );
}
