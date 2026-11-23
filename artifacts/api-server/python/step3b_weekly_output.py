"""Step 3B - Weekly Output.

Standalone stage that reads Node_Output's daily rows (Step 3's output,
skipping any pre-existing WEEKLY total rows) and rebuilds the WEEKLY-OUTPUT
tab, so it can be re-run independently of Step 3.

LOTTO / 12-HORSE MODE: Node_Output carries AI=HORSE_NO, AJ=HORSE on every
row.  Daily rows are grouped by horse (first-appearance order) and the
unchanged Monday-Sunday grouping runs once per horse, so WEEKLY-OUTPUT has
one weekly total row per (horse, week), tagged with the same two columns
(36 columns wide).  Rows are written WEEK-MAJOR: each week's 12 horse rows
appear together, in chronological week order.  Without horse columns there is a single group and the
result matches the previous 34-column behaviour plus two blank tag columns.

Weekly grouping logic (Monday-Sunday windows, col F = Monday date) is an
EXACT, unmodified port of step3_result_degree.py's close_week() /
build_weekly_summary_row() / date_info_from_serial() -- imported directly
from that module rather than duplicated, so behavior can never drift between
the two stages.

WRITE SAFETY (temp-tab swap, not clear-then-write):
A plain clear()-then-write() is NOT atomic -- if the process dies/times out/
gets restarted between the clear and the write finishing, WEEKLY-OUTPUT is
left completely blank (worse than stale data). To make an empty target tab
impossible:
  1. The full 2D `weekly_output_rows` array is built ENTIRELY in memory
     first, before any Sheets write happens.
  2. That data (and its formatting) is written into a brand-new temporary
     worksheet ("WEEKLY-OUTPUT__tmp_write"). The real WEEKLY-OUTPUT tab is
     never touched during this phase.
  3. Only once the temp tab is fully written and formatted does run() delete
     the old WEEKLY-OUTPUT tab and rename the temp tab in its place -- a
     single, fast metadata-only operation.
If step 2 raises for any reason (rate limit, timeout, restart, crash), the
existing WEEKLY-OUTPUT tab is guaranteed untouched; the (incomplete) temp tab
is cleaned up on a best-effort basis and/or removed at the start of the next
run.
"""
import sys
import time
import traceback

from gspread.exceptions import APIError, WorksheetNotFound

from _lib.runner import emit_result, log
from _lib.sheets import open_sheet
from step3_result_degree import (
    COLOR_YELLOW_WEEKLY,
    HORSE_NAME_COL,
    HORSE_NO_COL,
    NODE_OUTPUT_TAB,
    N_OUT_COLS,
    OUTPUT_SPREADSHEET_ID,
    WEEKLY_OUTPUT_TAB,
    apply_format_requests,
    bg_color_row_request,
    build_weekly_summary_row,
    col_letter,
    date_info_from_serial,
    sheets_retry,
)

TEMP_TAB = f"{WEEKLY_OUTPUT_TAB}__tmp_write"


