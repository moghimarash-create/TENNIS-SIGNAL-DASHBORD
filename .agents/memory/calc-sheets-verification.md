---
name: Calc-dashboard Google Sheets verification gotchas
description: How to independently verify / diff Step 4 (and similar) outputs written back to Google Sheets without false matches.
---

# Verifying calc-dashboard outputs written to Google Sheets

When re-checking what a step wrote to an output sheet (e.g. Step 4 → FINAL-SIGNAL)
against the raw inputs, **do not compare raw cell strings**.

**Why:** Steps write outputs with `valueInputOption=USER_ENTERED` (raw=False).
Google Sheets re-parses/reformats values on write — dates and numbers come back
displayed differently than the raw input strings they came from. Raw-string diffs
produce spurious discrepancies; date-only diffs produce spurious *agreements* when
two distinct rows share a date.

**How to apply:**
- Normalize before comparing: parse dates with the step's own format list
  (`%m/%d/%Y`, `%m/%d/%y`, `%Y-%m-%d`) and compare as ISO; normalize numbers by
  parsing to float; uppercase+trim text cells.
- Compare a **per-row fingerprint** (date + price + element cols), as a sorted
  multiset per grouping key — not a date-only set.
- Match the step's row-grouping exactly (Step 4 groups output rows by the
  FWD-DATE-SCORED column), and aggregate both sides by that key so duplicate keys
  compare symmetrically.

**Match-rule note (Step 4):** the weekday (DAY, col A) is part of the mandatory
base key, so a historical candidate row dated on a given weekday can ONLY land in
the match set of a forward day with the same weekday. A 1970-era date in a
KEY-MATCH-* tab is a *historical candidate row*, never a forward day (forward days
are the future dates in SEARCH-SIGNALS; the historical cutoff = min forward date).

**verify_logic reads the LIVE sheet, not step4's in-memory output.** Any new
output column (e.g. GEO-FIG) shows up as empty/stale in the verifier until step4 is
**re-run** to rewrite the sheet. Sequence after editing step4 output: run step4
first, THEN run verify_logic — otherwise new-column checks fail with `step4=''`.

**Geo multiplier (GEO_SIGNAL_MAP) re-weights scores only.** It scales each matched
row's `day_score`; it never changes which rows match, so the match-set diff is
inherently unaffected (276/276 stays exact). The verifier's SCORE recompute is
DJIA-only, so it can only strictly compare scores when DJIA is the *sole* active
market — with multiple active markets, step4's SCORE is a multi-market aggregate
and the verifier correctly SKIPS the strict score check (GEO-FIG still verifiable,
it's market-independent).

**Per-row verifier checks must be market-agnostic, not DJIA-hardcoded.** FINAL-SIGNAL
col P (GEO-FIG) is per-row (each matched row carries its own figure from its own
elements). The active market set is dynamic (visible KEY-MATCH-* tabs), so a
verifier filter of `col A == "DJIA"` yields a vacuous 0/0 whenever DJIA isn't
visible. Verify per-row figures across ALL data rows (skip banner `>>>`, SEARCH-KEY,
and `—` NO-MATCH rows) since the figure is computed from a row's OWN elements
regardless of market. Banner col P now reads `"<fig> | FIG: nB/mb"`, SEARCH-KEY col
P reads `"KEY: <fig>"` — parse the figure as the token before `" |"` / after `"KEY:"`.

**ELEM-TRIGGER is the ONE market-AWARE check — group by market, not agnostic.**
Unlike GEO-FIG, the element trigger runs `detect_element_trigger` SEPARATELY per
market within each block, so the verifier must bucket the sheet's matched rows by
(fwd-date, col-A market), preserving first-appearance market order (= step4's
`MARKETS` write order), then recompute. Keep ONE shared builder
(`build_block_trigger_text(matched_by_market, markets)`) imported by BOTH step4
(write path) and verify_logic (recompute) so format/ordering can never drift — do
not re-implement the join string in two places.

**Adding/shifting a FINAL-SIGNAL column = touch ALL of these in lockstep.** The
output schema width is encoded in *several independent literals*, and the data-write
range is a SEPARATE hardcoded literal from the header range — the easy one to miss.
Missing the data range gives a `400 Bad Request ... values/Sheet1!A2:Q<N>` (the
payload is N cols wide but the A1 range says fewer). Checklist when col count
changes: (1) `FINAL_COLS` constant; (2) header `write_sheet(... "Sheet1!A1:<col>1", [[...]])`;
(3) the **data** `write_sheet(... f"Sheet1!A2:<col>{n+1}", rect_output)`; (4) every
row-type append (data row, SEARCH-KEY row, per-day banner row) — insert the new cell
at the right position and shift trailing cells; (5) the over-clear range (kept wide,
e.g. A1:T, so usually fine); (6) format batch `endColumnIndex` (uses `FINAL_COLS`,
auto-OK); (7) in verify_logic: each `read_range(... "Sheet1!A2:<col>")`, each
`pad(r, FINAL_COLS)`, and any hardcoded column index `r[i]` for a SHIFTED column
(e.g. ELEM-TRIGGER moved P→Q→R as cols were inserted before it).

## Shared single-source-of-truth for banner verdicts (Step 4)

Any block-level verdict written to the FINAL-SIGNAL banner / PREDICTION-FINAL
(ELEM-TRIGGER col R, and the element-trigger-driven Overall/Conf/Agree) must be a
**pure function in step4_search_signals.py that verify_logic.py imports and re-runs**
against the sheet's OWN rows.

**Why:** the verifier must be independent of the writer's in-memory state, but the
two cannot be allowed to drift in format/ordering. A shared function gives both: the
write path and the recompute call identical code (e.g. `build_block_trigger_text`,
`element_trigger_overall`). Reparsing/reimplementing in the verifier caused drift.

**How to apply:** when adding/changing a banner verdict, put the logic in step4 as a
function taking sheet-shaped inputs (detector-shaped 9-col rows: idx2=price from sheet
col D, idx5..8=ELE-P-1..4 from sheet cols G:J), import it into verify_logic, and have
the verifier rebuild those inputs from the sheet + each block's SEARCH-KEY row.
The banner Overall is a HYBRID with TWO independent axes — do not conflate them:
(1) DIRECTION + CONFIDENCE are count-based (`count_block_overall`): pooled across all
active markets, UP if total_up>total_dn, DOWN if reversed, NEUTRAL only on a true
count tie (never forced NEUTRAL just because the element trigger is silent; flat/0
price counts as up). (2) The AGREEMENT column (banner F / PF AGREEMENT) is a 3-state
LABEL (`agreement_label`) comparing the element-trigger verdict (`element_trigger_overall`)
to the count direction: CONFIRMED / SILENT (elem NEUTRAL) / CONFLICT. The element
trigger is kept ONLY to drive this label — it does NOT decide direction.
**Why:** this logic has flip-flopped (count-based → element-trigger-driven → hybrid);
the durable rule is direction=count, label=element-trigger-agreement, kept in shared
SSOT helpers so the writer and verifier can't drift. SCORE/SCORE-OVERALL/SCORE-CONF
(cols M/N/O, match-depth) are a SEPARATE, independent computation — do not couple them.
