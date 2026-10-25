// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/search-ohlc.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const {
  parseSearchOhlcFile,
  buildSearchPerformanceLookup,
  listingIsoDateFromRow,
  formatPerformancePct,
  summarizeSearchPerformance,
  searchPerformanceAnomalies,
  mannWhitneyTwoSidedP,
  binomExactTwoSided,
  ohlcCloseDateSpan,
} = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);

test("parseSearchOhlcFile accepts listok-style JSON", () => {
  const payload = JSON.stringify([
    { date: "2024-01-01", close: 100 },
    { date: "2024-01-02", close: 110 },
  ]);
  const parsed = parseSearchOhlcFile("btc.json", payload);
  assert.equal(parsed.ok, true);
  if (parsed.ok) {
    assert.equal(Object.keys(parsed.series.closes).length, 2);
  }
});

test("buildSearchPerformanceLookup forward return from transit day close", () => {
  const lookup = buildSearchPerformanceLookup({
    "2024-01-01": 100,
    "2024-01-02": 100,
    "2024-01-03": 110,
  }, 1);
  assert.equal(lookup.returnForEventDay("2024-01-02"), Math.log(110 / 100));
  assert.equal(lookup.returnForEventDay("2024-01-03"), null);
});

test("buildSearchPerformanceLookup supports 3d horizon", () => {
  const lookup = buildSearchPerformanceLookup({
    "2024-01-01": 100,
    "2024-01-02": 100,
    "2024-01-03": 100,
    "2024-01-04": 120,
  }, 3);
  assert.equal(lookup.returnForEventDay("2024-01-01"), Math.log(120 / 100));
});

test("listingIsoDateFromRow prefers displayDatetime prefix", () => {
  assert.equal(
    listingIsoDateFromRow("2024-06-15T14:30:00Z", "2024-06-14"),
    "2024-06-15",
  );
});

test("formatPerformancePct signs positive moves", () => {
  assert.match(formatPerformancePct(Math.log(1.05)), /^\+/);
});

test("ohlcCloseDateSpan returns first and last close dates", () => {
  const span = ohlcCloseDateSpan({
    "2024-01-02": 1,
    "2024-01-01": 1,
    "2024-01-03": 1,
  });
  assert.equal(span?.fromDate, "2024-01-01");
  assert.equal(span?.toDate, "2024-01-03");
  assert.equal(span?.dayCount, 3);
});

test("summarizeSearchPerformance tallies visible rows", () => {
  const lookup = buildSearchPerformanceLookup({
    "2024-01-01": 100,
    "2024-01-02": 110,
    "2024-01-03": 105,
    "2024-01-04": 105,
  }, 1);
  const summary = summarizeSearchPerformance(
    [
      { displayDatetime: "2024-01-02T12:00:00Z", displayDate: "2024-01-02" },
      { displayDatetime: "2024-01-03T12:00:00Z", displayDate: "2024-01-03" },
    ],
    lookup,
    "2024-01-01",
    "2024-01-04",
  );
  assert.equal(summary?.nPos, 0);
  assert.equal(summary?.nNeg, 1);
  assert.equal(summary?.nZero, 1);
  assert.equal(summary?.eventsWithReturn, 2);
  assert.equal(summary?.hitReturnDays, 2);
  assert.equal(summary?.controlReturnDays, 1);
  assert.ok(summary?.pReturnTwoSided !== null);
});

test("searchPerformanceAnomalies flags return excess when groups diverge", () => {
  const closes = { "2024-01-01": 100 };
  for (let day = 2; day <= 14; day += 1) {
    closes[`2024-01-${String(day).padStart(2, "0")}`] = 100 + day;
  }
  closes["2024-01-15"] = 150;
  closes["2024-01-16"] = 200;
  closes["2024-01-17"] = 260;
  closes["2024-01-18"] = 320;
  closes["2024-01-19"] = 400;
  closes["2024-01-20"] = 500;
  const lookup = buildSearchPerformanceLookup(closes, 1);
  const rows = [
    { displayDatetime: "2024-01-15T12:00:00Z", displayDate: "2024-01-15" },
    { displayDatetime: "2024-01-16T12:00:00Z", displayDate: "2024-01-16" },
    { displayDatetime: "2024-01-17T12:00:00Z", displayDate: "2024-01-17" },
  ];
  const summary = summarizeSearchPerformance(rows, lookup, "2024-01-01", "2024-01-20");
  assert.ok(summary);
  assert.ok(summary.excessMeanPct > 0);
  assert.ok(summary.pReturnTwoSided !== null);
  assert.ok(summary.pReturnTwoSided < 0.05);
  assert.equal(searchPerformanceAnomalies(summary).return, true);
});

test("mannWhitneyTwoSidedP separates shifted samples", () => {
  const low = Array.from({ length: 20 }, (_, index) => index * 0.001);
  const high = Array.from({ length: 20 }, (_, index) => 0.05 + index * 0.001);
  const p = mannWhitneyTwoSidedP(high, low);
  assert.ok(p !== null);
  assert.ok(p < 0.01);
});

test("binomExactTwoSided is symmetric at p0=0.5", () => {
  assert.ok(binomExactTwoSided(5, 10, 0.5) > 0.9);
});