def write_new_tab(ss, title: str, rows: list[list], n_cols: int,
                   chunk_size: int = 2000, sleep_between: float = 0.5):
    """Create a brand-new worksheet named `title` and write `rows` into it.

    `title` must not already exist (callers are responsible for removing any
    stale leftover first). Raises on any failure -- callers must NOT treat a
    partially-written result from this function as usable; the sheet it
    returns should be discarded/deleted, never swapped in.
    """
    total = max(len(rows), 1)
    ws = sheets_retry(ss.add_worksheet, title=title, rows=total, cols=n_cols)

    if not rows:
        return ws

    last_col = col_letter(n_cols)
    header = rows[0]
    data = rows[1:]

    header_rng = f"A1:{last_col}1"
    log(f"  writing {title} header (1 row, {n_cols} cols)")
    resp = sheets_retry(ws.update, [header], header_rng, value_input_option="USER_ENTERED")
    cells = resp.get("updatedCells", 0)
    log(f"    -> updatedCells={cells} updatedRange={resp.get('updatedRange')}")
    if cells != n_cols:
        raise RuntimeError(
            f"{title} header write returned updatedCells={cells}, expected {n_cols} "
            f"(range={header_rng}); response={resp}"
        )

    if data:
        total_chunks = (len(data) + chunk_size - 1) // chunk_size
        total_written = cells
        for idx, i in enumerate(range(0, len(data), chunk_size), start=1):
            chunk = data[i:i + chunk_size]
            start_row = 2 + i
            end_row = start_row + len(chunk) - 1
            rng = f"A{start_row}:{last_col}{end_row}"
            expected = len(chunk) * n_cols
            log(f"  writing {title} chunk {idx}/{total_chunks}: rows {start_row}-{end_row}")
            resp = sheets_retry(ws.update, chunk, rng, value_input_option="USER_ENTERED")
            cells = resp.get("updatedCells", 0)
            total_written += cells
            log(f"    -> updatedCells={cells} updatedRange={resp.get('updatedRange')}")
            if cells != expected:
                raise RuntimeError(
                    f"{title} chunk {idx} returned updatedCells={cells}, expected {expected} "
                    f"(range={rng}, sent {len(chunk)} rows x {n_cols} cols); response={resp}"
                )
            if idx < total_chunks:
                time.sleep(sleep_between)
        log(f"  {title} total cells written: {total_written}")

    return ws


def remove_stale_temp_tab(ss, title: str) -> None:
    try:
        stale = ss.worksheet(title)
    except WorksheetNotFound:
        return
    log(f"  found leftover '{title}' from a previous failed/interrupted run -- removing it first")
    sheets_retry(ss.del_worksheet, stale)


def swap_in_tab(ss, target_title: str, temp_ws) -> None:
    """Replace `target_title` with the fully-written `temp_ws` in two fast
    metadata-only calls (delete old, rename new) -- only ever called once
    temp_ws is confirmed fully written and formatted.
    """
    try:
        old_ws = ss.worksheet(target_title)
    except WorksheetNotFound:
        old_ws = None
    if old_ws is not None:
        log(f"  deleting old '{target_title}' (gid={old_ws.id})...")
        sheets_retry(ss.del_worksheet, old_ws)
    log(f"  renaming temp tab (gid={temp_ws.id}) -> '{target_title}'...")
    sheets_retry(temp_ws.update_title, target_title)


