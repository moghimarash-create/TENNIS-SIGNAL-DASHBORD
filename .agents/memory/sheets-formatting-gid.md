---
name: Sheets batchUpdate gid resolution
description: Why Step 4 (and any Sheets writer) must resolve the formatting gid by tab name, not by sheet order
---

When a Google Sheets script writes VALUES by A1 range (e.g. `Sheet1!A2:L...`) but applies
FORMATTING via `batchUpdate` (which needs a numeric `sheetId`/gid), the gid MUST be resolved
by the SAME tab name used for the values write.

**Rule:** resolve gid with `get_sheet_gid(spreadsheetId, "Sheet1")`, never the no-arg form that
returns `sheets[0]` (the first tab).

**Why:** a no-arg lookup returns the first tab in the spreadsheet's tab order. If someone adds
or reorders a tab (e.g. a small `Sheet2` of 1000 rows lands first), formatting targets the wrong
grid and Google returns `400 ... Range (Sheet2!A1031:L1031) exceeds grid limits`. Values still
land on Sheet1, so the failure looks unrelated to formatting and only triggers on large outputs.

**How to apply:** any time you pair a values write with a `batchUpdate` format pass in the
Step pipeline (`artifacts/api-server/python/step*.py`), pass the explicit tab name to the gid
lookup. Also keep `format_sheet` raising with the API response body so the real message surfaces.
