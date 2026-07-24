import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const packageRoot = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  build: {
    lib: {
      entry: {
        index: path.join(packageRoot, "src/index.ts"),
        codegen: path.join(packageRoot, "src/codegen/index.ts"),
      },
      name: "AoaClientJs",
      formats: ["es"],
    },
  },
  test: {
    environment: "node",
  },
});
