// packages/aoa-client-js/src/codegen/check-drift.ts
//
// Compares a committed generated file against a freshly generated one from the live
// manifest -- for `aoa-codegen --check` (chapter 5, task 5). Not a second generator: this
// only describes where the ONE generator's two outputs (committed vs. fresh) differ: the
// manifest_version, and which named declaration (interface/type/function/const) is
// missing, stale, or changed. The `// Source: <url>` header line is deliberately
// excluded -- --check may legitimately run against a different URL (staging, localhost)
// than the one baked into the committed file's header, which is not real drift.

const MANIFEST_VERSION_PATTERN = /^\/\/ Manifest version: (.+)$/m;
const DECLARATION_NAME_PATTERN = /^export (?:interface|type|function|const)\s+(\w+)/m;
const DESCRIPTOR_CONST_PATTERN = /^const [A-Z0-9_]+_DESCRIPTOR\b/m;
const DESCRIPTOR_BLOCK_NAME = "(endpoint descriptors)";
const IMPORTS_BLOCK_NAME = "(imports)";

export function diffGeneratedSource(committed: string, fresh: string): string | null {
  const committedVersion = extractManifestVersion(committed);
  const freshVersion = extractManifestVersion(fresh);
  const committedBody = stripHeader(committed);
  const freshBody = stripHeader(fresh);

  if (committedVersion === freshVersion && committedBody === freshBody) return null;

  const lines: string[] = [];
  if (committedVersion !== freshVersion) {
    lines.push(`manifest_version: ${committedVersion ?? "(missing)"} -> ${freshVersion ?? "(missing)"}`);
  }

  const committedDecls = splitDeclarations(committedBody);
  const freshDecls = splitDeclarations(freshBody);
  const missing = [...freshDecls.keys()].filter((name) => !committedDecls.has(name));
  const stale = [...committedDecls.keys()].filter((name) => !freshDecls.has(name));
  const changed = [...freshDecls.keys()].filter(
    (name) => committedDecls.has(name) && committedDecls.get(name) !== freshDecls.get(name),
  );

  if (missing.length > 0) lines.push(`missing (in the live manifest, not in the committed file): ${missing.join(", ")}`);
  if (stale.length > 0) {
    lines.push(`stale (in the committed file, not in the live manifest -- endpoint removed?): ${stale.join(", ")}`);
  }
  if (changed.length > 0) {
    lines.push(`changed (same name, different shape -- schema drift): ${changed.join(", ")}`);
    // "(endpoint descriptors)" is one combined block for the whole file (audit finding
    // 2's fix for check-drift.ts's own naming collision only merges blocks that share a
    // NAME; this one is deliberately one block by construction, api-layout-to-ts.ts's
    // renderDescriptorConst output joined by a single "\n" -- see its own comment). A
    // pure route/method rename with no schema change reports only this one opaque name
    // -- audit finding 15 -- so when it's among the changed blocks, name the specific
    // descriptor(s) whose own line actually differs, not just the block as a whole.
    if (changed.includes(DESCRIPTOR_BLOCK_NAME)) {
      const detail = diffDescriptorRoutes(committedDecls.get(DESCRIPTOR_BLOCK_NAME)!, freshDecls.get(DESCRIPTOR_BLOCK_NAME)!);
      if (detail) lines.push(detail);
    }
  }

  return lines.join("\n");
}

function diffDescriptorRoutes(committedBlock: string, freshBlock: string): string | null {
  const committedLines = extractDescriptorLines(committedBlock);
  const freshLines = extractDescriptorLines(freshBlock);
  const routeChanged = [...freshLines.keys()].filter(
    (name) => committedLines.has(name) && committedLines.get(name) !== freshLines.get(name),
  );
  return routeChanged.length > 0 ? `  -> within ${DESCRIPTOR_BLOCK_NAME}, route changed for: ${routeChanged.join(", ")}` : null;
}

function extractDescriptorLines(block: string): Map<string, string> {
  const lines = new Map<string, string>();
  for (const line of block.split("\n")) {
    const match = /^const ([A-Z0-9_]+_DESCRIPTOR)\b/.exec(line);
    if (match) lines.set(match[1], line);
  }
  return lines;
}

function extractManifestVersion(source: string): string | undefined {
  return MANIFEST_VERSION_PATTERN.exec(source)?.[1];
}

// Strips the 3-line "// AUTO-GENERATED.../// Source:.../// Manifest version:..." comment
// block (everything up to the first blank line), so neither the environment-dependent
// Source line nor the separately-reported manifest_version leak into the per-declaration
// body diff below.
function stripHeader(source: string): string {
  const blankLineIndex = source.indexOf("\n\n");
  return blankLineIndex === -1 ? source : source.slice(blankLineIndex + 2);
}

function splitDeclarations(body: string): Map<string, string> {
  const blocks = body.split(/\n{2,}/).filter((block) => block.trim().length > 0);
  const decls = new Map<string, string>();
  blocks.forEach((block, index) => {
    const name = declarationName(block, index);
    // A name collision here would mean generateClient itself produced two blocks it
    // considers the same declaration, which naming.ts's NameRegistry already prevents.
    decls.set(name, block);
  });
  return decls;
}

function declarationName(block: string, index: number): string {
  // All per-endpoint descriptor consts are joined by a single "\n" (see
  // api-layout-to-ts.ts), landing in one combined block -- naming it after just the
  // first one found would misreport which endpoint's descriptor actually changed, so
  // this whole block is named as a single unit instead.
  if (DESCRIPTOR_CONST_PATTERN.test(block)) return DESCRIPTOR_BLOCK_NAME;
  // generate-client.ts's renderImports() always emits the file's first content block
  // (right after the header) as `import ...`/`export type { ... } from ...` lines --
  // neither matches DECLARATION_NAME_PATTERN (bare `import` isn't `export`, and
  // `export type { X } from "..."` isn't `export type NAME =`), so this always fell
  // through to the generic "(unrecognized block 0)" (audit finding 17). Checked by
  // content, not position (block 0), so it stays correct even if generateClient's own
  // section order ever changes -- no other block starts with a bare `import`.
  if (block.startsWith("import ")) return IMPORTS_BLOCK_NAME;
  const match = DECLARATION_NAME_PATTERN.exec(block);
  return match ? match[1] : `(unrecognized block ${index})`;
}
