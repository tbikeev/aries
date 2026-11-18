# OHLC 2026-11-17 gap trace — read-only

**Audit window:** 2026-11-18 ~09:58–10:15 CET (Europe/Brussels)  
**Question:** After prod catch-up through watermark batch `20261117T072648Z…` (~09:53 CET stall trace), why `max(trading_date)=2026-11-16` and **0** rows for `2026-11-17` while batches **SUCCEEDED**?  
**Scope:** Read-only — no restarts, config, ingest reruns, S3 uploads, or SQL writes.

---

## Executive answer

**Best hypothesis (high confidence): normal publish/session lag — not a prod filter bug, not an empty ingest failure.**

Production ingestion succeeded on the **publish batch** whose calendar id is `2026-11-17`, but that batch’s S3 `eod_adjusted_close.csv.gz` contained **no rows with `date=2026-11-17`** (max bar date **2026-11-16** only). The **2026-11-17 US session** is present only in the **next** nightly publish (`20261118T084402Z…`, raw uploaded **09:44 CET**), which prod ingested at **~09:56 CET** — **after** the ~09:53 snapshot. Watermark `last_source_created_at` tracks **receipt / manifest publish time**, not `max(trading_date)` in the file.

**At trace end (~10:15 CET re-query):** prod and staging both show **`count(trading_date=2026-11-17)=3783`**, `max(trading_date)=2026-11-17`.

---

## A. Source artifacts (17 Nov OHLC)

### DS425 nightly timing (CET)

| Night | `batch_id` | Local end | `prices_rows` (manifest) |
|-------|------------|-----------|--------------------------|
| 2026-11-17 | `20261117T072648Z-c6fca6e81066` | **08:26:51** | 19,081 |
| 2026-11-18 | `20261118T084402Z-e425f261a972` | **09:44:07** | (same order of magnitude) |

Nightly sequence (Nov 17 log): DSM start **02:15 CET** → `eodhd_ohlc_bulk` until **~05:54 CET** → `finance-export 7d` → S3 upload **08:26 CET**.

Nov 18 log shows OHLC bulk still ingesting `last=2026-11-16->2026-11-17` through **~07:07 CET** before export — consistent with **Tuesday 17 Nov US close** landing in the **18 Nov** publish, not the **17 Nov** publish.

Publisher mode: `finance-export.sh 7d` → `finance_export publish --mode 7d` (last **7 calendar days** of price rows, not “through yesterday’s session” keyed to batch id).

### S3 `eod_adjusted_close.csv.gz` — row counts by `date` column

Sampled read-only from prod worker (S3 get + gzip parse):

| Publish batch | `distinct_dates` | `max(date)` | rows `2026-11-16` | rows `2026-11-17` |
|---------------|------------------|-------------|-------------------|-------------------|
| `20261117T072648Z…` | 5 | **2026-11-16** | **3812** | **0** |
| `20261118T084402Z…` | 5 | **2026-11-17** | 3812 | **3810** |

**Conclusion (A):** Batch id / folder date **2026/11/17** names **when DS425 published**, not the latest **trading_date** inside the delta. **17 Nov session** appears in **18 Nov** raw object.

---

## B. Ingest behavior

### Code path (`/srv/app` on prod worker, issue #343)

- **No “drop future dates” or “drop today” filter** in `finance_ingestion/daily_prices.py` — PostgreSQL COPY + `pg_input_is_valid` on `date`; merge is `delta_upsert` on `(source, instrument_id, trading_date)`.
- `csv_parse.validate_daily_price_row` parses ISO dates via `date.fromisoformat`; quarantine is unresolved symbols only.

### Prod batches (ingestion_batches)

| `batch_id` | `status` | `created_at` (UTC) |
|------------|----------|---------------------|
| `20261117T072648Z-c6fca6e81066` | SUCCEEDED | 2026-11-18 08:40:51+00 (~09:40 CET) |
| `20261118T084402Z-e425f261a972` | SUCCEEDED | 2026-11-18 08:55:50+00 (~09:55 CET) |

