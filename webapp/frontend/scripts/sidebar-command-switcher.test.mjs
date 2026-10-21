// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const moduleUrl = pathToFileURL(
  join(root, "src/shortcuts/sidebar-command-switcher.ts"),
).href;

const {
  SIDEBAR_COMMAND_HOLD_MS,
  commandDigitCodeToSlotIndex,
  commandSlotShortcutLabel,
  commandSlotAriaShortcut,
  computeCommandSwitcherExpandedWidth,
  slotAssignmentsFromVisibleDocumentIds,
  resolveDocumentIdForCommandSlot,
  isMetaPhysicalKey,
  isCommandHoldModifier,
  shouldReserveCommandDigitFromManifestDismiss,
} = await import(moduleUrl);

assert.equal(SIDEBAR_COMMAND_HOLD_MS, 150);
assert.equal(commandDigitCodeToSlotIndex("Digit1"), 0);
assert.equal(commandDigitCodeToSlotIndex("Digit9"), 8);
assert.equal(commandDigitCodeToSlotIndex("Digit0"), 9);
assert.equal(commandDigitCodeToSlotIndex("Key1"), null);
assert.equal(
  commandDigitCodeToSlotIndex("Digit1"),
  0,
  "AZERTY & key must not be used — code Digit1 maps slot 0",
);
assert.equal(commandSlotShortcutLabel(0), "⌘1");
assert.equal(commandSlotShortcutLabel(9), "⌘0");
assert.equal(commandSlotAriaShortcut(0), "Meta+1");
assert.equal(commandSlotAriaShortcut(9), "Meta+0");
assert.equal(computeCommandSwitcherExpandedWidth(1200), 1200);
assert.deepEqual(
  slotAssignmentsFromVisibleDocumentIds(["a", "b", "c"]),
  { a: 0, b: 1, c: 2 },
);
assert.equal(
  resolveDocumentIdForCommandSlot(1, { x: 0, y: 1 }),
  "y",
);
assert.equal(isMetaPhysicalKey("MetaLeft"), true);
assert.equal(isMetaPhysicalKey("ControlLeft"), false);
assert.equal(isCommandHoldModifier({ metaKey: true, ctrlKey: false }), true);
assert.equal(isCommandHoldModifier({ metaKey: true, ctrlKey: true }), false);
assert.equal(isCommandHoldModifier({ metaKey: false, ctrlKey: true }), false);
assert.equal(
  shouldReserveCommandDigitFromManifestDismiss(
    { metaKey: true, ctrlKey: false, code: "Digit2" },
    true,
  ),
  true,
);
assert.equal(
  shouldReserveCommandDigitFromManifestDismiss(
    { metaKey: true, ctrlKey: false, code: "KeyS" },
    true,
  ),
  false,
);

const storeSource = readFileSync(
  join(root, "src/stores/sidebar-command-switcher-store.ts"),
  "utf8",
);
assert.doesNotMatch(storeSource, /setSidebarWidth/);
assert.doesNotMatch(storeSource, /setSidebarOpen/);

const homeClient = readFileSync(
  join(root, "src/components/workshell/home-client.tsx"),
  "utf8",
);
assert.match(homeClient, /useSidebarCommandSwitcher\(\{ onActivateDocument: handleSelect \}\)/);

const sidebar = readFileSync(
  join(root, "src/components/workshell/app-sidebar.tsx"),
  "utf8",
);
assert.match(sidebar, /ariaKeyShortcuts=\{commandShortcut\?\.aria\}/);

const globals = readFileSync(join(root, "src/app/globals.css"), "utf8");
assert.match(globals, /\[data-sidebar-command-switcher\][\s\S]*aries-sidebar-navrow--command-slot/);
assert.match(globals, /prefers-reduced-motion: reduce/);

const nativeMenu = readFileSync(
  join(root, "src-tauri/native-menu-manifest.json"),
  "utf8",
);
assert.doesNotMatch(nativeMenu, /CmdOrCtrl\+[0-9]/);

console.log("sidebar-command-switcher.test.mjs: ok");
