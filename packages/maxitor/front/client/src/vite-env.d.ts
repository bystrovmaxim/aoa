// src/vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API base URL for production builds; omit in dev to use the Vite /api proxy. */
  readonly VITE_MAXITOR_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/** The id of the client build this page runs, written by ``vite.config.ts`` (spec 028, FR-090). */
declare const __MAXITOR_BUILD__: string;
