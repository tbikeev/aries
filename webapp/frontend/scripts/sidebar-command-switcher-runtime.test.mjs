// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import assert from "node:assert/strict";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const moduleUrl = pathToFileURL(
  join(root, "src/shortcuts/sidebar-command-switcher.ts"),
).href;

const { installSidebarCommandSwitcherRuntime, SIDEBAR_COMMAND_HOLD_MS } =
  await import(moduleUrl);

class DomStub {
  constructor() {
    this.visibilityState = "visible";
    this.htmlAttrs = new Set();
    this.listeners = new Map();
  }
  querySelector() {
    return null;
  }
  addEventListener(type, listener) {
    const list = this.listeners.get(type) ?? [];
    list.push(listener);
    this.listeners.set(type, list);
  }
  removeEventListener(type, listener) {
    const list = this.listeners.get(type) ?? [];
    this.listeners.set(
      type,
      list.filter((entry) => entry !== listener),
    );
  }
  get documentElement() {
    return {
      classList: { contains: () => true },
      setAttribute: (name) => this.htmlAttrs.add(name),
      removeAttribute: (name) => this.htmlAttrs.delete(name),
    };
  }
}

function makeKeyboardEvent(type, init) {
  return {
    type,
    code: init.code ?? "",
    key: init.key ?? "",
    metaKey: init.metaKey ?? false,
    ctrlKey: init.ctrlKey ?? false,
    altKey: init.altKey ?? false,
    repeat: init.repeat ?? false,
    target: init.target ?? null,
    prevented: false,
    stopped: false,
    preventDefault() {
      this.prevented = true;
    },
    stopPropagation() {
      this.stopped = true;
    },
  };
}

function makePointerEvent(init) {
  return {
    metaKey: init.metaKey ?? false,
    ctrlKey: init.ctrlKey ?? false,
  };
}

function runScenario() {
  const doc = new DomStub();
  const winListeners = new Map();
  const windowStub = {
    addEventListener(type, listener, capture) {
      const key = `${type}:${capture ? "capture" : "bubble"}`;
      const list = winListeners.get(key) ?? [];
      list.push(listener);
      winListeners.set(key, list);
    },
    removeEventListener(type, listener, capture) {
      const key = `${type}:${capture ? "capture" : "bubble"}`;
      const list = winListeners.get(key) ?? [];
      winListeners.set(
        key,
        list.filter((entry) => entry !== listener),
      );
    },
  };

  globalThis.document = doc;
  globalThis.window = windowStub;

  const timers = [];
  let timerId = 0;
  let clock = 0;
  globalThis.window.setTimeout = (fn, ms) => {
    const id = ++timerId;
    timers.push({ id, fn, at: clock + ms });
    return id;
  };
  globalThis.window.clearTimeout = (id) => {
    for (let i = timers.length - 1; i >= 0; i -= 1) {
      if (timers[i].id === id) timers.splice(i, 1);
    }
  };

  const advanceTimers = (ms) => {
    clock += ms;
    const due = timers.filter((entry) => entry.at <= clock);
    for (const entry of due) entry.fn();
    timers.splice(
      0,
      timers.length,
      ...timers.filter((entry) => entry.at > clock),
    );
  };

  const fireKeyDown = (init) => {
    const event = makeKeyboardEvent("keydown", init);
    for (const listener of winListeners.get("keydown:capture") ?? []) {
      listener(event);
    }
    return event;
  };
  const fireKeyUp = (init) => {
    const event = makeKeyboardEvent("keyup", init);
    for (const listener of winListeners.get("keyup:capture") ?? []) {
      listener(event);
    }
    return event;
  };
  const firePointerDown = (init) => {
    const event = makePointerEvent(init);
    for (const listener of winListeners.get("pointerdown:capture") ?? []) {
      listener(event);
    }
  };
  const fireBlur = () => {
    for (const [key, listeners] of winListeners.entries()) {
      if (!key.startsWith("blur:")) continue;
      for (const listener of listeners) listener();
    }
  };
  const fireVisibilityHidden = () => {
    doc.visibilityState = "hidden";
    for (const listener of doc.listeners.get("visibilitychange") ?? []) {
      listener();
    }
  };

  let frameWidth = 288;
  let frameOpen = true;
  const frame = {
    get sidebarWidth() {
      return frameWidth;
    },
    get sidebarOpen() {
      return frameOpen;
    },
    setSidebarWidth(next) {
      frameWidth = next;
    },
    setSidebarOpen(next) {
      frameOpen = next;
    },
  };

  let activated = 0;
  let dismissed = 0;
  let lastOpenedDoc = null;
  const store = {
    active: false,
    slotByDocumentId: {},
    activate() {
      activated += 1;
      this.active = true;
      doc.documentElement.setAttribute("data-sidebar-command-switcher");
    },
    dismiss() {
      dismissed += 1;
      this.active = false;
      this.slotByDocumentId = {};
      doc.documentElement.removeAttribute("data-sidebar-command-switcher");
    },
  };

  const dispose = installSidebarCommandSwitcherRuntime({
    getStore: () => store,
    onActivateDocument: (id) => {
      lastOpenedDoc = id;
    },
    isMacOS: () => true,
    scheduleHoldTimeout: (callback, delayMs) => window.setTimeout(callback, delayMs),
    clearHoldTimeout: (handle) => window.clearTimeout(handle),
  });

  return {
    store,
    frame,
    fireKeyDown,
    fireKeyUp,
    firePointerDown,
    fireBlur,
    fireVisibilityHidden,
    advanceTimers,
    dispose,
    get activated() {
      return activated;
    },
    get dismissed() {
      return dismissed;
    },
    get lastOpenedDoc() {
      return lastOpenedDoc;
    },
    doc,
  };
}

