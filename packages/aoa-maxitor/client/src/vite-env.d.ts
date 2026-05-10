/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API base URL for production builds; omit in dev to use the Vite /api proxy. */
  readonly VITE_MAXITOR_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
