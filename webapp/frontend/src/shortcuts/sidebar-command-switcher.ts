// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

/** Hold duration before bare Command expands the sidebar switcher (ms). */
export const SIDEBAR_COMMAND_HOLD_MS = 150;

export const SIDEBAR_COMMAND_SLOT_COUNT = 10;

export function isCommandModifierEvent(event: Pick<KeyboardEvent, "metaKey" | "ctrlKey">): boolean {
  return event.metaKey || event.ctrlKey;
}

export function isMetaOrControlKey(code: string): boolean {
  return (
    code === "MetaLeft" ||
    code === "MetaRight" ||
    code === "ControlLeft" ||
    code === "ControlRight"
  );
}

/** Map ⌘1…⌘9 / ⌘0 to slot index 0…9. */
export function commandDigitToSlotIndex(key: string): number | null {
  if (key.length !== 1) return null;
  if (key >= "1" && key <= "9") return key.charCodeAt(0) - "1".charCodeAt(0);
  if (key === "0") return 9;
  return null;
}

export function commandSlotShortcutLabel(slotIndex: number): string {
  if (slotIndex < 0 || slotIndex >= SIDEBAR_COMMAND_SLOT_COUNT) return "";
  const digit = slotIndex === 9 ? "0" : String(slotIndex + 1);
  return `⌘${digit}`;
}

export function computeCommandSwitcherExpandedWidth(windowInnerWidth: number): number {
  if (!Number.isFinite(windowInnerWidth) || windowInnerWidth <= 0) return 320;
  return Math.max(320, Math.floor(windowInnerWidth));
}

export function slotAssignmentsFromVisibleDocumentIds(
  visibleDocumentIds: readonly string[],
): Record<string, number> {
  const next: Record<string, number> = {};
  const limit = Math.min(SIDEBAR_COMMAND_SLOT_COUNT, visibleDocumentIds.length);
  for (let slot = 0; slot < limit; slot += 1) {
    const docId = visibleDocumentIds[slot];
    if (docId) next[docId] = slot;
  }
  return next;
}

export function resolveDocumentIdForCommandSlot(
  slotIndex: number,
  slotByDocumentId: Readonly<Record<string, number>>,
): string | null {
  for (const [docId, slot] of Object.entries(slotByDocumentId)) {
    if (slot === slotIndex) return docId;
  }
  return null;
}

/** Visible document rows in sidebar scroll order (top → bottom). */
export function measureVisibleSidebarDocumentIds(
  scrollRoot: HTMLElement | null,
): string[] {
  if (!scrollRoot) return [];
  const rootRect = scrollRoot.getBoundingClientRect();
  const rows = scrollRoot.querySelectorAll<HTMLElement>(
    "[data-aries-sidebar-document-row]",
  );
  const visible: { id: string; top: number }[] = [];
  for (const row of rows) {
    const id = row.dataset.ariesSidebarDocumentId;
    if (!id) continue;
    const rect = row.getBoundingClientRect();
    if (rect.bottom <= rootRect.top + 1 || rect.top >= rootRect.bottom - 1) {
      continue;
    }
    visible.push({ id, top: rect.top });
  }
  visible.sort((a, b) => a.top - b.top || a.id.localeCompare(b.id));
  return visible.slice(0, SIDEBAR_COMMAND_SLOT_COUNT).map((entry) => entry.id);
}