const scenario = runScenario();

scenario.fireKeyDown({ code: "MetaLeft", metaKey: true });
assert.equal(scenario.activated, 0);
scenario.advanceTimers(SIDEBAR_COMMAND_HOLD_MS - 1);
assert.equal(scenario.activated, 0);
scenario.advanceTimers(1);
assert.equal(scenario.activated, 1);
assert.equal(scenario.store.active, true);

scenario.fireKeyUp({ code: "MetaLeft", metaKey: false });
assert.equal(scenario.store.active, false);
assert.equal(scenario.frame.sidebarWidth, 288, "frame width must stay untouched");

const repeat = runScenario();
repeat.fireKeyDown({ code: "MetaLeft", metaKey: true, repeat: true });
repeat.advanceTimers(SIDEBAR_COMMAND_HOLD_MS + 10);
assert.equal(repeat.activated, 0);

const chord = runScenario();
chord.fireKeyDown({ code: "MetaLeft", metaKey: true });
chord.fireKeyDown({ code: "KeyS", key: "s", metaKey: true });
chord.advanceTimers(SIDEBAR_COMMAND_HOLD_MS + 10);
assert.equal(chord.activated, 0);

const pointerCancel = runScenario();
pointerCancel.fireKeyDown({ code: "MetaLeft", metaKey: true });
pointerCancel.firePointerDown({ metaKey: true });
pointerCancel.advanceTimers(SIDEBAR_COMMAND_HOLD_MS + 10);
assert.equal(pointerCancel.activated, 0);

const inputBlock = runScenario();
inputBlock.fireKeyDown({
  code: "MetaLeft",
  metaKey: true,
  target: { tagName: "INPUT" },
});
inputBlock.advanceTimers(SIDEBAR_COMMAND_HOLD_MS + 10);
assert.equal(inputBlock.activated, 0);

const digit = runScenario();
digit.store.slotByDocumentId = { "doc-a": 0 };
digit.fireKeyDown({ code: "MetaLeft", metaKey: true });
digit.advanceTimers(SIDEBAR_COMMAND_HOLD_MS);
assert.equal(digit.store.active, true);
const azerty = digit.fireKeyDown({
  code: "Digit1",
  key: "&",
  metaKey: true,
});
assert.equal(azerty.prevented, true);
assert.equal(digit.lastOpenedDoc, "doc-a");
assert.equal(digit.store.active, false);
assert.equal(digit.frame.sidebarWidth, 288);

const ctrlIgnored = runScenario();
ctrlIgnored.fireKeyDown({ code: "ControlLeft", ctrlKey: true });
ctrlIgnored.advanceTimers(SIDEBAR_COMMAND_HOLD_MS + 10);
assert.equal(ctrlIgnored.activated, 0);

const blur = runScenario();
blur.fireKeyDown({ code: "MetaLeft", metaKey: true });
blur.advanceTimers(SIDEBAR_COMMAND_HOLD_MS);
assert.equal(blur.store.active, true);
blur.fireBlur();
assert.equal(blur.store.active, false);

const visibility = runScenario();
visibility.fireKeyDown({ code: "MetaLeft", metaKey: true });
visibility.advanceTimers(SIDEBAR_COMMAND_HOLD_MS);
visibility.fireVisibilityHidden();
assert.equal(visibility.store.active, false);

scenario.dispose();
repeat.dispose();
chord.dispose();
pointerCancel.dispose();
inputBlock.dispose();
digit.dispose();
ctrlIgnored.dispose();
blur.dispose();
visibility.dispose();

delete globalThis.document;
delete globalThis.window;

console.log("sidebar-command-switcher-runtime.test.mjs: ok");
