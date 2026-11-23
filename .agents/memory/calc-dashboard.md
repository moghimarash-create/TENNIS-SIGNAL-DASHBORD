---
name: calc-dashboard / api-server step logs
description: Where per-step Python run logs actually live and how to inspect a step run
---

# Step run logs path

Per-step logs are written to `artifacts/logs/stepN.log` (repo-root-relative), NOT
`artifacts/api-server/logs/stepN.log` as some docs/comments imply.

**Why:** the api-server resolves its log dir relative to the workspace root, not the
package dir. A grep against the api-server path silently finds nothing.

**How to apply:** to inspect a step run, prefer the API
(`curl -s http://localhost:80/api/steps/N/logs`) or read `artifacts/logs/stepN.log`.
Trigger a run with `curl -X POST http://localhost:80/api/steps/N/run -d '{}'`
(no api-server restart needed for Python-only changes; restart only when
`steps-config.ts` changes, since the running server caches step descriptions).

# Dynamic-width sheet output must clear the whole sheet, not a computed range

When a step writes a Google Sheet whose column count varies between runs (e.g.
Step 4 PREDICTION-FINAL = 3 + 5*N + 6 cols, N = active markets), clearing only the
*current* run's range (`A1:<lastcol>5000`) leaves stale columns from a prior wider
run. Always clear the entire sheet (`clear_sheet(ID, "Sheet1")`) before writing.

**Why:** Step 4 went from 4 markets (29 cols, A:AC) to 2 markets (19 cols, A:S);
clearing A1:S left ghost `SPX_*`/summary headers in T:AC.

**How to apply:** for any variable-width sheet output, prefer a full-sheet values
clear over a computed/fixed-width range. Fixed wide ranges (e.g. A1:BZ) only push
the bug to a larger market count.

# Step 4 historical-only cutoff can silently zero out all DB rows

Step 4 keeps a search-DB (KEY-MATCH-*) row only if its DATE is strictly BEFORE
the earliest forward date in SEARCH-SIGNALS. If SEARCH-SIGNALS holds placeholder
data whose dates overlap (or predate) the DB range — e.g. both start at
1970-01-02 — every DB row is dropped as "future" and the run ends with
"DATA-SEARCH-KEY had no usable historical rows" (rowsWritten 0). This is a DATA
state, not a matcher bug.

**How to apply:** before concluding Step 4 matching is broken, check the
forward-date cutoff line in `artifacts/logs/step4.log`. To exercise the scoring
loop you need SEARCH-SIGNALS forward dates strictly AFTER the DB history range.