def run() -> None:
    log("[1/4] Opening output workbook + reading Node_Output...")
    ss = open_sheet(OUTPUT_SPREADSHEET_ID)
    node_ws = ss.worksheet(NODE_OUTPUT_TAB)
    last_col = col_letter(N_OUT_COLS)
    raw_rows = sheets_retry(
        node_ws.get_values,
        f"A:{last_col}",
        value_render_option="UNFORMATTED_VALUE",
        date_time_render_option="SERIAL_NUMBER",
    )

    daily_rows: list[list] = []
    skipped_weekly = 0
    skipped_blank = 0
    for r in raw_rows:
        if not r or all(v == "" or v is None for v in r):
            skipped_blank += 1
            continue
        col_e = str(r[4]).strip().upper() if len(r) > 4 and r[4] is not None else ""
        if col_e == "WEEKLY":
            skipped_weekly += 1
            continue
        row = list(r) + [""] * (N_OUT_COLS - len(r))
        daily_rows.append(row[:N_OUT_COLS])

    log(
        f"  read {len(raw_rows)} raw Node_Output rows: {len(daily_rows)} daily rows, "
        f"{skipped_weekly} pre-existing WEEKLY rows skipped, {skipped_blank} blank rows skipped"
    )

    # Group by horse tag (AI/AJ), first-appearance order; legacy rows -> ('', '').
    horse_groups: dict[tuple[str, str], list[list]] = {}
    for row in daily_rows:
        key = (str(row[HORSE_NO_COL]).strip() if row[HORSE_NO_COL] not in ("", None) else "",
               str(row[HORSE_NAME_COL]).strip() if row[HORSE_NAME_COL] not in ("", None) else "")
        horse_groups.setdefault(key, []).append(row)
    log(f"  {len(horse_groups)} horse group(s): "
        + ", ".join(f"{no} {name}".strip() or "(no horse)" for no, name in horse_groups))

    log("[2/4] Grouping into Monday-Sunday weeks per horse (in memory only, no Sheets writes yet)...")
    # Collected per (week_start, horse) first, then emitted WEEK-MAJOR: for each
    # Monday-Sunday window (in order of first appearance) one row per horse
    # (horse order = first appearance), so every week shows its 12 horses
    # together -- mirroring the date-major layout of Node_Output.
    weekly_by_week: dict = {}            # week_key -> {horse_key: weekly row}
    week_order: list = []                # week_keys in first-appearance order
    per_horse_counts: dict[str, int] = {}

    current_horse: tuple[str, str] = ("", "")

    def close_week(week_rows: list[list], first_row: int | None, week_start=None) -> None:
        if not week_rows or first_row is None:
            return
        # first_row/last_row only matter for the live =SUM() formula that
        # build_weekly_summary_row() puts in cols G/H/I; that formula is
        # always overwritten below with the already-computed numeric sums,
        # since Node_Output's row numbers are meaningless (and could even
        # self-reference) once copied onto WEEKLY-OUTPUT. Placeholder values
        # (1, 1) only satisfy the function signature.
        weekly_row, sum_g, sum_h, sum_i = build_weekly_summary_row(week_rows, 1, 1)
        weekly_copy = list(weekly_row)
        weekly_copy[6] = sum_g
        weekly_copy[7] = sum_h
        weekly_copy[8] = sum_i
        # Col F = the Monday of this week's Mon-Sun window, formatted the
        # same way as Node_Output's daily col F (format_serial_date_f: M/D/YYYY).
        if week_start is not None:
            weekly_copy[5] = f"{week_start.month}/{week_start.day}/{week_start.year}"
        weekly_copy = list(weekly_copy) + [""] * (N_OUT_COLS - len(weekly_copy))
        weekly_copy[HORSE_NO_COL] = current_horse[0]
        weekly_copy[HORSE_NAME_COL] = current_horse[1]
        week_key = str(week_start) if week_start is not None else f"__none_{len(week_order)}"
        if week_key not in weekly_by_week:
            weekly_by_week[week_key] = {}
            week_order.append(week_key)
        weekly_by_week[week_key][current_horse] = weekly_copy
        label = f"{current_horse[0]} {current_horse[1]}".strip() or "(no horse)"
        per_horse_counts[label] = per_horse_counts.get(label, 0) + 1

    for horse_key, horse_rows in horse_groups.items():
        # Identical loop as before, run once per horse so weeks never mix horses.
        current_horse = horse_key
        current_week_rows: list[list] = []
        current_week_start = None
        week_first_row_num: int | None = None

        for row in horse_rows:
            _weekday_name, _weekday_num, week_start = date_info_from_serial(row[5] if len(row) > 5 else "")

            # A new row belongs to a different Monday-Sunday window than the one
            # currently being accumulated -> the previous week is done (even if
            # it never contained a Sunday row, e.g. date gaps).
            if current_week_rows and week_start is not None and week_start != current_week_start:
                close_week(current_week_rows, week_first_row_num, current_week_start)
                current_week_rows = []
                week_first_row_num = None
                current_week_start = None

            current_week_rows.append(row)
            if week_first_row_num is None:
                week_first_row_num = 1  # placeholder; the real row numbers are never used downstream
                current_week_start = week_start

        # Flush any trailing partial week (data ended before hitting the next
        # week's window, e.g. no Sunday row present) -- still gets its own
        # yellow total row per the "place after the last present day" rule.
        close_week(current_week_rows, week_first_row_num, current_week_start)

    # Week-major emission: chronological weeks (sorted by Monday date), horses
    # in first-appearance order inside each week.
    def _week_sort_key(k: str):
        return (0, k) if not k.startswith("__none_") else (1, k)
    weekly_output_rows: list[list] = []
    yellow_row_indices: list[int] = []
    horse_order = list(horse_groups.keys())
    for week_key in sorted(week_order, key=_week_sort_key):
        rows_for_week = weekly_by_week[week_key]
        for hk in horse_order:
            if hk in rows_for_week:
                weekly_output_rows.append(rows_for_week[hk])
                yellow_row_indices.append(len(weekly_output_rows) - 1)

    log(f"  built {len(weekly_output_rows)} WEEKLY-OUTPUT rows in memory "
        f"({', '.join(f'{k}: {v}' for k, v in per_horse_counts.items())})")

    log(f"[3/4] Writing to temp tab '{TEMP_TAB}' ('{WEEKLY_OUTPUT_TAB}' is NOT touched yet)...")
    remove_stale_temp_tab(ss, TEMP_TAB)
    try:
        temp_ws = write_new_tab(ss, TEMP_TAB, weekly_output_rows, N_OUT_COLS)
    except Exception:
        log(
            f"  write to '{TEMP_TAB}' failed -- '{WEEKLY_OUTPUT_TAB}' left fully intact; "
            "cleaning up the incomplete temp tab"
        )
        try:
            remove_stale_temp_tab(ss, TEMP_TAB)
        except Exception as cleanup_exc:
            log(f"  WARNING: failed to clean up '{TEMP_TAB}': {cleanup_exc}")
        raise

    sent = 0
    format_status = "OK"
    format_error: str | None = None
    format_requests = [
        bg_color_row_request(temp_ws.id, idx, COLOR_YELLOW_WEEKLY, n_cols=N_OUT_COLS)
        for idx in yellow_row_indices
    ]
    if not format_requests:
        log("  No format requests to apply")
    else:
        log(f"  Applying {len(format_requests)} background-color requests to temp tab...")
        try:
            sent = apply_format_requests(ss, format_requests)
            log(f"  formatting complete: {sent}/{len(format_requests)} applied")
        except APIError as exc:
            format_status = "WARNING"
            format_error = str(exc)
            log(f"  WARNING: formatting failed on temp tab (values still OK): {exc}")

    log(f"[4/4] Swapping temp tab into '{WEEKLY_OUTPUT_TAB}'...")
    swap_in_tab(ss, WEEKLY_OUTPUT_TAB, temp_ws)
    log(f"  {WEEKLY_OUTPUT_TAB} replaced successfully")

    msg_parts = [
        f"Wrote {len(weekly_output_rows)} {WEEKLY_OUTPUT_TAB} rows",
        f"from {len(daily_rows)} Node_Output daily rows",
        f"applied {sent}/{len(format_requests)} color formats" if format_requests else "no color formats",
    ]
    if format_status == "WARNING":
        msg_parts.append("(formatting WARNING — values OK)")
    msg = "; ".join(msg_parts)

    log(f"Step 3B complete: {msg}")
    emit_result(
        ok=True,
        rows_written=len(weekly_output_rows),
        message=msg,
        extra={
            "dailyRowsRead": len(daily_rows),
            "horses": len(horse_groups),
            "weeklyPerHorse": per_horse_counts,
            "skippedWeeklyRows": skipped_weekly,
            "skippedBlankRows": skipped_blank,
            "formatRequests": sent,
            "formatTotal": len(format_requests),
            "formatStatus": format_status,
            "formatError": format_error,
        },
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log("ERROR: " + str(e))
        log(traceback.format_exc())
        emit_result(ok=False, error=str(e), message="Step 3B failed")
        sys.exit(1)
