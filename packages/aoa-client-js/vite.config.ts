import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const packageRoot = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  build: {
    lib: {
      entry: path.join(packageRoot, "src/index.ts"),
      name: "AoaClientJs",
      fileName: "aoa-client-js",
      formats: ["es"],
    },
  },
  test: {
    environment: "node",
  },
});
