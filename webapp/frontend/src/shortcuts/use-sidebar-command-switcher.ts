// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

"use client";

import { useEffect, useRef } from "react";

import {
  SIDEBAR_COMMAND_HOLD_MS,
  commandDigitToSlotIndex,
  isCommandModifierEvent,
  isMetaOrControlKey,
  resolveDocumentIdForCommandSlot,
} from "@/shortcuts/sidebar-command-switcher";
import { useFrameLayoutStore } from "@/stores/frame-layout-store";
import {
  dismissSidebarCommandSwitcher,
  useSidebarCommandSwitcherStore,
} from "@/stores/sidebar-command-switcher-store";

type Options = {
  onActivateDocument: (documentId: string) => void;
};

function targetAllowsCommandSwitcher(target: EventTarget | null): boolean {
  const element = target as HTMLElement | null;
  if (!element) return true;
  return !(
    element.tagName === "INPUT" ||
    element.tagName === "TEXTAREA" ||
    element.tagName === "SELECT" ||
    element.isContentEditable
  );
}

function chartScopeIsClear(): boolean {
  if (typeof document === "undefined") return true;
  return (
    document.querySelector(
      '[role="dialog"][data-state="open"], [role="alertdialog"][data-state="open"]',
    ) === null
  );
}

export function useSidebarCommandSwitcher({ onActivateDocument }: Options): void {
  const activate = useSidebarCommandSwitcherStore((s) => s.activate);
  const active = useSidebarCommandSwitcherStore((s) => s.active);
  const slotByDocumentId = useSidebarCommandSwitcherStore((s) => s.slotByDocumentId);

  const activeRef = useRef(active);
  const slotMapRef = useRef(slotByDocumentId);
  const metaHeldRef = useRef(false);
  const pendingTimerRef = useRef<number | null>(null);
  const chordDuringPendingRef = useRef(false);
  const onActivateDocumentRef = useRef(onActivateDocument);

  activeRef.current = active;
  slotMapRef.current = slotByDocumentId;
  onActivateDocumentRef.current = onActivateDocument;

  const clearPendingTimer = () => {
    if (pendingTimerRef.current != null) {
      window.clearTimeout(pendingTimerRef.current);
      pendingTimerRef.current = null;
    }
  };

  const restoreSavedLayout = () => {
    dismissSidebarCommandSwitcher();
  };

  const beginPendingHold = () => {
    if (activeRef.current || pendingTimerRef.current != null) return;
    chordDuringPendingRef.current = false;
    pendingTimerRef.current = window.setTimeout(() => {
      pendingTimerRef.current = null;
      if (!metaHeldRef.current || chordDuringPendingRef.current || activeRef.current) {
        return;
      }
      const frame = useFrameLayoutStore.getState();
      const savedLayout = {
        width: frame.sidebarWidth,
        open: frame.sidebarOpen,
      };
      if (!frame.sidebarOpen) {
        frame.setSidebarOpen(true);
      }
      activate(savedLayout);
    }, SIDEBAR_COMMAND_HOLD_MS);
  };

  const cancelPendingHold = () => {
    clearPendingTimer();
    chordDuringPendingRef.current = true;
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!chartScopeIsClear() || !targetAllowsCommandSwitcher(event.target)) {
        return;
      }

      if (isMetaOrControlKey(event.code)) {
        if (event.repeat) return;
        metaHeldRef.current = true;
        if (!activeRef.current) beginPendingHold();
        return;
      }

      if (!isCommandModifierEvent(event)) return;

      if (event.altKey) {
        if (activeRef.current) restoreSavedLayout();
        cancelPendingHold();
        return;
      }

      const slotIndex = commandDigitToSlotIndex(event.key);
      if (slotIndex != null && activeRef.current) {
        event.preventDefault();
        event.stopPropagation();
        const docId = resolveDocumentIdForCommandSlot(
          slotIndex,
          slotMapRef.current,
        );
        restoreSavedLayout();
        metaHeldRef.current = false;
        clearPendingTimer();
        if (docId) onActivateDocumentRef.current(docId);
        return;
      }

      if (!activeRef.current) {
        cancelPendingHold();
        return;
      }

      restoreSavedLayout();
    };

    const onKeyUp = (event: KeyboardEvent) => {
      if (!isMetaOrControlKey(event.code)) return;
      metaHeldRef.current = false;
      clearPendingTimer();
      if (activeRef.current) {
        restoreSavedLayout();
      }
    };

    const onBlur = () => {
      metaHeldRef.current = false;
      clearPendingTimer();
      if (activeRef.current) restoreSavedLayout();
    };

    window.addEventListener("keydown", onKeyDown, true);
    window.addEventListener("keyup", onKeyUp, true);
    window.addEventListener("blur", onBlur);
    return () => {
      window.removeEventListener("keydown", onKeyDown, true);
      window.removeEventListener("keyup", onKeyUp, true);
      window.removeEventListener("blur", onBlur);
      clearPendingTimer();
    };
  }, [activate]);
}
