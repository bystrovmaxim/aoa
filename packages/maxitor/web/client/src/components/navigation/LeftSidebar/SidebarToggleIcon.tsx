// src/components/navigation/LeftSidebar/SidebarToggleIcon.tsx
import SvgIcon, { type SvgIconProps } from "@mui/material/SvgIcon";

/** Panel-left icon: rounded frame with a fixed left rail, matching the reference. */
export function SidebarToggleIcon({ sx, ...rest }: SvgIconProps) {
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
        strokeLinejoin="round"
        strokeLinecap="round"
        d="M4.75 5.75h14.5c.55 0 1 .45 1 1v10.5c0 .55-.45 1-1 1H4.75c-.55 0-1-.45-1-1V6.75c0-.55.45-1 1-1z"
      />
      <path fill="none" stroke="currentColor" strokeWidth="1.38" strokeLinecap="round" d="M9.25 6.25v11.5" />
    </SvgIcon>
  );
}
