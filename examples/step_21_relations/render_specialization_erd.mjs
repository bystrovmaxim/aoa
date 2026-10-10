/** Reproduce the tutorial image with Maxitor's current DOT builder and Graphviz. */
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { build } from "../../packages/aoa-maxitor/client/node_modules/esbuild/lib/main.js";
import { Graphviz } from "../../packages/aoa-maxitor/client/node_modules/@hpcc-js/wasm-graphviz/dist/index.js";

const builder = fileURLToPath(new URL("../../packages/aoa-maxitor/client/src/lib/buildDotSource.ts", import.meta.url));
const result = await build({ entryPoints: [builder], bundle: true, write: false, format: "esm", platform: "node" });
const { buildDotSource } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`);
const stem = new URL("./02_specialization_erd", import.meta.url);
const payload = JSON.parse(await readFile(`${stem.pathname}.json`, "utf8"));
const dot = buildDotSource(payload, "gv-dot-lr");
const graphviz = await Graphviz.load();
await writeFile(`${stem.pathname}.dot`, `${dot}\n`);
await writeFile(`${stem.pathname}.svg`, graphviz.layout(dot, "svg", "dot"));
console.log("Saved: examples/step_21_relations/02_specialization_erd.dot");
console.log("Saved: examples/step_21_relations/02_specialization_erd.svg");
