// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

/** Daily OHLC series for optional Search performance column (listing-date ret_cc0). */

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
  /** Log close-to-close return on listing date, or null if unknown */
  retCc0: (isoDate: string) => number | null;
  /** Positive-day rate among all ret_cc0 days in [fromIso, toIso] (search baseline). */
  baselinePosRateBetween: (fromIso: string, toIso: string) => { rate: number; days: number };
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

function baselinePosRateBetween(
  retByDate: Map<string, number>,
  fromIso: string,
  toIso: string,
): { rate: number; days: number } {
  const from = fromIso <= toIso ? fromIso : toIso;
  const to = fromIso <= toIso ? toIso : fromIso;
  let positive = 0;
  let days = 0;
  for (const [day, ret] of retByDate) {
    if (day < from || day > to) continue;
    days += 1;
    if (ret > 0) positive += 1;
  }
  return { rate: days > 0 ? positive / days : 0.5, days };
}

export function buildRetCc0Lookup(closes: Record<string, number> | null | undefined): SearchPerformanceLookup {
  const emptyBaseline = () => ({ rate: 0.5, days: 0 });
  if (!closes) {
    return { retCc0: () => null, baselinePosRateBetween: emptyBaseline };
  }
  const dates = Object.keys(closes).filter((key) => ISO_DATE.test(key)).sort();
  const retByDate = new Map<string, number>();
  for (let index = 1; index < dates.length; index += 1) {
    const prev = dates[index - 1];
    const cur = dates[index];
    const p0 = closes[prev];
    const p1 = closes[cur];
    if (p0 > 0 && p1 > 0) {
      retByDate.set(cur, Math.log(p1 / p0));
    }
  }
  return {
    retCc0: (isoDate: string) => retByDate.get(isoDate) ?? null,
    baselinePosRateBetween: (fromIso, toIso) => baselinePosRateBetween(retByDate, fromIso, toIso),
  };
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
    const ret = lookup.retCc0(iso);
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
  };
}

export function formatSearchPerformanceSummaryLine(summary: SearchPerformanceSummary): string {
  const posSum = summary.sumPosPct >= 0 ? `+${summary.sumPosPct.toFixed(1)}` : summary.sumPosPct.toFixed(1);
  const negSum = summary.sumNegPct.toFixed(1);
  return (
    `${summary.nPos}+/${summary.nNeg}−`
    + ` · ${summary.posSharePct.toFixed(1)}/${summary.negSharePct.toFixed(1)}%`
    + ` · ∑ ${posSum}/${negSum}%`
    + ` · p=${summary.pBinomTwoSided.toFixed(3)}`
  );
}

export function listingIsoDateFromRow(displayDatetime: string, displayDate: string): string | null {
  const fromIso = displayDatetime?.slice(0, 10);
  if (fromIso && ISO_DATE.test(fromIso)) return fromIso;
  return normalizeIsoDate(displayDate);
}

export function formatPerformancePct(retCc0: number): string {
  const pct = retCc0 * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}
