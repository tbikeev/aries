// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

/** Daily OHLC series for optional Search performance column (forward return from transit day close). */

export const SEARCH_PERFORMANCE_HORIZONS = [1, 3, 7] as const;
export type SearchPerformanceHorizonDays = (typeof SEARCH_PERFORMANCE_HORIZONS)[number];

export function parseSearchPerformanceHorizonDays(value: unknown): SearchPerformanceHorizonDays {
  if (value === 3 || value === 7) return value;
  return 1;
}

export type SearchOhlcSeries = {
  fileName: string;
  /** ISO calendar date YYYY-MM-DD → close price */
  closes: Record<string, number>;
};

export type OhlcCloseDateSpan = {
  fromDate: string;
  toDate: string;
  dayCount: number;
};

export type SearchOhlcParseResult =
  | { ok: true; series: SearchOhlcSeries }
  | { ok: false; error: string };

export type SearchPerformanceLookup = {
  horizonDays: SearchPerformanceHorizonDays;
  /** Log return from close on event day to close N trading sessions later. */
  returnForEventDay: (anchorIsoDate: string) => number | null;
  /** Positive-day rate among forward returns in [fromIso, toIso] (search baseline). */
  baselinePosRateBetween: (fromIso: string, toIso: string) => { rate: number; days: number };
  /** Mean log return and day count in [fromIso, toIso]. */
  baselineMeanReturnBetween: (fromIso: string, toIso: string) => { mean: number; days: number };
  /** Forward returns on non-hit anchor days within [fromIso, toIso]. */
  controlReturnsBetween: (
    fromIso: string,
    toIso: string,
    hitIsoDates: ReadonlySet<string>,
  ) => number[];
};

export type SearchListingRow = {
  displayDatetime: string;
  displayDate: string;
};

export type SearchPerformanceSummary = {
  eventsWithReturn: number;
  nPos: number;
  nNeg: number;
  nZero: number;
  /** Share of pos / neg among events with a return (percent). */
  posSharePct: number;
  negSharePct: number;
  /** Sum of listing-day log-return % on up / down events. */
  sumPosPct: number;
  sumNegPct: number;
  pBinomTwoSided: number;
  baselinePosPct: number;
  baselineDays: number;
  /** Unique hit calendar days with a return. */
  hitReturnDays: number;
  /** Mean log return on hit days (unique dates). */
  hitMeanReturn: number;
  /** Mean log return on all OHLC days in the search span. */
  baselineMeanReturn: number;
  /** hitMeanReturn − baselineMeanReturn, as log-return percent points. */
  excessMeanPct: number;
  /** Two-sided Mann–Whitney p: hit-day returns vs other days in span. */
  pReturnTwoSided: number | null;
  controlReturnDays: number;
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function normalizeIsoDate(raw: string): string | null {
  const token = raw.trim();
  if (ISO_DATE.test(token)) return token;
  const match = token.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function readClose(row: Record<string, unknown>): number | null {
  for (const key of ["close", "price", "c", "Close", "adjclose", "adj_close"]) {
    const value = row[key];
    if (typeof value === "number" && Number.isFinite(value) && value > 0) return value;
    if (typeof value === "string") {
      const parsed = Number(value);
      if (Number.isFinite(parsed) && parsed > 0) return parsed;
    }
  }
  return null;
}

function rowsFromJson(value: unknown): Record<string, unknown>[] | null {
  if (Array.isArray(value)) {
    return value.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
  }
  if (value && typeof value === "object") {
    const container = value as Record<string, unknown>;
    for (const key of ["rows", "data", "quotes", "prices"]) {
      const nested = container[key];
      if (Array.isArray(nested)) {
        return nested.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
      }
    }
  }
  return null;
}

function parseCsv(text: string): Record<string, unknown>[] {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2) return [];
  const header = lines[0].split(",").map((cell) => cell.trim().toLowerCase());
  const dateIndex = header.findIndex((cell) => cell === "date" || cell === "day");
  const closeIndex = header.findIndex((cell) => cell === "close" || cell === "price" || cell === "adj close" || cell === "adjclose");
  if (dateIndex < 0 || closeIndex < 0) return [];
  const rows: Record<string, unknown>[] = [];
  for (const line of lines.slice(1)) {
    const cells = line.split(",").map((cell) => cell.trim());
    rows.push({ date: cells[dateIndex], close: cells[closeIndex] });
  }
  return rows;
}

export function ohlcCloseDateSpan(closes: Record<string, number> | null | undefined): OhlcCloseDateSpan | null {
  if (!closes) return null;
  const dates = Object.keys(closes).filter((key) => ISO_DATE.test(key)).sort();
  if (dates.length < 2) return null;
  const fromDate = dates[0];
  const toDate = dates[dates.length - 1];
  return { fromDate, toDate, dayCount: dates.length };
}

export function parseSearchOhlcFile(fileName: string, text: string): SearchOhlcParseResult {
  const trimmed = text.trim();
  if (!trimmed) {
    return { ok: false, error: "empty_file" };
  }
  let rows: Record<string, unknown>[] | null = null;
  if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
    try {
      rows = rowsFromJson(JSON.parse(trimmed));
    } catch {
      return { ok: false, error: "invalid_json" };
    }
  } else {
    rows = parseCsv(trimmed);
  }
  if (!rows?.length) {
    return { ok: false, error: "no_rows" };
  }
  const closes: Record<string, number> = {};
  for (const row of rows) {
    const dateRaw = row.date ?? row.Date ?? row.timestamp ?? row.time;
    if (typeof dateRaw !== "string" && typeof dateRaw !== "number") continue;
    const iso = normalizeIsoDate(String(dateRaw));
    if (!iso) continue;
    const close = readClose(row);
    if (close === null) continue;
    closes[iso] = close;
  }
  if (Object.keys(closes).length < 2) {
    return { ok: false, error: "insufficient_closes" };
  }
  return { ok: true, series: { fileName, closes } };
}

