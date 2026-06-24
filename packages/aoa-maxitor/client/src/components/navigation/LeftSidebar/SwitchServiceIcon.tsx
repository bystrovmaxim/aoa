// src/components/navigation/LeftSidebar/SwitchServiceIcon.tsx
import SvgIcon, { type SvgIconProps } from "@mui/material/SvgIcon";

/** Thin-stroke swap-arrows icon matching SidebarToggleIcon stroke weight. */
export function SwitchServiceIcon({ sx, ...rest }: SvgIconProps) {
  return (
    <SvgIcon
      {...rest}
      viewBox="0 0 24 24"
      sx={[{ overflow: "visible" }, ...(Array.isArray(sx) ? sx : sx ? [sx] : [])]}
    >
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.38"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4.75 8h14.5M15.75 5l3 3-3 3"
      />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.38"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.25 16H4.75M8.25 13l-3 3 3 3"
      />
    </SvgIcon>
  );
}
