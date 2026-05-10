// packages/aoa-maxitor/client/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/app";
import { AppProviders } from "./app/providers/app_providers";
import "./index.css";

const rootEl = document.getElementById("root");
if (rootEl) {
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <AppProviders>
        <App />
      </AppProviders>
    </React.StrictMode>,
  );
}
