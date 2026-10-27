import { createHash, randomBytes } from "node:crypto";
import { writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const clientRoot = path.dirname(fileURLToPath(import.meta.url));
const backend = process.env.VITE_MAXITOR_API_BASE_URL ?? "http://127.0.0.1:8000";

/**
 * The id of this build: a tab reports it, and Maxitor compares it with the ``build.json`` it serves,
 * so a tab left open over a deploy reloads itself (spec 028, FR-090). Unique per build, so two builds of
 * one package version never look the same.
 */
const BUILD_ID = createHash("sha256").update(`${Date.now()}:${randomBytes(16).toString("hex")}`).digest("hex").slice(0, 12);

/** Write ``build.json`` next to the bundle, holding the id the page itself was built with. */
function buildId(): Plugin {
  let outDir = "dist";
  return {
    name: "maxitor-build-id",
    apply: "build",
    configResolved(config) {
      outDir = path.resolve(config.root, config.build.outDir);
    },
    closeBundle() {
      writeFileSync(path.join(outDir, "build.json"), `${JSON.stringify({ build: BUILD_ID })}\n`);
    },
  };
}

export default defineConfig({
  plugins: [react(), buildId()],
  define: {
    __MAXITOR_BUILD__: JSON.stringify(BUILD_ID),
  },
  resolve: {
    alias: {
      "@": path.join(clientRoot, "src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // Room connections keep the page's Host: Maxitor accepts a browser origin of the same host,
      // and ``changeOrigin`` would replace it with the backend's (the stand's nginx does the same).
      "/api/v1/rooms": { target: backend, changeOrigin: false, ws: true },
      "/api": { target: backend, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
