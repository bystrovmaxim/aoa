// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import { AppProviders } from "./app/providers/AppProviders";
import { adoptKeyFromLocation } from "@/lib/historyKey";
import { readUrlDeepLink } from "@/lib/urlState";
import "./index.css";

// A read key that arrived after ``#key=`` moves to this tab and leaves the address bar before anything else runs (spec 037, FR-010a).
adoptKeyFromLocation();

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
