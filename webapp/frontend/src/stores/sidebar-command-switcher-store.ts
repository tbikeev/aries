// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import { create } from "zustand";

import {
  computeCommandSwitcherExpandedWidth,
  slotAssignmentsFromVisibleDocumentIds,
} from "@/shortcuts/sidebar-command-switcher";

type SidebarCommandSwitcherState = {
  /** True while the sidebar is expanded for ⌘-hold document switching. */
  active: boolean;
  expandedWidthPx: number;
  slotByDocumentId: Record<string, number>;

  activate: () => void;
  setVisibleDocumentIds: (visibleDocumentIds: readonly string[]) => void;
  syncExpandedWidth: () => void;
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
    expandedWidthPx: computeCommandSwitcherExpandedWidth(
      typeof window !== "undefined" ? window.innerWidth : 1024,
    ),
    slotByDocumentId: {},

    activate: () => {
      set({
        active: true,
        expandedWidthPx: computeCommandSwitcherExpandedWidth(window.innerWidth),
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

    syncExpandedWidth: () => {
      if (!get().active) return;
      set({
        expandedWidthPx: computeCommandSwitcherExpandedWidth(window.innerWidth),
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
