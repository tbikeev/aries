// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { readFile } from "node:fs/promises";
import { compositionModuleUrl } from "./wheel-composition-test-loader.mjs";

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
  assert.deepEqual(authoring["authoring.wheel.base.fills.houseField.backgroundColor"], [255, 255, 255]);
  assert.deepEqual(authoring["authoring.wheel.base.fills.glyphField.backgroundColor"], [200, 220, 245]);
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

async function loadWheelGeometryApi() {
  let layoutSource = await readFile(
    new URL("../src/lib/chart/wheel-layout-model.ts", import.meta.url),
    "utf8",
  );
  layoutSource = layoutSource.replaceAll('"./wheel-composition"', `"${compositionModuleUrl}"`);
  let layoutJavascript = ts.transpileModule(layoutSource, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  layoutJavascript = layoutJavascript
    .replaceAll('"./wheel-composition"', `"${compositionModuleUrl}"`)
    .replaceAll('"../chart/wheel-composition"', `"${compositionModuleUrl}"`);
  const layoutUrl = `data:text/javascript;base64,${Buffer.from(layoutJavascript).toString("base64")}`;
  const wheelSource = await readFile(
    new URL("../src/lib/chart/wheel-render-style.ts", import.meta.url),
    "utf8",
  );
  let wheelJavascript = ts.transpileModule(wheelSource, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  wheelJavascript = wheelJavascript
    .replaceAll('"./wheel-layout-model"', `"${layoutUrl}"`)
    .replaceAll('"./wheel-composition"', `"${compositionModuleUrl}"`);
  const wheelUrl = `data:text/javascript;base64,${Buffer.from(wheelJavascript).toString("base64")}`;
  const wheel = await import(wheelUrl);
  const layout = await import(layoutUrl);
  return { wheel, layout };
}

test("classic light ring geometry matches ZET-like stacking", async () => {
  const { wheel, layout } = await loadWheelGeometryApi();
  const maxRadius = 400;
  const baseInput = {
    profile: "classic",
    maxRadius,
    hasOuterRing: true,
    showTerms: false,
    showDecans: false,
    showHouses: true,
    showPositions: true,
    wheelChartStyle: "classic_light",
  };
  const single = wheel.resolveWheelRingSet(wheel.DEFAULT_WHEEL_RENDER_STYLE, {
    ...baseInput,
    mode: "single",
    comparisonWithOuterHouses: false,
  });
  assert.ok(Math.abs(single.rAsp / maxRadius - 0.8) < 0.01, "aspect zone starts near 80% radius");
  assert.ok(single.rPlanet <= single.r0 && single.rPlanet >= single.rAsp, "natal planets inside zodiac");
  assert.ok(single.r30 === maxRadius, "zodiac sits on the wheel rim");

  const comparison = wheel.resolveWheelRingSet(wheel.DEFAULT_WHEEL_RENDER_STYLE, {
    ...baseInput,
    mode: "comparison",
    comparisonWithOuterHouses: true,
  });
  assert.ok(comparison.rOuterPlanet > comparison.rPlanet, "outer chart ring is outside natal ring");
  assert.ok(comparison.rOuterPlanet <= comparison.r0, "comparison planets stay inside zodiac");
  const ringWidth = (comparison.r0 - comparison.rAsp) / 2;
  assert.ok(
    Math.abs(comparison.rOuterPlanet - (comparison.r0 - ringWidth / 2)) < 0.5,
    "outer planet lane is centered in the outer ring",
  );
  assert.ok(
    Math.abs(comparison.rPlanet - (comparison.r0 - ringWidth * 1.5)) < 0.5,
    "inner planet lane is centered in the inner ring",
  );

  const canonical = layout.resolveCanonicalWheelLayout(wheel.DEFAULT_WHEEL_RENDER_STYLE, {
    ...baseInput,
    mode: "comparison",
    comparisonWithOuterHouses: true,
  });
  assert.deepEqual({ ...canonical.rings }, { ...comparison });
  assert.deepEqual(canonical.violations, []);
  assert.equal(layout.wheelLayoutFamily({ ...baseInput, mode: "comparison" }), "classicSingle");
});
