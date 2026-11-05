/**
 * Reproduce the tutorial image with Maxitor's current DOT builder and Graphviz.
 *
 * Maxitor lives in bystrovmaxim/gnomon: the script reads its client from a gnomon checkout, by default the
 * folder `gnomon` beside this repository, or the one `GNOMON` names; run `npm ci` in its client first.
 */
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const repo = fileURLToPath(new URL("../..", import.meta.url));
const client = resolve(process.env.GNOMON ?? resolve(repo, "../gnomon"), "packages/maxitor/maxitor-web/client");
const { build } = await import(pathToFileURL(resolve(client, "node_modules/esbuild/lib/main.js")).href);
const { Graphviz } = await import(pathToFileURL(resolve(client, "node_modules/@hpcc-js/wasm-graphviz/dist/index.js")).href);

const builder = resolve(client, "src/lib/buildDotSource.ts");
const result = await build({ entryPoints: [builder], bundle: true, write: false, format: "esm", platform: "node" });
const { buildDotSource } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`);
const stem = new URL("./02_specialization_erd", import.meta.url);
const payload = JSON.parse(await readFile(`${stem.pathname}.json`, "utf8"));
const dot = buildDotSource(payload, "gv-dot-lr");
const graphviz = await Graphviz.load();
await writeFile(`${stem.pathname}.dot`, `${dot}\n`);
await writeFile(`${stem.pathname}.svg`, graphviz.layout(dot, "svg", "dot"));
console.log("Saved: examples/step_24_relations/02_specialization_erd.dot");
console.log("Saved: examples/step_24_relations/02_specialization_erd.svg");
