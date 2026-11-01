// src/components/history/DiffCard/StatusIcon.tsx
import type { ErdDiff } from "@/lib/buildDotSource";
import { changeDiskUri } from "@/lib/erdFilterPresence";

const ICON_SIZE_PX = 14;

/** What happened to an element, as the disk the filter panel shows for it. */
export function StatusIcon({ status }: { status: ErdDiff }) {
  return <img data-testid="status-icon" src={changeDiskUri(status)} alt={status} title={status} width={ICON_SIZE_PX} height={ICON_SIZE_PX} style={{ flexShrink: 0 }} />;
}
