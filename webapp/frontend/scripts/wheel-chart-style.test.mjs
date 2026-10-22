// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { readFile } from "node:fs/promises";

const source = await readFile(
  new URL("../src/lib/chart/wheel-chart-style.ts", import.meta.url),
  "utf8",
);
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const {
  normalizeWheelChartStyle,
  applyWheelChartStylePalette,
  mergeWheelChartStyleAppearance,
  classicLightHouseNameRadius,
  wrapWheelCssValueReader,
  HOUSE_GLYPHS_CLASSIC_LIGHT,
  WHEEL_CHART_STYLE_CATALOG,
} = await import(
  `data:text/javascript;base64,${Buffer.from(javascript).toString("base64")}`
);

const basePalette = {
  background: "rgb(0 0 0)",
  frame: "rgb(220 220 221)",
  signs: "rgb(215 215 217)",
  angles: "rgb(205 205 209)",
  houses: "rgb(138 139 141)",
  houseNums: "rgb(59 59 60)",
  positions: "rgb(255 255 255)",
  peregrin: "rgb(205 205 209)",
  domicil: "rgb(2 191 2)",
  exil: "rgb(255 0 0)",
  exal: "rgb(255 215 0)",
  casus: "rgb(205 92 92)",
  textDim: "rgb(120 121 123)",
  textBright: "rgb(220 220 221)",
  fortune: "rgb(215 215 217)",
  elements: [],
  planets: Array.from({ length: 13 }, () => "rgb(205 205 209)"),
  aspects: Array.from({ length: 14 }, () => "rgb(205 205 209)"),
};

test("wheel chart style catalog covers every normalized value", () => {
  assert.deepEqual(
    WHEEL_CHART_STYLE_CATALOG.map((entry) => entry.value),
    ["default", "classic_light"],
  );
});

test("wheel chart style normalizes unknown values to default", () => {
  assert.equal(normalizeWheelChartStyle(undefined), "default");
  assert.equal(normalizeWheelChartStyle("classic_light"), "classic_light");
  assert.equal(normalizeWheelChartStyle("invalid"), "default");
});

test("classic light palette and authoring overrides are isolated from default", () => {
  assert.equal(applyWheelChartStylePalette(basePalette, "default").background, basePalette.background);
  const styled = applyWheelChartStylePalette(basePalette, "classic_light");
  assert.equal(styled.background, "rgb(255 255 255)");
  assert.equal(styled.frame, "rgb(0 102 204)");
  assert.equal(styled.aspects[0], "rgb(255 0 0)");
  assert.deepEqual(mergeWheelChartStyleAppearance({}, "default"), {});
  const authoring = mergeWheelChartStyleAppearance({ "authoring.wheel.base.fills.houseField.fillPattern": "paper" }, "classic_light");
  assert.equal(authoring["authoring.wheel.base.fills.zodiacBand.fillPattern"], "solid");
  assert.equal(authoring["authoring.wheel.base.fills.houseField.fillPattern"], "solid");
});

test("classic light house labels use full Roman numerals outside the zodiac band", () => {
  assert.deepEqual(HOUSE_GLYPHS_CLASSIC_LIGHT, ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]);
  assert.equal(classicLightHouseNameRadius({ rOuterMax: 200, r30: 190, rHouseName: 120 }), 206);
});

test("wheel css reader wrapper applies morinus overrides only for classic light", () => {
  const read = wrapWheelCssValueReader(() => "from-theme", "default");
  assert.equal(read("--morinus-frame"), "from-theme");
  const classic = wrapWheelCssValueReader(() => "from-theme", "classic_light");
  assert.equal(classic("--morinus-frame"), "rgb(0 102 204)");
  assert.equal(classic("--morinus-unknown"), "from-theme");
});
