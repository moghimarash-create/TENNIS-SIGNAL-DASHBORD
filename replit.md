# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.

## Calculation Pipeline (calc-dashboard + api-server)

Six-step orchestrator that runs Google-Sheets-backed Python calculations sequentially.

**Architecture:**
- `artifacts/api-server` exposes REST endpoints (`/api/steps`, `/api/steps/{id}/run`, `/api/steps/run-all`, `/api/steps/{id}/logs`) and spawns Python subprocesses.
- Python scripts live in `artifacts/api-server/python/`. Each emits a final `__RESULT__ {json}` line consumed by `step-runner.ts`.
- Per-step state persists to `artifacts/api-server/data/dashboard_state.json` (atomic temp+rename, serialized via in-process mutex). Per-step logs stored at `artifacts/api-server/logs/step{N}.log`.
- `artifacts/calc-dashboard` is the React UI: status badges, sheet links, Run / Run-All, expandable logs, 2-second polling.

**Steps (all IMPLEMENTED):**
1. Geomantic Calculator — F/F2/F3 from DEG1-3 + DayNumber/DigitalSum, writes Astro_Input + Astro_Header_Input (~3,905 rows).
2. Astro Aspects (pyswisseph) — 12 planets × 24 aspects, Sun/Moon orb bonus; writes ~50,765 rows to Aspects/Sheet1. Downloads `seas_18.se1` ephemeris to `/tmp` on first run.
3. Result Degree (port of `process.js`) — 4-phase processor (per-row → strongest aspect per day → Node aggregation → 34-col output). Writes Sheet1 (50,765 rows + ~45k color formats chunked at 1k/batch) and Node_Output (~3,905 rows). JS-equivalent helpers: `_js_parse_float` (regex prefix), `mod_arcanum` (preserves floats), `get_zodiac_card` (strict-int match).
4. Search Signals — **9-col schema (A:I)** + **progressive-narrowing match (Option B = try-next), applied per market**. **Markets are discovered dynamically at runtime** from the VISIBLE `KEY-MATCH-*` tabs in DATA-SEARCH-KEY: hiding a tab in Google Sheets disables that market, unhiding re-enables it (no code change to add/remove markets). Market code = tab name minus `KEY-MATCH-` prefix; hidden tabs skipped (`worksheet.properties.hidden`); 0 visible tabs → Step 4 aborts with "No visible KEY-MATCH-* tabs found. Unhide at least one to run Step 4." The dynamic `MARKETS` list cascades everywhere — search loop, FINAL-SIGNAL banner, PREDICTION-FINAL columns, per-market vote counts, dashboard counts. ETH retired; the historical default set is BTC, DJIA, NAS, SPX but any `KEY-MATCH-<CODE>` tab works. Reads SEARCH-SIGNALS (Sheet1!A2:I) and the visible DATA-SEARCH-KEY tabs (A:I each): cols = `[A=Weekday, B=DATE, C=DAILY PRICE, D=QULITY-FIN-1, E=QULITY-FIN-2, F=ELE-P-1/FIRE, G=ELE-P-2/AIR, H=ELE-P-3/WATER, I=ELE-P-4/EARTH]` (QULITY-DAY-1/2 no longer exist). **Match logic (progressive narrowing, all comparisons case-insensitive + trimmed via `norm()`):** the mandatory **base/floor** is `DAY (A) + QULITY-FIN-1 (D) + QULITY-FIN-2 (E)` — built by `base_key3()`; **DAY/weekday is a MATCH KEY again** (reverted from display-only). A DB row is dropped (unmatchable) if any of A/D/E is blank; forward rows with a blank in A/D/E are skipped. If the base yields **< 3** matches, return whatever it has (0/1/2 rows) — no NO-MATCH floor, no narrowing. If the base yields **>= 3**, narrow but **never below 3**, adding element cols on top of the LAST ACCEPTED set: **Stage 2** adds ELE-P-1 (F) + ELE-P-2 (G); **Stage 3** adds ELE-P-3 (H); **Stage 4** adds ELE-P-4 (I). After each stage keep the narrowed set only if it still has >= 3 rows; otherwise **skip that stage's criteria (Option B) but still attempt later stages**. Once the accepted set reaches the floor of 3, narrowing stops. Element-column comparison is exact-equality on the normalized value. 0 base matches across all markets → single `NO MATCH` row. Historical-only cutoff: search-DB rows must have date strictly before earliest forward search date. **Match-depth scoring** (cols M:O on the per-day summary banner row): per matched history row `match_weight = 1 + count of ELE-P cols equal to the forward day`, `direction = sign(PRICE)`, `day_score = match_weight * direction * geo_mult`. **Geomantic signal multiplier:** each matched row's `day_score` is scaled by `GEO_SIGNAL_MAP.get((figure, quadrant), 1.0)` where figure = `figure_from_elements()` of the row's ELE-P ints (4-bit parity → 16 geomancy figures) and quadrant = `mazzaj_quadrant()` from QF1 cold-number + QF2 humoral label (MELANCHOLIC/PHLEGMATIC/CHOLERIC/SANGUINE). The 4 notable combos boost/cut weight: Albus/SANGUINE 1.20, Acquisitio/PHLEGMATIC 1.15, Acquisitio/MELANCHOLIC 1.10, Conjunctio/PHLEGMATIC 0.85; all others 1.0 (so non-notable rows score exactly as before). The geo multiplier only re-weights scores — it never changes which rows match, so the match-set verification is unaffected. Writes FINAL-SIGNAL (**18-col A:R**: data rows fill A=MARKET, B=DAY/LABEL = display-only weekday (no tag), C=DATE, D=PRICE, E=QULITY-FIN-1, F=QULITY-FIN-2, G–J=ELE-P-1..4, K=FWD-DATE-SCORED, L=PER-MARKET-COUNT on the first row of each market block; per-day summary banner row also carries M=SCORE, N=SCORE-OVERALL, O=SCORE-CONF; **P=GEO-FIG is now per-row** (display-only, never affects matching/counts/scores): each matched data row carries ITS OWN figure via `_row_figure()` = `figure_from_elements()` of that row's ELE-P-1..4 (cols G:J); the yellow SEARCH-KEY row carries `"KEY: <fwd_figure>"` (the search day's own figure, labeled); the per-day summary banner row carries `"<fwd_figure> | FIG: nB/mb"` = forward day's figure PLUS a bullish/bearish tally of its matched rows (BULLISH={Albus,Acquisitio,Laetitia,Fortuna_Major}, BEARISH={Conjunctio,Amissio,Tristitia,Cauda_Draconis,Carcer}, all else neutral; sets in `BULLISH_FIGURES`/`BEARISH_FIGURES`). **Q=GEO-FIG-NUM is per-row** (display-only, never affects matching/counts/scores): the 0-15 binary index of the SAME (fire,air,water,earth) parity tuple used for GEO-FIG, with FIRE as the most-significant bit = `fire*8 + air*4 + water*2 + earth*1` (Populus→0, Via→15, Caput_Draconis→7, Cauda_Draconis→14), via `figure_num_from_elements()`/`_row_figure_num()`; each data row carries its own row's num, the SEARCH-KEY row carries the forward day's num, the banner row carries the forward day's num — always bijective with the GEO-FIG figure on that row. **R=ELEM-TRIGGER is PER MARKET** (display-only for the col R text itself; never affects matching/SCORE/GEO-FIG, but it now DRIVES the Overall verdict — see "Overall verdict" below): on the per-day summary banner row only, `detect_element_trigger()` runs SEPARATELY on EACH market's matched rows. For one market it finds the ONE element (FIRE=G, AIR=H, WATER=I, EARTH=J) whose PURE values (>=2 rows all sharing one price direction; FLAT/0-price rows ignored) best separate UP vs DOWN; tiebreak = most rows covered, then EARTH>WATER>AIR>FIRE (`TRIGGER_PRIORITY`). Col R joins each market-with-rows (in `MARKETS` order) with `" | "` via `build_block_trigger_text()` → `format_trigger_compact()`, e.g. `'BTC EARTH:2->DOWN(2/2),1->UP(2/2) | DJIA EARTH:1->DOWN(3/3) | NAS none | SPX none'`; a market with rows but no pure trigger shows `'<MKT> none'`; single-market blocks show just that one; no-match days leave R empty. **The exact same `build_block_trigger_text(matched, MARKETS)` is the single source of truth for BOTH the step4 write path AND the verify_logic recompute** (no format/ordering drift). The winning element's cell is GREEN-highlighted (`GREEN_HL`) on each market's own pure-trigger matched rows. All rows padded to 18-col A:R (`FINAL_COLS=18`). verify_logic.py parses the banner figure as the token before `" |"`, and checks per-row figures across ALL market data rows, the SEARCH-KEY `KEY:` figure, and (DJIA-only) the tally; it also verifies GEO-FIG-NUM (col Q) equals the binary index of each row's GEO-FIG figure AND that figure↔num is bijective across all rows; it also recomputes col R per market from the sheet's own rows (grouped by fwd-date AND market, market order = first-appearance = step4 write order) and asserts Wed 5/27/2026 BTC = `EARTH:2->DOWN(2/2),1->UP(2/2)`; it ALSO independently recomputes the HYBRID Overall (banner D/E/F): count-based DIRECTION+CONFIDENCE via the shared `count_block_overall`, plus the element-trigger verdict via the shared `element_trigger_overall` + the 3-state `agreement_label`, all from the sheet's own matched rows + each block's SEARCH-KEY forward elements, and asserts 5/12/2026 Overall = UP, 5/15/2026 Overall = UP (pooled 12u/6d), and 3/27/2026 Overall = DOWN + agreement label = CONFIRMED; permanent header row 1, yellow SEARCH-KEY row + colored per-day separator; separator banner label includes `[MATCH]` / `[NO MATCH]` tag). **Overall verdict (banner D=`Overall:`, E=`Conf:`, F=`Agree:`; PREDICTION-FINAL OVERALL_SIGNAL/_CONF + AGREEMENT) is HYBRID** — count-based DIRECTION + CONFIDENCE, annotated with a 3-state element-trigger AGREEMENT label: **(1) DIRECTION (D)** is the ORIGINAL count-of-up-vs-down majority pooled across ALL active markets' matched rows (per market `dn` = rows with a NEGATIVE price (cell starts with `-`), `up` = all other rows so FLAT/0 counts as up): `UP` if `total_up > total_dn`, `DOWN` if `total_dn > total_up`, `NEUTRAL` ONLY on a TRUE count tie — it is NEVER forced NEUTRAL just because the element trigger is silent. **(2) CONFIDENCE (E)** = `max(total_up, total_dn) / total_matches × 100`. **(3) AGREEMENT (F) is a 3-state LABEL** (its own column, in the slot the old numeric `n/m` agreement occupied — no column shift needed): it compares the element-trigger verdict (`element_trigger_overall`, the per-market most-rows-covered pure-element vote combined by market majority → `elem_dir` ∈ {UP,DOWN,NEUTRAL}) to the COUNT direction via `agreement_label()` — `CONFIRMED` (elem_dir == count dir), `SILENT` (elem_dir == NEUTRAL: no pure signal / no matching forward value / market tie), `CONFLICT` (elem_dir is directional but differs, incl. count = NEUTRAL tie). The label NEVER overrides the direction; the element-trigger computation is kept ONLY to drive this label. `count_block_overall()` + `agreement_label()` (DIRECTION/CONFIDENCE/label) and `element_trigger_overall()` (elem_dir) in step4 are the single source of truth shared with verify_logic. Match-depth SCORE / SCORE-OVERALL / SCORE-CONF (cols M/N/O) are UNCHANGED and fully independent of this verdict. + PREDICTION-FINAL (**dynamic width** = 3 fixed cols + 5 per active market + 7 summary; `<MARKET>_MATCHES/_UP/_DOWN/_SIGNAL/_CONF` columns generated only for visible markets, col C = `QUALITY_SIG`; summary tail ends `SCORE, SCORE_OVERALL, SCORE_CONF, GEO_FIG`; AGREEMENT is the 3-state element-trigger label (`CONFIRMED`/`SILENT`/`CONFLICT`); OVERALL_SIGNAL suffix: unsuffixed for match days, ` (NM)` for no-match days). PREDICTION-FINAL is built from in-memory results, not by re-parsing FINAL-SIGNAL col B. **Dashboard per-market checkboxes:** each `KEY-MATCH-*` input on the Step 4 card has an enable/disable checkbox (checked by default; state persisted in localStorage key `calc-dashboard.disabledMarkets`). Unchecking sends an **exclusion** list to the run endpoint (`POST /steps/{id}/run` body `{ disabledMarkets: string[] }` → Python flag `--disabled-markets <csv>`); active set = **visible − disabled**, so unknown/new visible tabs still run even while known markets are filtered (omitted/empty ⇒ full dynamic discovery). Disabling every visible market aborts with NO_ENABLED_MARKETS; the dashboard also disables Run when all known markets are unchecked. **Formatting gid:** FINAL-SIGNAL and PREDICTION-FINAL writes target the `Sheet1` tab, so their `batchUpdate` formatting must resolve the gid by tab name (`get_sheet_gid(id, "Sheet1")`) — resolving to the first sheet breaks when another tab (e.g. Sheet2) is reordered ahead of it ("Range exceeds grid limits" 400). `format_sheet` raises with the API response body so such errors surface their message.
5. BTC ATR — Coinbase daily candles, ATR14 over previous 14 candles (today excluded), writes K/L/I/J atomically in one batch update for today's UTC row.

