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
  buildRetCc0Lookup,
  listingIsoDateFromRow,
  formatPerformancePct,
  summarizeSearchPerformance,
  binomExactTwoSided,
  ohlcCloseDateSpan,
} = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);

test("parseSearchOhlcFile accepts listok-style JSON", () => {
  const payload = JSON.stringify([
    { date: "2024-01-01", close: 100 },
    { date: "2024-01-02", close: 110 },
  ]);
  const result = parseSearchOhlcFile("btc.json", payload);
  assert.equal(result.ok, true);
  assert.deepEqual(result.series.closes["2024-01-02"], 110);
});

test("buildRetCc0Lookup returns log return on listing date", () => {
  const lookup = buildRetCc0Lookup({
    "2024-01-01": 100,
    "2024-01-02": 110,
  });
  const ret = lookup.retCc0("2024-01-02");
  assert.ok(ret !== null);
  assert.ok(Math.abs(ret - Math.log(1.1)) < 1e-9);
  assert.equal(lookup.retCc0("2024-01-01"), null);
});

test("listingIsoDateFromRow prefers displayDatetime prefix", () => {
  assert.equal(listingIsoDateFromRow("2025-03-14T12:00:00Z", "14/03/2025"), "2025-03-14");
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
  const lookup = buildRetCc0Lookup({
    "2024-01-01": 100,
    "2024-01-02": 110,
    "2024-01-03": 105,
  });
  const summary = summarizeSearchPerformance(
    [
      { displayDatetime: "2024-01-02T12:00:00Z", displayDate: "2024-01-02" },
      { displayDatetime: "2024-01-03T12:00:00Z", displayDate: "2024-01-03" },
    ],
    lookup,
    "2024-01-01",
    "2024-01-03",
  );
  assert.equal(summary?.nPos, 1);
  assert.equal(summary?.nNeg, 1);
  assert.equal(summary?.eventsWithReturn, 2);
});

test("binomExactTwoSided is symmetric at p0=0.5", () => {
  assert.ok(binomExactTwoSided(5, 10, 0.5) > 0.9);
});
