// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

import type { ChartPalette } from "./types";
import type { WheelCssValueReader } from "./wheel-render-style";

/** User-facing chart wheel colour style (independent of app chrome theme). */
export type WheelChartStyle = "default" | "classic_light";

export const WHEEL_CHART_STYLE_DEFAULT: WheelChartStyle = "default";

export const WHEEL_CHART_STYLE_VALUES = ["default", "classic_light"] as const;

export function normalizeWheelChartStyle(value: unknown): WheelChartStyle {
  return value === "classic_light" ? "classic_light" : WHEEL_CHART_STYLE_DEFAULT;
}

export function isClassicLightWheelChartStyle(style: WheelChartStyle): boolean {
  return style === "classic_light";
}

/** Full Roman house numerals for the Classic light wheel. */
export const HOUSE_GLYPHS_CLASSIC_LIGHT = [
  "I",
  "II",
  "III",
  "IV",
  "V",
  "VI",
  "VII",
  "VIII",
  "IX",
  "X",
  "XI",
  "XII",
] as const;

const MEDIUM_BLUE = "rgb(0 102 204)";
const LIGHT_BLUE = "rgb(200 220 245)";
const DARK_BLUE = "rgb(0 0 128)";
const ASC_RED = "rgb(255 0 0)";
const INK = "rgb(17 17 17)";
const WHITE = "rgb(255 255 255)";

/** Astro-Seek / Daylight aspect families on a white wheel field. */
const CLASSIC_LIGHT_ASPECTS: readonly string[] = [
  "rgb(255 0 0)",
  "rgb(0 128 0)",
  "rgb(214 96 0)",
  "rgb(0 0 255)",
  "rgb(179 122 0)",
  "rgb(255 0 0)",
  "rgb(0 0 255)",
  "rgb(214 96 0)",
  "rgb(179 122 0)",
  "rgb(0 128 0)",
  "rgb(255 0 0)",
  "rgb(128 0 160)",
  "rgb(0 128 0)",
  "rgb(128 0 160)",
];

const CLASSIC_LIGHT_MORINUS_VARS: Readonly<Record<string, string>> = {
  "--morinus-background": WHITE,
  "--morinus-frame": MEDIUM_BLUE,
  "--morinus-signs": MEDIUM_BLUE,
  "--morinus-angles": ASC_RED,
  "--morinus-houses": LIGHT_BLUE,
  "--morinus-housenums": MEDIUM_BLUE,
  "--morinus-positions": DARK_BLUE,
  "--morinus-text-bright": INK,
  "--morinus-text-dim": "rgb(68 68 68)",
};

const CLASSIC_LIGHT_FILL_OVERRIDES: Readonly<Record<string, unknown>> = {
  "authoring.wheel.base.fills.chartField.backgroundColor": [255, 255, 255],
  "authoring.wheel.base.fills.chartField.fillPattern": "solid",
  "authoring.wheel.base.fills.centerField.backgroundColor": [255, 255, 255],
  "authoring.wheel.base.fills.centerField.fillPattern": "solid",
  "authoring.wheel.base.fills.glyphField.backgroundColor": [255, 255, 255],
  "authoring.wheel.base.fills.glyphField.fillPattern": "solid",
  "authoring.wheel.base.fills.houseField.backgroundColor": [200, 220, 245],
  "authoring.wheel.base.fills.houseField.fillPattern": "solid",
  "authoring.wheel.base.fills.zodiacBand.backgroundColor": [0, 102, 204],
  "authoring.wheel.base.fills.zodiacBand.fillPattern": "solid",
  "authoring.wheel.base.fills.zodiacBand.patternColor": [255, 255, 255],
  "authoring.wheel.base.fills.zodiacBand.opacity": 100,
};

export function wheelChartStyleCssOverrides(
  style: WheelChartStyle,
): Readonly<Record<string, string>> {
  return isClassicLightWheelChartStyle(style) ? CLASSIC_LIGHT_MORINUS_VARS : {};
}

export function wrapWheelCssValueReader(
  readValue: WheelCssValueReader,
  style: WheelChartStyle,
): WheelCssValueReader {
  const overrides = wheelChartStyleCssOverrides(style);
  if (!Object.keys(overrides).length) return readValue;
  return (cssVar) => overrides[cssVar] ?? readValue(cssVar);
}

export function applyWheelChartStylePalette(
  palette: ChartPalette,
  style: WheelChartStyle,
): ChartPalette {
  if (!isClassicLightWheelChartStyle(style)) return palette;
  return {
    ...palette,
    background: WHITE,
    frame: MEDIUM_BLUE,
    signs: MEDIUM_BLUE,
    angles: ASC_RED,
    houses: LIGHT_BLUE,
    houseNums: MEDIUM_BLUE,
    positions: DARK_BLUE,
    peregrin: DARK_BLUE,
    textBright: INK,
    textDim: "rgb(68 68 68)",
    aspects: Array.from({ length: Math.max(palette.aspects.length, 14) }, (_, index) =>
      CLASSIC_LIGHT_ASPECTS[index] ?? CLASSIC_LIGHT_ASPECTS[0],
    ),
    planets: palette.planets.map(() => DARK_BLUE),
  };
}

export function mergeWheelChartStyleAppearance<T extends Record<string, unknown>>(
  appearance: Readonly<T>,
  style: WheelChartStyle,
): T {
  if (!isClassicLightWheelChartStyle(style)) return { ...appearance };
  return { ...appearance, ...CLASSIC_LIGHT_FILL_OVERRIDES };
}

/** Place house numerals just outside the painted zodiac band. */
export function classicLightHouseNameRadius(rings: {
  readonly rOuterMax: number;
  readonly r30: number;
  readonly rHouseName: number;
}): number {
  const anchor = rings.rOuterMax > 0 ? rings.rOuterMax : rings.r30;
  return Math.max(rings.rHouseName, anchor + 6);
}

export function classicLightHorizontalAxisColor(): string {
  return ASC_RED;
}

export function classicLightMeridianAxisColor(): string {
  return MEDIUM_BLUE;
}
