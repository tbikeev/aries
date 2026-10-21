// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

/** Hold duration before bare Command expands the sidebar switcher (ms). */
export const SIDEBAR_COMMAND_HOLD_MS = 150;

export const SIDEBAR_COMMAND_SLOT_COUNT = 10;

const DIGIT_CODE_TO_SLOT: Record<string, number> = {
  Digit1: 0,
  Digit2: 1,
  Digit3: 2,
  Digit4: 3,
  Digit5: 4,
  Digit6: 5,
  Digit7: 6,
  Digit8: 7,
  Digit9: 8,
  Digit0: 9,
};

/** Physical top-row digit keys (AZERTY-safe — do not use `event.key`). */
export function commandDigitCodeToSlotIndex(code: string): number | null {
  const slot = DIGIT_CODE_TO_SLOT[code];
  return slot === undefined ? null : slot;
}

export function isMetaPhysicalKey(code: string): boolean {
  return code === "MetaLeft" || code === "MetaRight";
}

/** True when the platform ⌘ modifier is held (never Control alone). */
export function isCommandHoldModifier(
  event: Pick<KeyboardEvent, "metaKey" | "ctrlKey">,
): boolean {
  return event.metaKey === true && event.ctrlKey !== true;
}

export function detectMacOSPlatform(): boolean {
  if (typeof document !== "undefined") {
    if (document.documentElement.classList.contains("is-macos")) return true;
  }
  if (typeof navigator === "undefined") return true;
  return /Mac|iPhone|iPod|iPad/i.test(navigator.platform);
}

export function commandSlotShortcutLabel(slotIndex: number): string {
  if (slotIndex < 0 || slotIndex >= SIDEBAR_COMMAND_SLOT_COUNT) return "";
  const digit = slotIndex === 9 ? "0" : String(slotIndex + 1);
  return `⌘${digit}`;
}

export function commandSlotAriaShortcut(slotIndex: number): string {
  const digit = slotIndex === 9 ? "0" : String(slotIndex + 1);
  return `Meta+${digit}`;
}

/** Hard cap for ⌘-hold expansion (px). */
export const SIDEBAR_COMMAND_EXPAND_MAX_PX = 480;

/** Never expand past this fraction of the window width. */
export const SIDEBAR_COMMAND_EXPAND_MAX_WINDOW_FRACTION = 0.5;

export function commandSwitcherExpandCapPx(windowInnerWidth: number): number {
  if (!Number.isFinite(windowInnerWidth) || windowInnerWidth <= 0) {
    return SIDEBAR_COMMAND_EXPAND_MAX_PX;
  }
  const halfWindow = Math.floor(windowInnerWidth * SIDEBAR_COMMAND_EXPAND_MAX_WINDOW_FRACTION);
  return Math.min(SIDEBAR_COMMAND_EXPAND_MAX_PX, halfWindow);
}

export type CommandSwitcherRowMeasure = {
  paddingLeftPx: number;
  paddingRightPx: number;
  labelScrollWidthPx: number;
  hintScrollWidthPx: number;
  closeButtonWidthPx: number;
};

/** Width one document row needs so label + badge + chrome fit without truncation. */
export function measureSidebarRowContentNeedPx(row: CommandSwitcherRowMeasure): number {
  const hintGapPx = row.hintScrollWidthPx > 0 ? 8 : 0;
  return (
    row.paddingLeftPx +
    row.labelScrollWidthPx +
    hintGapPx +
    row.hintScrollWidthPx +
    row.paddingRightPx +
    row.closeButtonWidthPx
  );
}

export function computeCommandSwitcherFitWidth(input: {
  baselineWidthPx: number;
  contentNeedPx: number;
  windowInnerWidth: number;
  scrollRootHorizontalPaddingPx?: number;
}): number {
  const baseline = Number.isFinite(input.baselineWidthPx)
    ? Math.max(0, input.baselineWidthPx)
    : 0;
  const cap = commandSwitcherExpandCapPx(input.windowInnerWidth);
  const shellPadding = input.scrollRootHorizontalPaddingPx ?? 0;
  const target = Math.ceil(input.contentNeedPx + shellPadding);
  const clamped = Math.min(cap, target);
  return Math.max(baseline, clamped);
}