function binomPmf(k: number, n: number, p: number): number {
  if (k < 0 || k > n) return 0;
  if (p <= 0) return k === 0 ? 1 : 0;
  if (p >= 1) return k === n ? 1 : 0;
  let coeff = 1;
  for (let index = 1; index <= k; index += 1) {
    coeff = (coeff * (n - k + index)) / index;
  }
  return coeff * p ** k * (1 - p) ** (n - k);
}

export function binomExactTwoSided(kPos: number, n: number, p0: number): number {
  if (n <= 0) return 1;
  const target = binomPmf(kPos, n, p0);
  let total = 0;
  for (let hits = 0; hits <= n; hits += 1) {
    const prob = binomPmf(hits, n, p0);
    if (prob <= target + 1e-15) total += prob;
  }
  return Math.min(1, total);
}

function rangeBounds(fromIso: string, toIso: string): { from: string; to: string } {
  return fromIso <= toIso ? { from: fromIso, to: toIso } : { from: toIso, to: fromIso };
}

function returnsInRange(retByDate: Map<string, number>, fromIso: string, toIso: string): number[] {
  const { from, to } = rangeBounds(fromIso, toIso);
  const values: number[] = [];
  for (const [day, ret] of retByDate) {
    if (day < from || day > to) continue;
    values.push(ret);
  }
  return values;
}

function meanReturn(values: readonly number[]): number {
  if (values.length === 0) return 0;
  let sum = 0;
  for (const value of values) sum += value;
  return sum / values.length;
}

function baselinePosRateBetween(
  retByDate: Map<string, number>,
  fromIso: string,
  toIso: string,
): { rate: number; days: number } {
  const values = returnsInRange(retByDate, fromIso, toIso);
  let positive = 0;
  for (const ret of values) {
    if (ret > 0) positive += 1;
  }
  const days = values.length;
  return { rate: days > 0 ? positive / days : 0.5, days };
}

function controlReturnsInRange(
  retByDate: Map<string, number>,
  fromIso: string,
  toIso: string,
  hitIsoDates: ReadonlySet<string>,
): number[] {
  const { from, to } = rangeBounds(fromIso, toIso);
  const values: number[] = [];
  for (const [day, ret] of retByDate) {
    if (day < from || day > to) continue;
    if (hitIsoDates.has(day)) continue;
    values.push(ret);
  }
  return values;
}

function rankWithTies(values: readonly number[]): number[] {
  const indexed = values.map((value, index) => ({ value, index }));
  indexed.sort((left, right) => left.value - right.value);
  const ranks = new Array<number>(values.length);
  let position = 0;
  while (position < indexed.length) {
    let end = position + 1;
    while (end < indexed.length && indexed[end].value === indexed[position].value) end += 1;
    const averageRank = (position + 1 + end) / 2;
    for (let cursor = position; cursor < end; cursor += 1) {
      ranks[indexed[cursor].index] = averageRank;
    }
    position = end;
  }
  return ranks;
}

function normalCdf(z: number): number {
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const d = 0.3989423 * Math.exp((-z * z) / 2);
  const probability =
    d
    * t
    * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
  return z > 0 ? 1 - probability : probability;
}

