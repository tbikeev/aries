// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import { create } from "zustand";

import {
  computeCommandSwitcherFitWidth,
  measureCommandSwitcherContentWidth,
  readShellSidebarWidthPx,
  slotAssignmentsFromVisibleDocumentIds,
} from "@/shortcuts/sidebar-command-switcher";

type SidebarCommandSwitcherState = {
  /** True while the sidebar is expanded for ⌘-hold document switching. */
  active: boolean;
  /** Sidebar column width captured when ⌘-hold began (never shrink below this). */
  baselineWidthPx: number;
  expandedWidthPx: number;
  slotByDocumentId: Record<string, number>;

  activate: () => void;
  setVisibleDocumentIds: (visibleDocumentIds: readonly string[]) => void;
  syncExpandedWidthFromDom: (scrollRoot: HTMLElement | null) => void;
  dismiss: () => void;
};

function clearSwitcherDomFlag(): void {
  if (typeof document !== "undefined") {
    document.documentElement.removeAttribute("data-sidebar-command-switcher");
  }
}

function setSwitcherDomFlag(): void {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-sidebar-command-switcher", "");
  }
}

export const useSidebarCommandSwitcherStore = create<SidebarCommandSwitcherState>(
  (set, get) => ({
    active: false,
    baselineWidthPx: 272,
    expandedWidthPx: 272,
    slotByDocumentId: {},

    activate: () => {
      const baseline = readShellSidebarWidthPx(
        typeof document !== "undefined" ? document : undefined,
      );
      set({
        active: true,
        baselineWidthPx: baseline,
        expandedWidthPx: baseline,
        slotByDocumentId: {},
      });
      setSwitcherDomFlag();
    },

    setVisibleDocumentIds: (visibleDocumentIds) => {
      if (!get().active) return;
      set({
        slotByDocumentId: slotAssignmentsFromVisibleDocumentIds(visibleDocumentIds),
      });
    },

    syncExpandedWidthFromDom: (scrollRoot) => {
      if (!get().active) return;
      const { baselineWidthPx } = get();
      const contentNeedPx = measureCommandSwitcherContentWidth(scrollRoot);
      set({
        expandedWidthPx: computeCommandSwitcherFitWidth({
          baselineWidthPx,
          contentNeedPx,
          windowInnerWidth: window.innerWidth,
        }),
      });
    },

    dismiss: () => {
      set({
        active: false,
        slotByDocumentId: {},
      });
      clearSwitcherDomFlag();
    },
  }),
);

/** End the switcher when another ⌘ shortcut runs (menu, manifest, native). */
export function dismissSidebarCommandSwitcher(): void {
  useSidebarCommandSwitcherStore.getState().dismiss();
}

/** Hard reset for hook teardown and stuck-state recovery. */
export function resetSidebarCommandSwitcher(): void {
  useSidebarCommandSwitcherStore.getState().dismiss();
  clearSwitcherDomFlag();
}