**Concurrency rules:** single-step runs are rejected (409) while a pipeline is running. Run-All runs 1→5 sequentially, stopping on first error.

**Secrets:** Sheets writes require `GOOGLE_SERVICE_ACCOUNT_JSON` (full JSON value of a service account key). The service account email (currently `geomantic-sheets@kalshi-trade-agent.iam.gserviceaccount.com`) must have Editor access to every input/output spreadsheet listed in `steps-config.ts`. Step 5 supports `--dry-run` to validate without the secret.

**Sheet IDs** are configured in `artifacts/api-server/src/lib/steps-config.ts`.
## LOTTO / 12-HORSE MODE (added 2026-10-12)

The third geomantic point is no longer the DEG3 column. Step 1 reads the **HORSES** tab of
GEOMANTIC-CALCULATER-INPUT (NO | NAME | NUMBER | DEG | SIGN; DEG = NUMBER mod 360 = absolute
0-359 zodiac degree) and emits **12 rows per date** (one per horse): F/F2 from DEG1/DEG2 as before,
F3 = HORSE.DEG + DayNumber + DigitalSum. Every downstream table carries the horse tag:
Astro_Input J:K, Astro_Header_Input F:G, Aspects G:H, Result Degree / Node_Output / WEEKLY-OUTPUT
AI:AJ (36 cols). Step 2 keys blocks by (DATE, HORSE_NO). Step 3 and 3B run the UNCHANGED
processor / weekly grouping once per horse (first-appearance order) and concatenate, with row
offsets so colours and =SUM() weekly formulas stay correct. Calculation formulas were not changed.
Pre-change copies of the 5 edited files: backup_pre_horses_2026-10-12/. Step 4 is untouched.
### Dedicated LOTTO spreadsheets (2026-10-12, later the same day)
Steps 1-3B now point at their own LOTTO-* spreadsheets (all shared with the service account as Editor),
so the original Unified-Calculator sheets are never touched by this app:
- LOTTO-GEOMANTIC-INPUT  1OPmbKcm0QlWph6dtY_oiKXs17gm3ICOMGUJqakr8gLw  (Sheet1 = DATE, PRIC-CH, WEEKDAY, DEG1, DEG2, Time, Zone, Lat, Lon ; HORSES tab)
- LOTTO-Astro_Input      17i6LLr6DjqG0FofADd68V4hg1kKcDRHevFiHSiO4IGg  (tab Data)
- LOTTO-Astro_Header_Input 1VInHih6qtLw7ivxU09Q8Up39hEnWJtzwKoggqZzbbHM (tab Sheet1)
- LOTTO-Aspects          1VdFX7HyZQCYkYPhWDTUewr8UpNKatBL43b4G5L9y6K0  (tab Sheet1)
- LOTTO-Result-Degree    1Gx_6_OG8DF6GNBMVJMC-5mL6hvo0bYuExnIB5mFbgfA  (tabs Sheet1, Node_Output, WEEKLY-OUTPUT)
Verified end-to-end on 14 sample dates: 168 Astro rows, 2184 Aspects rows, 192 Node_Output rows (168 daily + 24 weekly), 24 WEEKLY-OUTPUT rows (2 per horse).
Steps 4 and 5 still use their original market sheets (not part of the lotto chain).
### Date-major output order (2026-10-12, evening)
Result Degree / Node_Output are DATE-MAJOR: for every date the 12 horse blocks / 12 Node rows are
consecutive (horse 1..12), then the next date. After each Monday-Sunday window, 12 WEEKLY rows follow
(one per horse); their live G/H/I formulas are =SUMIF($AI$a:$AI$b, horse_no, Ga:Gb) over that week's
daily block (same per-horse weekly sum as before, just filtered by the horse column because horses are
interleaved). WEEKLY-OUTPUT is week-major too (each week: 12 horse rows, chronological weeks).