/** Two-sided Mann–Whitney U (normal approximation, tie-averaged ranks). */
export function mannWhitneyTwoSidedP(sampleA: readonly number[], sampleB: readonly number[]): number | null {
  const n1 = sampleA.length;
  const n2 = sampleB.length;
  if (n1 === 0 || n2 === 0) return null;
  const combined = [...sampleA, ...sampleB];
  const ranks = rankWithTies(combined);
  let rankSumA = 0;
  for (let index = 0; index < n1; index += 1) rankSumA += ranks[index];
  const u1 = rankSumA - (n1 * (n1 + 1)) / 2;
  const u = Math.min(u1, n1 * n2 - u1);
  const meanU = (n1 * n2) / 2;
  const sigmaU = Math.sqrt((n1 * n2 * (n1 + n2 + 1)) / 12);
  if (sigmaU === 0) return 1;
  const z = (u - meanU) / sigmaU;
  const p = 2 * (1 - normalCdf(Math.abs(z)));
  return Math.min(1, Math.max(0, p));
}

export const SEARCH_PERF_ANOMALY_P = 0.05;
export const SEARCH_PERF_MIN_COUNT_EVENTS = 5;
export const SEARCH_PERF_MIN_BASELINE_DAYS = 10;
export const SEARCH_PERF_MIN_HIT_RETURN_DAYS = 3;
export const SEARCH_PERF_MIN_CONTROL_RETURN_DAYS = 10;

export function searchPerformanceAnomalies(summary: SearchPerformanceSummary): {
  count: boolean;
  return: boolean;
} {
  const classified = summary.nPos + summary.nNeg + summary.nZero;
  const count =
    classified >= SEARCH_PERF_MIN_COUNT_EVENTS
    && summary.baselineDays >= SEARCH_PERF_MIN_BASELINE_DAYS
    && summary.pBinomTwoSided <= SEARCH_PERF_ANOMALY_P;
  const returnAnomaly =
    summary.pReturnTwoSided !== null
    && summary.hitReturnDays >= SEARCH_PERF_MIN_HIT_RETURN_DAYS
    && summary.controlReturnDays >= SEARCH_PERF_MIN_CONTROL_RETURN_DAYS
    && summary.pReturnTwoSided <= SEARCH_PERF_ANOMALY_P;
  return { count, return: returnAnomaly };
}

function buildForwardReturnByAnchor(
  closes: Record<string, number>,
  horizonDays: SearchPerformanceHorizonDays,
): Map<string, number> {
  const dates = Object.keys(closes).filter((key) => ISO_DATE.test(key)).sort();
  const retByAnchor = new Map<string, number>();
  for (let index = 0; index < dates.length; index += 1) {
    const endIndex = index + horizonDays;
    if (endIndex >= dates.length) continue;
    const p0 = closes[dates[index]];
    const p1 = closes[dates[endIndex]];
    if (p0 > 0 && p1 > 0) {
      retByAnchor.set(dates[index], Math.log(p1 / p0));
    }
  }
  return retByAnchor;
}

export function buildSearchPerformanceLookup(
  closes: Record<string, number> | null | undefined,
  horizonDays: SearchPerformanceHorizonDays = 1,
): SearchPerformanceLookup {
  const emptyBaseline = () => ({ rate: 0.5, days: 0 });
  const emptyMean = () => ({ mean: 0, days: 0 });
  if (!closes) {
    return {
      horizonDays,
      returnForEventDay: () => null,
      baselinePosRateBetween: emptyBaseline,
      baselineMeanReturnBetween: emptyMean,
      controlReturnsBetween: () => [],
    };
  }
  const retByDate = buildForwardReturnByAnchor(closes, horizonDays);
  return {
    horizonDays,
    returnForEventDay: (isoDate: string) => retByDate.get(isoDate) ?? null,
    baselinePosRateBetween: (fromIso, toIso) => baselinePosRateBetween(retByDate, fromIso, toIso),
    baselineMeanReturnBetween: (fromIso, toIso) => {
      const values = returnsInRange(retByDate, fromIso, toIso);
      return { mean: meanReturn(values), days: values.length };
    },
    controlReturnsBetween: (fromIso, toIso, hitIsoDates) =>
      controlReturnsInRange(retByDate, fromIso, toIso, hitIsoDates),
  };
}

/** @deprecated Use buildSearchPerformanceLookup */
export function buildRetCc0Lookup(closes: Record<string, number> | null | undefined): SearchPerformanceLookup {
  return buildSearchPerformanceLookup(closes, 1);
}

