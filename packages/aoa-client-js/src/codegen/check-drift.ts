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
  if (changed.length > 0) lines.push(`changed (same name, different shape -- schema drift): ${changed.join(", ")}`);

  return lines.join("\n");
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
  if (DESCRIPTOR_CONST_PATTERN.test(block)) return "(endpoint descriptors)";
  const match = DECLARATION_NAME_PATTERN.exec(block);
  return match ? match[1] : `(unrecognized block ${index})`;
}