### WEEKLY rows removed (2026-10-12, night)
Per user: weekly sums are not needed in the lotto app. Step 3 has WEEKLY_ROWS_ENABLED=False
(env STEP3_WEEKLY_ROWS=1 re-enables), so Node_Output holds only daily Node rows (12 per date, no
yellow rows). The 3B card (step id 6) was removed from steps-config.ts and the WEEKLY-OUTPUT tab was
deleted from LOTTO-Result-Degree; step3b_weekly_output.py is kept on disk but is no longer wired in.
Remaining yellow in Result Degree Sheet1 is part of the original method: AG (numberAG) on Node rows
and the light-yellow K cell marking the day's strongest aspect.

### Location / Time preset (2026-10-12)
Dashboard card "LOCATION / TIME PRESET" above Step 1 (App.tsx LocationPresetPanel). Default preset:
CA Lottery — Sacramento HQ, 38.5915 / -121.4832, 18:30 America/Los_Angeles (Daily Derby draw time;
coordinates are an address-based estimate for 700 N 10th St). "Apply to input sheet" POSTs
/api/preset/apply (routes/preset.ts) -> python/step1_apply_preset.py, which writes Time/Zone/Lat/Lon into
every data row of LOTTO-GEOMANTIC-INPUT (creates the columns if missing). Last applied preset is stored in
artifacts/api-server/data/location_preset.json. Step scripts are unchanged: Step 1 still reads the four
columns per row; Step 2 converts local time -> UTC with pytz (DST-aware).
