// packages/aoa-maxitor/client/src/shared/theme/maxitorTheme.ts
import { createTheme } from "@mui/material/styles";

export const maxitorTheme = createTheme({
  palette: {
    mode: "light",
    background: {
      default: "#f6f8fa",
    },
  },
  typography: {
    fontFamily: [
      "ui-sans-serif",
      "system-ui",
      "-apple-system",
      "Segoe UI",
      "Roboto",
      "Helvetica Neue",
      "Arial",
      "sans-serif",
    ].join(","),
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        "html, body, #root": {
          height: "100%",
        },
        body: {
          margin: 0,
        },
      },
    },
  },
});
