// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifestSource = readFileSync(
  resolve(frontendRoot, "../daemon/manifest_service.py"),
  "utf8",
);
const homeClientSource = readFileSync(
  resolve(frontendRoot, "src/components/workshell/home-client.tsx"),
  "utf8",
);
const settingsSource = readFileSync(
  resolve(frontendRoot, "src/components/workshell/settings-dialog.tsx"),
  "utf8",
);
const optionsSource = readFileSync(
  resolve(frontendRoot, "../daemon/options_service.py"),
  "utf8",
);

test("wheel appearance quick options live under Wheel layout and Theme presets", () => {
  assert.match(manifestSource, /menu\.options\.quick\.wheel-layout\.wheel-appearance/);
  assert.match(manifestSource, /menu\.options\.quick\.theme-presets\.wheel-appearance/);
  assert.match(manifestSource, /quick\.options\.wheel-chart-style:default/);
  assert.match(manifestSource, /quick\.options\.wheel-chart-style:classic_light/);
  const wheelLayoutIndex = manifestSource.indexOf('"menu.options.quick.wheel-layout"');
  const houseRoutingIndex = manifestSource.indexOf('"menu.options.quick.anglo-dense-label-layout"');
  const wheelAppearanceInLayout = manifestSource.indexOf(
    "menu.options.quick.wheel-layout.wheel-appearance",
    wheelLayoutIndex,
  );
  assert.ok(wheelLayoutIndex >= 0 && houseRoutingIndex > wheelLayoutIndex);
  assert.ok(wheelAppearanceInLayout > houseRoutingIndex);
});

test("native quick options patch and checked state wire wheel chart style", () => {
  assert.match(homeClientSource, /quick\.options\.wheel-chart-style:/);
  assert.match(homeClientSource, /wheel_chart_style: value/);
  assert.match(homeClientSource, /"quick.options.wheel-chart-style"/);
});

test("settings appearance tab renders wheel style with catalog fallback", () => {
  assert.match(settingsSource, /WHEEL_CHART_STYLE_CATALOG/);
  assert.match(settingsSource, /normalizeWheelChartStyle\(d\.wheel_chart_style\)/);
  assert.match(settingsSource, /wheelChartStyles\?\.length \? cat\.wheelChartStyles : WHEEL_CHART_STYLE_CATALOG/);
});

test("daemon options expose wheel chart style display field and catalog", () => {
  assert.match(optionsSource, /'wheel_chart_style'/);
  assert.match(optionsSource, /'wheelChartStyles': \[dict\(item\) for item in _WHEEL_CHART_STYLE_CATALOG\]/);
  assert.match(optionsSource, /elif attr == 'wheel_chart_style':/);
});
