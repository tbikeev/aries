// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

"use client";

import * as React from "react";

import { measureVisibleSidebarDocumentIds } from "@/shortcuts/sidebar-command-switcher";
import { useSidebarCommandSwitcherStore } from "@/stores/sidebar-command-switcher-store";

/**
 * While ⌘-hold switcher mode is active, keep slot badges aligned with the first
 * ten document rows visible in the sidebar scroller.
 */
export function SidebarCommandSwitcherSlotSync({
  scrollRootRef,
}: {
  scrollRootRef: React.RefObject<HTMLElement | null>;
}) {
  const active = useSidebarCommandSwitcherStore((s) => s.active);
  const setVisibleDocumentIds = useSidebarCommandSwitcherStore(
    (s) => s.setVisibleDocumentIds,
  );
  const syncExpandedWidthFromDom = useSidebarCommandSwitcherStore(
    (s) => s.syncExpandedWidthFromDom,
  );

  React.useEffect(() => {
    if (!active) {
      setVisibleDocumentIds([]);
      return;
    }

    let raf = 0;
    const measure = () => {
      setVisibleDocumentIds(
        measureVisibleSidebarDocumentIds(scrollRootRef.current),
      );
    };
    const schedule = () => {
      if (raf !== 0) return;
      raf = window.requestAnimationFrame(() => {
        raf = 0;
        measure();
        // Slot badges paint on the next frame; measure width after that.
        window.requestAnimationFrame(() => {
          syncExpandedWidthFromDom(scrollRootRef.current);
        });
      });
    };

    schedule();
    const root = scrollRootRef.current;
    root?.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);

    const observer =
      typeof MutationObserver !== "undefined"
        ? new MutationObserver(schedule)
        : null;
    if (observer && root) {
      observer.observe(root, { childList: true, subtree: true });
    }

    return () => {
      root?.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      observer?.disconnect();
      window.cancelAnimationFrame(raf);
    };
  }, [active, scrollRootRef, setVisibleDocumentIds, syncExpandedWidthFromDom]);

  return null;
}
