// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import { create } from "zustand";

import {
  computeCommandSwitcherExpandedWidth,
  slotAssignmentsFromVisibleDocumentIds,
} from "@/shortcuts/sidebar-command-switcher";
import { useFrameLayoutStore } from "@/stores/frame-layout-store";

type SavedSidebarLayout = {
  width: number;
  open: boolean;
};

type SidebarCommandSwitcherState = {
  /** True while the sidebar is expanded for ⌘-hold document switching. */
  active: boolean;
  expandedWidthPx: number;
  slotByDocumentId: Record<string, number>;
  savedLayout: SavedSidebarLayout | null;

  activate: (savedLayout: SavedSidebarLayout) => void;
  setVisibleDocumentIds: (visibleDocumentIds: readonly string[]) => void;
  syncExpandedWidth: () => void;
  dismiss: () => SavedSidebarLayout | null;
};

export const useSidebarCommandSwitcherStore = create<SidebarCommandSwitcherState>(
  (set, get) => ({
    active: false,
    expandedWidthPx: computeCommandSwitcherExpandedWidth(
      typeof window !== "undefined" ? window.innerWidth : 1024,
    ),
    slotByDocumentId: {},
    savedLayout: null,

    activate: (savedLayout) => {
      set({
        active: true,
        savedLayout,
        expandedWidthPx: computeCommandSwitcherExpandedWidth(window.innerWidth),
        slotByDocumentId: {},
      });
      if (typeof document !== "undefined") {
        document.documentElement.setAttribute("data-sidebar-command-switcher", "");
      }
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
      const saved = get().savedLayout;
      set({
        active: false,
        slotByDocumentId: {},
        savedLayout: null,
      });
      if (typeof document !== "undefined") {
        document.documentElement.removeAttribute("data-sidebar-command-switcher");
      }
      if (saved) {
        const frame = useFrameLayoutStore.getState();
        frame.setSidebarWidth(saved.width);
        frame.setSidebarOpen(saved.open);
      }
      return saved;
    },
  }),
);

/** End the switcher when another ⌘ shortcut runs (menu, manifest, native). */
export function dismissSidebarCommandSwitcher(): SavedSidebarLayout | null {
  return useSidebarCommandSwitcherStore.getState().dismiss();
}
