// Copyright (C) 2026 Max Lange
// SPDX-License-Identifier: AGPL-3.0-or-later

/** Daily OHLC series for optional Search performance column (listing-date ret_cc0). */

export type SearchOhlcSeries = {
  fileName: string;
  /** ISO calendar date YYYY-MM-DD → close price */
  closes: Record<string, number>;
};

export type SearchOhlcParseResult =
  | { ok: true; series: SearchOhlcSeries }
  | { ok: false; error: string };

export type SearchPerformanceLookup = {
  /** Log close-to-close return on listing date, or null if unknown */
  retCc0: (isoDate: string) => number | null;
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

export function buildRetCc0Lookup(closes: Record<string, number> | null | undefined): SearchPerformanceLookup {
  if (!closes) {
    return { retCc0: () => null };
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
  };
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