### Worker merge logs (UTC → CET +1)

| Batch | `inserted` | `updated` | Interpretation |
|-------|------------|-----------|----------------|
| `20261117T…` | **3785** | 97 | New bars for **2026-11-16** session (matches ~3785 row count in DB for that date) |
| `20261118T…` | **3783** | 44 | New bars for **2026-11-17** session |

### SQL: which batch owns which `trading_date`

```text
 batch_id                     | trading_date | count
------------------------------+--------------+-------
 20261117T072648Z-c6fca6e81066 | 2026-11-16   |  3741
 20261118T084402Z-e425f261a972 | 2026-11-16   |    44  (late corrections)
 20261118T084402Z-e425f261a972 | 2026-11-17   |  3783
```

### Why ~09:53 CET looked “wrong”

Stall trace at **~09:53 CET** completed catch-up through validated receipt **`20261117T…`** (watermark `2026-11-17 07:26:48+00`). Receipt **`20261118T…`** was validated on staging **~09:46 CET** and prod-imported **~09:56 CET**. Between those times:

- All ingested batches **SUCCEEDED** ✓  
- `max(trading_date)` correctly reflected **file contents** of ingested batches only → **2026-11-16** ✓  
- **`2026-11-17` not missing due to failure** — simply **not yet published or ingested**

---

## C. Staging vs prod

| Env | `max(trading_date)` | `count` for `2026-11-17` |
|-----|---------------------|---------------------------|
| **a1-second (prod)** | **2026-11-17** (re-query ~10:15 CET) | **3783** |
| **a1-ts (staging)** | **2026-11-17** | **3783** |

Gap was **identical upstream semantics** (same S3 deltas), not prod-only filtering. Earlier identical `max=2026-11-02` on both envs was the **validator ENOSPC stall** (separate incident; see `finance-feed-stall-trace-2026-11-18.md`).

---

## D. Conclusion and proposed fix (NOT applied)

| Hypothesis | Verdict |
|------------|---------|
| Normal lag (session in **next** publish) | **Selected** — S3 proof: 17 Nov publish has 0× `2026-11-17` rows; 18 Nov publish has 3810× |
| Prod bug / date filter | **Rejected** — code + batch attribution |
| Empty delta / ingest failure | **Rejected** — 19k staged rows; `inserted=3785` on 17 Nov batch for prior session |
| Misread watermark | **Contributing** — watermark batch date ≠ `max(trading_date)` |

### Proposed improvements (Thomas approval only)

1. **Monitoring:** alert on `max(trading_date)` lag vs US session calendar **and** on gap between watermark batch date and `max(trading_date)` > 1 session (expected ~1 day after Brussels morning catch-up).
2. **Runbook / dashboard:** document that DS425 nightly (~02:15–09:45 CET) means **Tuesday close** appears in DB **Wednesday late morning CET** after `20261118T…`-class batch.
3. **Optional product:** freshness API could expose `max(trading_date)` and last `ingestion_batch_id` separately from watermark.
4. **No action** required for 2026-11-17 once `20261118T…` ingested — already healed by **~09:56 CET**.

### Needs Thomas

- None for credentials — investigation used existing SSH + container env.
- Approve only if you want monitoring/runbook changes above.

---

## Evidence index

| Time (CET) | Host | Action |
|------------|------|--------|
| ~10:00 | DS425 | `nightly_2026-11-17` / `18` logs; `finance-export.sh` |
| ~10:00 | prod | Worker logs `daily_price merge`; S3 date histogram; SQL batch↔date map |
| ~10:05 | staging | `max(trading_date)`, Nov 17 count |

**Related:**

- `/Volumes/OWC Aura Pro X2/Users/thomasbikeev/Projects/aries/sa_app/internal/finance-feed-stall-trace-2026-11-18.md`

---

*Read-only audit. No configuration or data paths were modified.*