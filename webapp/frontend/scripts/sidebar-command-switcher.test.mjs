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
  commandDigitToSlotIndex,
  commandSlotShortcutLabel,
  computeCommandSwitcherExpandedWidth,
  slotAssignmentsFromVisibleDocumentIds,
  resolveDocumentIdForCommandSlot,
  isMetaOrControlKey,
} = await import(moduleUrl);

assert.equal(SIDEBAR_COMMAND_HOLD_MS, 150);
assert.equal(commandDigitToSlotIndex("1"), 0);
assert.equal(commandDigitToSlotIndex("9"), 8);
assert.equal(commandDigitToSlotIndex("0"), 9);
assert.equal(commandDigitToSlotIndex("a"), null);
assert.equal(commandSlotShortcutLabel(0), "⌘1");
assert.equal(commandSlotShortcutLabel(9), "⌘0");
assert.equal(computeCommandSwitcherExpandedWidth(1200), 1200);
assert.deepEqual(
  slotAssignmentsFromVisibleDocumentIds(["a", "b", "c"]),
  { a: 0, b: 1, c: 2 },
);
assert.equal(
  resolveDocumentIdForCommandSlot(1, { x: 0, y: 1 }),
  "y",
);
assert.equal(isMetaOrControlKey("MetaLeft"), true);
assert.equal(isMetaOrControlKey("KeyA"), false);

const homeClient = readFileSync(
  join(root, "src/components/workshell/home-client.tsx"),
  "utf8",
);
assert.match(homeClient, /useSidebarCommandSwitcher\(\{ onActivateDocument: handleSelect \}\)/);

const globals = readFileSync(join(root, "src/app/globals.css"), "utf8");
assert.match(globals, /\[data-sidebar-command-switcher\][\s\S]*aries-sidebar-navrow--command-slot/);

console.log("sidebar-command-switcher.test.mjs: ok");