export function readShellSidebarWidthPx(doc: Document | undefined): number {
  if (!doc) return 272;
  const shell = doc.querySelector<HTMLElement>(".app-shell");
  if (!shell) return 272;
  const raw = doc.defaultView?.getComputedStyle(shell).getPropertyValue("--sidebar-width").trim();
  const parsed = raw ? parseFloat(raw) : Number.NaN;
  return Number.isFinite(parsed) ? parsed : 272;
}

function parseCssPx(value: string): number {
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function measureRowElementContentNeed(row: HTMLElement): number {
  const button = row.querySelector<HTMLElement>('[data-slot="sidebar-menu-button"]');
  if (!button) return 0;
  const label =
    row.querySelector<HTMLElement>(".aries-sidebar-navrow-label-faded") ??
    row.querySelector<HTMLElement>(".aries-sidebar-navrow-label");
  const hint = row.querySelector<HTMLElement>(".aries-sidebar-shortcut-hint");
  const closeButton = row.querySelector<HTMLElement>(
    'button[type="button"][aria-label]',
  );
  const style = button.ownerDocument.defaultView?.getComputedStyle(button);
  if (!style) return 0;
  return measureSidebarRowContentNeedPx({
    paddingLeftPx: parseCssPx(style.paddingLeft),
    paddingRightPx: parseCssPx(style.paddingRight),
    labelScrollWidthPx: label?.scrollWidth ?? 0,
    hintScrollWidthPx: hint?.scrollWidth ?? 0,
    closeButtonWidthPx: closeButton ? closeButton.offsetWidth : 0,
  });
}

/** Widest visible document row in the sidebar scroller (+ horizontal content padding). */
export function measureCommandSwitcherContentWidth(
  scrollRoot: HTMLElement | null,
): number {
  if (!scrollRoot) return 0;
  const rootRect = scrollRoot.getBoundingClientRect();
  const rows = scrollRoot.querySelectorAll<HTMLElement>(
    "[data-aries-sidebar-document-row]",
  );
  let maxRow = 0;
  for (const row of rows) {
    const rect = row.getBoundingClientRect();
    if (rect.bottom <= rootRect.top + 1 || rect.top >= rootRect.bottom - 1) {
      continue;
    }
    maxRow = Math.max(maxRow, measureRowElementContentNeed(row));
  }
  const rootStyle = scrollRoot.ownerDocument.defaultView?.getComputedStyle(scrollRoot);
  const shellPadding = rootStyle
    ? parseCssPx(rootStyle.paddingLeft) + parseCssPx(rootStyle.paddingRight)
    : 0;
  return maxRow + shellPadding;
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

export function shouldReserveCommandDigitFromManifestDismiss(
  event: Pick<KeyboardEvent, "metaKey" | "ctrlKey" | "code">,
  switcherActive: boolean,
): boolean {
  return (
    switcherActive &&
    isCommandHoldModifier(event) &&
    commandDigitCodeToSlotIndex(event.code) != null
  );
}

export type CommandSwitcherStoreApi = {
  active: boolean;
  slotByDocumentId: Record<string, number>;
  activate: () => void;
  dismiss: () => void;
};

export type CommandSwitcherRuntimeOptions = {
  getStore: () => CommandSwitcherStoreApi;
  onActivateDocument: (documentId: string) => void;
  isMacOS?: () => boolean;
  scheduleHoldTimeout: (callback: () => void, delayMs: number) => number;
  clearHoldTimeout: (handle: number) => void;
};

export function targetAllowsCommandSwitcher(target: EventTarget | null): boolean {
  const element = target as HTMLElement | null;
  if (!element) return true;
  return !(
    element.tagName === "INPUT" ||
    element.tagName === "TEXTAREA" ||
    element.tagName === "SELECT" ||
    element.isContentEditable
  );
}

export function chartScopeIsClear(doc: Document | undefined): boolean {
  if (!doc) return true;
  return (
    doc.querySelector(
      '[role="dialog"][data-state="open"], [role="alertdialog"][data-state="open"]',
    ) === null
  );
}

export function installSidebarCommandSwitcherRuntime(
  options: CommandSwitcherRuntimeOptions,
): () => void {
  const isMacOS = options.isMacOS ?? detectMacOSPlatform;
  const win = typeof window !== "undefined" ? window : undefined;
  const doc = typeof document !== "undefined" ? document : undefined;

  let metaHeld = false;
  let pendingTimer: number | null = null;
  let chordDuringPending = false;

  const clearPendingTimer = () => {
    if (pendingTimer != null) {
      options.clearHoldTimeout(pendingTimer);
      pendingTimer = null;
    }
  };

  const dismiss = () => {
    options.getStore().dismiss();
  };

  const dismissIfActiveWithoutMeta = (event: { metaKey: boolean }) => {
    if (options.getStore().active && !event.metaKey) {
      dismiss();
    }
  };

  const cancelPendingHold = () => {
    clearPendingTimer();
    chordDuringPending = true;
  };

  const beginPendingHold = () => {
    const store = options.getStore();
    if (store.active || pendingTimer != null) return;
    chordDuringPending = false;
    pendingTimer = options.scheduleHoldTimeout(() => {
      pendingTimer = null;
      if (!metaHeld || chordDuringPending || options.getStore().active) {
        return;
      }
      options.getStore().activate();
    }, SIDEBAR_COMMAND_HOLD_MS);
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (!isMacOS()) return;
    if (!chartScopeIsClear(doc) || !targetAllowsCommandSwitcher(event.target)) {
      return;
    }

    dismissIfActiveWithoutMeta(event);

    if (isMetaPhysicalKey(event.code)) {
      if (event.repeat) return;
      metaHeld = true;
      if (!options.getStore().active) beginPendingHold();
      return;
    }

    if (!isCommandHoldModifier(event)) return;

    if (event.altKey) {
      if (options.getStore().active) dismiss();
      cancelPendingHold();
      return;
    }

    const slotIndex = commandDigitCodeToSlotIndex(event.code);
    if (slotIndex != null && options.getStore().active) {
      event.preventDefault();
      event.stopPropagation();
      const docId = resolveDocumentIdForCommandSlot(
        slotIndex,
        options.getStore().slotByDocumentId,
      );
      dismiss();
      metaHeld = false;
      clearPendingTimer();
      if (docId) options.onActivateDocument(docId);
      return;
    }

    if (!options.getStore().active) {
      cancelPendingHold();
      return;
    }

    dismiss();
  };

  const onKeyUp = (event: KeyboardEvent) => {
    if (!isMacOS()) return;
    dismissIfActiveWithoutMeta(event);
    if (!isMetaPhysicalKey(event.code)) return;
    metaHeld = false;
    clearPendingTimer();
    if (options.getStore().active) {
      dismiss();
    }
  };

  const onPointerDown = (event: PointerEvent) => {
    if (!isMacOS()) return;
    dismissIfActiveWithoutMeta(event);
    if (metaHeld || pendingTimer != null) {
      cancelPendingHold();
    }
  };

  const onPointerMove = (event: PointerEvent) => {
    if (!isMacOS()) return;
    dismissIfActiveWithoutMeta(event);
  };

  const onBlur = () => {
    metaHeld = false;
    clearPendingTimer();
    if (options.getStore().active) dismiss();
  };

  const onVisibilityChange = () => {
    if (doc?.visibilityState === "hidden") {
      metaHeld = false;
      clearPendingTimer();
      dismiss();
    }
  };

  const onPageHide = () => {
    metaHeld = false;
    clearPendingTimer();
    dismiss();
  };

  win?.addEventListener("keydown", onKeyDown, true);
  win?.addEventListener("keyup", onKeyUp, true);
  win?.addEventListener("pointerdown", onPointerDown, true);
  win?.addEventListener("pointermove", onPointerMove, true);
  win?.addEventListener("blur", onBlur);
  doc?.addEventListener("visibilitychange", onVisibilityChange);
  win?.addEventListener("pagehide", onPageHide);

  return () => {
    win?.removeEventListener("keydown", onKeyDown, true);
    win?.removeEventListener("keyup", onKeyUp, true);
    win?.removeEventListener("pointerdown", onPointerDown, true);
    win?.removeEventListener("pointermove", onPointerMove, true);
    win?.removeEventListener("blur", onBlur);
    doc?.removeEventListener("visibilitychange", onVisibilityChange);
    win?.removeEventListener("pagehide", onPageHide);
    metaHeld = false;
    clearPendingTimer();
    dismiss();
  };
}
