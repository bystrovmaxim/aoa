// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import { AppProviders } from "./app/providers/AppProviders";
import { readUrlDeepLink } from "@/lib/urlState";
import "./index.css";

// The same chunk the viewer imports later; starting it here only begins the download earlier.
if (readUrlDeepLink().view === "full-graph") void import("@antv/g6");

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
