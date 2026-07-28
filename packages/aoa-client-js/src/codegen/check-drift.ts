// packages/aoa-client-js/src/codegen/check-drift.ts
//
// Compares the committed generated file against one generated from the server right now.
// Not a second generator: it only reports where the one generator's two outputs differ --
// the manifest version, and which declaration is missing, extra, or changed.
//
// The `// Source: <url>` header line is skipped on purpose. A check may legitimately run
// against staging or localhost while the committed file names production, and that is not
// drift.

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
    // Every endpoint descriptor lives in one combined block, so renaming a single route
    // would otherwise be reported as "that whole block changed" and tell the reader
    // nothing. When this block is among the changed ones, name the individual
    // descriptors whose own line differs.
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
  // The imports block declares no name of its own, so without this it is reported as an
  // unrecognised block and the reader has to go and look. Recognised by what it starts
  // with rather than by its position, so reordering the generated file does not break
  // it -- nothing else begins with a bare `import`.
  if (block.startsWith("import ")) return IMPORTS_BLOCK_NAME;
  const match = DECLARATION_NAME_PATTERN.exec(block);
  return match ? match[1] : `(unrecognized block ${index})`;
}
