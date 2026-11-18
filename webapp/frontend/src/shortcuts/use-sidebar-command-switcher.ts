// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

"use client";

import { useEffect, useRef } from "react";

import { installSidebarCommandSwitcherRuntime } from "@/shortcuts/sidebar-command-switcher-runtime";
import {
  resetSidebarCommandSwitcher,
  useSidebarCommandSwitcherStore,
} from "@/stores/sidebar-command-switcher-store";

type Options = {
  onActivateDocument: (documentId: string) => void;
};

export function useSidebarCommandSwitcher({ onActivateDocument }: Options): void {
  const onActivateDocumentRef = useRef(onActivateDocument);
  onActivateDocumentRef.current = onActivateDocument;

  useEffect(() => {
    const dispose = installSidebarCommandSwitcherRuntime({
      getStore: () => useSidebarCommandSwitcherStore.getState(),
      onActivateDocument: (documentId) => onActivateDocumentRef.current(documentId),
      scheduleHoldTimeout: (callback, delayMs) =>
        window.setTimeout(callback, delayMs),
      clearHoldTimeout: (handle) => window.clearTimeout(handle),
    });
    return () => {
      dispose();
      resetSidebarCommandSwitcher();
    };
  }, []);
}
