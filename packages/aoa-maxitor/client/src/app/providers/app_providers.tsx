// packages/aoa-maxitor/client/src/app/providers/app_providers.tsx
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import type { ReactNode } from "react";
import { maxitorTheme } from "../../shared/theme/maxitor_theme";

type AppProvidersProps = {
  children: ReactNode;
};

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ThemeProvider theme={maxitorTheme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}