export function summarizeSearchPerformance(
  rows: readonly SearchListingRow[],
  lookup: SearchPerformanceLookup,
  baselineFromIso: string,
  baselineToIso: string,
): SearchPerformanceSummary | null {
  const returns: number[] = [];
  for (const row of rows) {
    const iso = listingIsoDateFromRow(row.displayDatetime, row.displayDate);
    if (!iso) continue;
    const ret = lookup.returnForEventDay(iso);
    if (ret !== null) returns.push(ret);
  }
  if (returns.length === 0) return null;

  let nPos = 0;
  let nNeg = 0;
  let nZero = 0;
  let sumPosPct = 0;
  let sumNegPct = 0;
  for (const ret of returns) {
    const pct = ret * 100;
    if (ret > 0) {
      nPos += 1;
      sumPosPct += pct;
    } else if (ret < 0) {
      nNeg += 1;
      sumNegPct += pct;
    } else {
      nZero += 1;
    }
  }
  const n = returns.length;
  const { rate: baselinePos, days: baselineDays } = lookup.baselinePosRateBetween(
    baselineFromIso,
    baselineToIso,
  );
  const classified = nPos + nNeg + nZero;
  const posSharePct = classified > 0 ? (100 * nPos) / classified : 0;
  const negSharePct = classified > 0 ? (100 * nNeg) / classified : 0;

  const hitReturnByDay = new Map<string, number>();
  for (const row of rows) {
    const iso = listingIsoDateFromRow(row.displayDatetime, row.displayDate);
    if (!iso) continue;
    const ret = lookup.returnForEventDay(iso);
    if (ret !== null) hitReturnByDay.set(iso, ret);
  }
  const hitReturnDaysList = [...hitReturnByDay.values()];
  const hitIsoDates = new Set(hitReturnByDay.keys());
  const { mean: baselineMeanReturn } = lookup.baselineMeanReturnBetween(baselineFromIso, baselineToIso);
  const hitMeanReturn = meanReturn(hitReturnDaysList);
  const excessMean = hitMeanReturn - baselineMeanReturn;
  const controlReturns = lookup.controlReturnsBetween(baselineFromIso, baselineToIso, hitIsoDates);

  return {
    eventsWithReturn: n,
    nPos,
    nNeg,
    nZero,
    posSharePct,
    negSharePct,
    sumPosPct,
    sumNegPct,
    pBinomTwoSided: binomExactTwoSided(nPos, classified, baselinePos),
    baselinePosPct: baselinePos * 100,
    baselineDays,
    hitReturnDays: hitReturnDaysList.length,
    hitMeanReturn,
    baselineMeanReturn,
    excessMeanPct: excessMean * 100,
    pReturnTwoSided: mannWhitneyTwoSidedP(hitReturnDaysList, controlReturns),
    controlReturnDays: controlReturns.length,
  };
}

export function formatMeanReturnPct(meanLogReturn: number): string {
  const pct = meanLogReturn * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

export function formatSearchPerformanceSummaryLine(summary: SearchPerformanceSummary): string {
  const posSum = summary.sumPosPct >= 0 ? `+${summary.sumPosPct.toFixed(1)}` : summary.sumPosPct.toFixed(1);
  const negSum = summary.sumNegPct.toFixed(1);
  const excessSign = summary.excessMeanPct > 0 ? "+" : "";
  const returnBlock =
    `μ ${formatMeanReturnPct(summary.hitMeanReturn)} vs ${formatMeanReturnPct(summary.baselineMeanReturn)}`
    + ` · Δ ${excessSign}${summary.excessMeanPct.toFixed(2)}%`
    + (summary.pReturnTwoSided !== null ? ` · pμ=${summary.pReturnTwoSided.toFixed(3)}` : "");
  return (
    `${summary.nPos}+/${summary.nNeg}−`
    + ` · ${summary.posSharePct.toFixed(1)}/${summary.negSharePct.toFixed(1)}%`
    + ` · ∑ ${posSum}/${negSum}%`
    + ` · p=${summary.pBinomTwoSided.toFixed(3)}`
    + ` · ${returnBlock}`
  );
}

export function listingIsoDateFromRow(displayDatetime: string, displayDate: string): string | null {
  const fromIso = displayDatetime?.slice(0, 10);
  if (fromIso && ISO_DATE.test(fromIso)) return fromIso;
  return normalizeIsoDate(displayDate);
}

export function formatPerformancePct(logReturn: number): string {
  const pct = logReturn * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}
