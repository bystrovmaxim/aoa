// packages/aoa-maxitor/client/src/features/diagram-viewer/erd/lib/domainTabKeys.ts
/** Stable tab keys for ``ERD_DATA.domains`` (same collision rule as the server-side materializer). */
export function allocateDomainTabKey(used: Set<string>, base: string): string {
  let key = base;
  let n = 2;
  while (used.has(key)) {
    key = `${base} (${n})`;
    n += 1;
  }
  used.add(key);
  return key;
}
