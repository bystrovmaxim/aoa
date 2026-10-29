// src/app/providers/AppProviders.tsx
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import type { ReactNode } from "react";
import { maxitorTheme } from "@/styles/theme";

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
