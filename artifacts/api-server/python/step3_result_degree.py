"""Step 3 - Result Degree (port of process.js wrapper).

Reads Aspects (1SeI..MTt4 / Sheet1) — A:E formatted, F unformatted — merges
into 6-col rows, runs the 4-phase processor, then writes:

  1. OUTPUT/Sheet1     : 34 columns (A..AH), with cell background-color formatting
                         applied via spreadsheets.batchUpdate.
  2. OUTPUT/Node_Output : node-only rows, including weekly (Mon-Sun) summary
                         rows, which feed Step 3B's WEEKLY-OUTPUT tab.

WEEKLY-OUTPUT itself is written by the standalone step3b_weekly_output.py,
which re-derives the weekly grouping straight from Node_Output. This module
does not write WEEKLY-OUTPUT.

LOTTO / 12-HORSE MODE: Aspects now carries G=HORSE_NO, H=HORSE on every row
and each (DATE, HORSE) pair is its own date-block, in DATE-MAJOR order
(date 1: horse 1..12, date 2: horse 1..12, ...).  Phases 1-3 are unchanged:
they work block by block, so every (DATE, HORSE) block gets its own Node row
and Result Degree / Node_Output keep that same date-major order -- i.e. each
date has 12 consecutive outputs, one per horse.  The only horse-aware part is
the WEEKLY summary in Phase 4: daily Node rows are accumulated PER HORSE inside
each Monday-Sunday window and, when the window changes, one weekly row per
horse is emitted (12 weekly rows after the week's last day).  The weekly G/H/I
are the same per-horse weekly sums as before; because horses are interleaved
inside the week block, the live formula is =SUMIF(<week AI range>, horse_no,
<week G range>) instead of a plain =SUM over a contiguous range (legacy
single-point input still gets the plain =SUM).  Two tag columns are appended
to every output row: AI=HORSE_NO, AJ=HORSE (36 columns).

WEEKLY rows are disabled by default in this app (WEEKLY_ROWS_ENABLED /
STEP3_WEEKLY_ROWS env): Node_Output then holds daily Node rows only, 12 per
date, with no yellow summary rows.
"""
import os
import random
import re
import sys
import time
import traceback
from typing import Any

import gspread
from gspread.exceptions import APIError, WorksheetNotFound

from _lib.runner import emit_result, log
from _lib.sheets import open_sheet

# Toggle to skip color formatting entirely (values + Node_Output still written).
FORMAT_ENABLED = os.environ.get("STEP3_FORMAT_ENABLED", "1") not in ("0", "false", "False")

# LOTTO: weekly (Monday-Sunday) summary rows are NOT wanted in Node_Output.
# Default off; set STEP3_WEEKLY_ROWS=1 to re-enable the yellow WEEKLY rows.
WEEKLY_ROWS_ENABLED = os.environ.get("STEP3_WEEKLY_ROWS", "0") in ("1", "true", "True")

_RETRYABLE_CODES = ("[429]", "[500]", "[502]", "[503]", "[504]")


def sheets_retry(fn, *args, max_retries: int = 6, base_delay: float = 1.5,
                 max_delay: float = 60.0, **kwargs):
    """Retry Google Sheets API calls with exponential backoff + jitter.

    Retries on transient APIError responses (429/500/502/503/504). Re-raises
    everything else immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except APIError as e:
            msg = str(e)
            retryable = any(code in msg for code in _RETRYABLE_CODES)
            if not retryable or attempt == max_retries:
                raise
            delay = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, 1.5)
            log(f"  sheets retry {attempt + 1}/{max_retries} in {delay:.1f}s ({msg[:120]})")
            time.sleep(delay)

INPUT_SPREADSHEET_ID = os.environ.get("TENNIS_ASTRO_ASPECTS_SHEET_ID", "")
INPUT_TAB = "Sheet1"

OUTPUT_SPREADSHEET_ID = os.environ.get("TENNIS_RESULT_DEGREE_SHEET_ID", "")
OUTPUT_TAB = "Sheet1"
NODE_OUTPUT_TAB = "Node_Output"
WEEKLY_OUTPUT_TAB = "WEEKLY-OUTPUT"

PLANET_NAMES = (
    "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
    "uranus", "neptune", "pluto", "chiron", "north node", "south node",
)

DATE_PATTERN = re.compile(r"^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$")

COLOR_BLUE = {"red": 0.68, "green": 0.85, "blue": 0.9}
COLOR_RED = {"red": 1.0, "green": 0.6, "blue": 0.6}
COLOR_GREEN = {"red": 0.56, "green": 0.93, "blue": 0.56}
COLOR_YELLOW = {"red": 1.0, "green": 1.0, "blue": 0.6}
COLOR_YELLOW_PURE = {"red": 1.0, "green": 1.0, "blue": 0.0}


# ----- helpers (port of process.js) -----

def is_date_row(cell: Any) -> bool:
    if not cell:
        return False
    s = str(cell).strip()
    if DATE_PATTERN.match(s):
        return True
    return "/" in s or "-" in s


def is_planet_row(cell: Any) -> bool:
    if not cell:
        return False
    s = str(cell).strip().lower()
    return any(p in s for p in PLANET_NAMES)


def extract_nature(col_d: Any, col_e: Any) -> str:
    d = str(col_d or "").strip().lower()
    e = str(col_e or "").strip().lower()
    temp = "Hot" if "hot" in d else ("Cold" if "cold" in d else "")
    moist = "Dry" if "dry" in e else ("Moist" if "moist" in e else "")
    return f"{temp} & {moist}" if temp and moist else ""


def quality_to_element(q: str) -> str:
    if not q:
        return ""
    s = str(q).lower()
    if "hot" in s and "dry" in s:
        return "Fire"
    if "cold" in s and "dry" in s:
        return "Earth"
    if "hot" in s and "moist" in s:
        return "Air"
    if "cold" in s and "moist" in s:
        return "Water"
    return ""


def digital_root_keep_101112(n: int) -> int:
    if n in (10, 11, 12):
        return n
    while n > 12:
        n = sum(int(c) for c in str(n))
        if n in (10, 11, 12):
            break
    return n


def mod_arcanum(n):
    return ((n - 1) % 22) + 1


_ZODIAC_MAP = {
    1: "Scorpio - [Water]", 2: "Leo - [Fire]", 3: "Gemini - [Air]",
    4: "Aries - [Fire]",
    5: "Gemini - [Air]", 6: "Gemini - [Air]",
    7: "Capricorn - [Earth]", 8: "Libra - [Air]",
    9: "Capricorn - [Earth]", 10: "Gemini - [Air]",
    11: "Taurus - [Earth]", 12: "Cancer - [Water]",
    13: "Gemini - [Air]", 14: "Leo - [Fire]",
    15: "Aries - [Fire]", 16: "Gemini - [Air]",
    17: "Taurus - [Earth]", 18: "Scorpio - [Water]",
    19: "Capricorn - [Earth]", 20: "Leo - [Fire]",
    21: "Aquarius - [Air]", 22: "Virgo - [Earth]",
}


def get_zodiac_card(n: Any) -> str:
    """Match JS: Number(n); switch on exact integer equality. Floats like 5.7 -> ''."""
    if n is None or n == "":
        return ""
    try:
        f = float(n)
    except (TypeError, ValueError):
        return ""
    if f != int(f):
        return ""
    return _ZODIAC_MAP.get(int(f), "")


def get_qualities(sign: str) -> str:
    if not sign:
        return ""
    s = str(sign).lower()
    table = [
        ("aries", "Hot-Dry"), ("taurus", "Cold-Dry"), ("gemini", "Hot-Moist"),
        ("cancer", "Cold-Moist"), ("leo", "Hot-Dry"), ("virgo", "Cold-Dry"),
        ("libra", "Hot-Moist"), ("scorpio", "Cold-Moist"),
        ("sagittarius", "Hot-Dry"), ("capricorn", "Cold-Dry"),
        ("aquarius", "Hot-Moist"), ("pisces", "Cold-Moist"),
    ]
    for key, val in table:
        if key in s:
            return val
    return ""


def elem_main(sign: Any, num: Any) -> str:
    if not sign or num is None or num == "":
        return ""
    q = get_qualities(sign)
    return f"{num}{q.split('-')[0]}" if q else ""


def elem_sub(sign: Any, num: Any) -> str:
    if not sign or num is None or num == "":
        return ""
    q = get_qualities(sign)
    return f"{num}{q.split('-')[1]}" if q else ""


_LEADING_NUM_RE = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)")


def _js_parse_float(s: str):
    """Mimic JS parseFloat: parses leading numeric prefix, ignoring trailing junk."""
    m = _LEADING_NUM_RE.match(s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _net_pair(values: list, pos_label: str, neg_label: str) -> str:
    pos = neg = 0.0
    for txt in values:
        if not txt:
            continue
        s = str(txt).strip().upper()
        if not s:
            continue
        n = _js_parse_float(s)
        if n is None:
            continue
        if s.endswith(pos_label):
            pos += n
        elif s.endswith(neg_label):
            neg += n
    net = pos - neg
    if net > 0:
        return f"{_fmt_num(net)} {pos_label}"
    if net < 0:
        return f"{_fmt_num(abs(net))} {neg_label}"
    return "0 NEUTRAL"


def _fmt_num(n: float) -> str:
    return str(int(n)) if n == int(n) else str(n)


def hot_cold_net(*vals: Any) -> str:
    return _net_pair(list(vals), "HOT", "COLD")


def moist_dry_net(*vals: Any) -> str:
    return _net_pair(list(vals), "MOIST", "DRY")


def get_taba_adad(input_val: Any) -> Any:
    if input_val is None or input_val == "":
        return ""
    s = str(input_val).strip()
    if not s:
        return ""
    total = 0
    for ch in s:
        code = ord(ch)
        if 48 <= code <= 57:
            total += int(ch)
        elif 65 <= code <= 90:
            total += code - 64
        elif 97 <= code <= 122:
            total += code - 96
    return digital_root_keep_101112(total)


def zod_aspect_deg(aspect: Any) -> Any:
    if aspect is None or aspect == "":
        return ""
    raw = str(aspect).strip()
    if not raw:
        return ""
    s = raw.upper()
    code = re.sub(r"\s", "", s)
    first = ord(raw[0]) if raw else 0
    if first == 9740:
        return 0
    if first == 9741:
        return 180
    if first == 9651:
        return 120
    if first == 9633:
        return 90
    if "\u2220" in raw:
        return 45
    if "\u26BA" in raw or "\u26ba" in raw:
        return 30
    if "\u26BB" in raw or "\u26bb" in raw:
        return 150
    if "\u26BC" in raw or "\u26bc" in raw:
        return 135
    sextile_chars = ["*", "\u2217", "\u2731", "\u2733", "\u2734", "\u2736",
                     "\u274B", "\u2606", "\u066D", "\u204E", "\uFF0A"]
    if any(c in raw for c in sextile_chars):
        return 60
    if len(raw) == 1:
        a = first
        if not ((48 <= a <= 57) or (65 <= a <= 90) or (97 <= a <= 122)):
            return 60
    if "SEXTILE" in s:
        return 60
    if "SESQUISQUARE" in s:
        return 135
    if "SEMISQUARE" in s:
        return 45
    if "SEMISEXTILE" in s:
        return 30
    if "QUINCUNX" in s or "INCONJ" in s:
        return 150
    if "TRINE" in s:
        return 120
    if "SQUARE" in s:
        return 90
    if "OPP" in s:
        return 180
    if "CONJ" in s:
        return 0
    code_map = {
        "S": 51, "S2": 103, "S3": 154,
        "N": 40, "N2": 80, "N4": 160,
        "U": 33, "U2": 65, "U3": 98, "U5": 164,
        "Q": 72, "Q2": 144, "BQ": 144,
        "D": 36, "D3": 108,
    }
    if code in code_map:
        return code_map[code]
    if code:
        fc = code[0]
        rest = code[1:]
        if fc == "H":
            try:
                n = int(rest) if rest else 1
                if n > 0:
                    return 360 / n
            except ValueError:
                pass
    try:
        return float(raw)
    except ValueError:
        return ""


_NEAREST_TARGETS = [0, 30, 36, 40, 45, 51, 60, 65, 72, 80, 90, 98, 103, 108,
                    120, 131, 135, 144, 150, 154, 180, 33]


def nearest_angle(deg: Any) -> Any:
    if not isinstance(deg, (int, float)) or isinstance(deg, bool):
        return ""
    best = _NEAREST_TARGETS[0]
    best_diff = abs(deg - best)
    for t in _NEAREST_TARGETS[1:]:
        d = abs(deg - t)
        if d < best_diff:
            best_diff = d
            best = t
    return best


def aspect_element(angle_val: Any) -> str:
    if not isinstance(angle_val, (int, float)) or isinstance(angle_val, bool):
        return ""
    a = nearest_angle(angle_val)
    if a in (0, 120, 72, 144, 36):
        return "Fire"
    if a == 60 or any(abs(a - t) < 0.01 for t in (51, 103, 154, 33, 65, 98, 131)):
        return "Air"
    if a in (40, 80):
        return "Water"
    if a in (30, 45, 90, 135, 150, 180):
        return "Earth"
    return ""


_HIGHLIGHT_POS = [0, 30, 36, 40, 60, 65, 72, 80, 120, 144]
_HIGHLIGHT_NEG = [45, 51, 90, 98, 103, 108, 131, 135, 150, 154, 163, 180]


def get_aspect_highlight(degree: Any) -> str:
    if not isinstance(degree, (int, float)) or isinstance(degree, bool):
        return ""
    for t in _HIGHLIGHT_POS:
        if abs(degree - t) <= 3:
            return "blue"
    for t in _HIGHLIGHT_NEG:
        if abs(degree - t) <= 3:
            return "red"
    return ""


def format_serial_date_f(serial: Any) -> str:
    if serial is None or serial == "":
        return ""
    if isinstance(serial, str):
        trimmed = serial.strip()
        if not trimmed:
            return ""
        try:
            n = float(trimmed)
            serial = n
        except ValueError:
            return trimmed
    if not isinstance(serial, (int, float)) or isinstance(serial, bool):
        return ""
    from datetime import datetime, timedelta, timezone
    epoch = datetime(1899, 12, 30, tzinfo=timezone.utc)
    d = epoch + timedelta(milliseconds=round(float(serial) * 86400000))
    return f"{d.month}/{d.day}/{d.year}"


def date_info_from_serial(serial: Any) -> tuple[str, int | None, Any]:
    """Return (WEEKDAY_NAME_UPPER, weekday_num, week_start_date) from a sheet date serial.

    weekday_num follows Python's convention: Monday=0 ... Sunday=6.
    week_start_date is the `date` (Monday) of the calendar week that this
    serial's actual date falls into -- computed directly from the date, NOT
    by counting/position, so it is correct even when dates have gaps
    (e.g. 12/4 then 12/6 then 12/8) and no row lands exactly on a Sunday.
    Returns ("", None, None) if serial can't be parsed as a date. Uses the
    same epoch as format_serial_date_f so weekday and formatted date agree.

    Column F in this pipeline's real data is a pre-formatted text string
    like "12/1/2014" (NOT a numeric Sheets serial) -- format_serial_date_f
    already passes such strings through unchanged, so to stay in agreement
    this parses that same "M/D/YYYY" text form directly (in addition to
    still accepting a genuine numeric serial, for robustness).
    """
    from datetime import datetime, timedelta, timezone

    if serial is None or serial == "":
        return "", None, None
    if isinstance(serial, str):
        trimmed = serial.strip()
        if not trimmed:
            return "", None, None
        try:
            serial = float(trimmed)
        except ValueError:
            d_date = None
            for fmt in ("%m/%d/%Y", "%m/%d/%y"):
                try:
                    d_date = datetime.strptime(trimmed, fmt).date()
                    break
                except ValueError:
                    continue
            if d_date is None:
                return "", None, None
            weekday_num = d_date.weekday()
            week_start = d_date - timedelta(days=weekday_num)
            return d_date.strftime("%A").upper(), weekday_num, week_start
    if not isinstance(serial, (int, float)) or isinstance(serial, bool):
        return "", None, None
    epoch = datetime(1899, 12, 30, tzinfo=timezone.utc)
    d = epoch + timedelta(milliseconds=round(float(serial) * 86400000))
    weekday_num = d.weekday()
    week_start = d.date() - timedelta(days=weekday_num)
    return d.strftime("%A").upper(), weekday_num, week_start


def bg_color_request(sheet_id: int, row_idx: int, col_idx: int, color: dict) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": col_idx,
                "endColumnIndex": col_idx + 1,
            },
            "cell": {"userEnteredFormat": {"backgroundColor": color}},
            "fields": "userEnteredFormat.backgroundColor",
        },
    }


def bg_color_row_request(sheet_id: int, row_idx: int, color: dict, n_cols: int = 34) -> dict:
    """Same as bg_color_request but spans the full row width in one request."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": 0,
                "endColumnIndex": n_cols,
            },
            "cell": {"userEnteredFormat": {"backgroundColor": color}},
            "fields": "userEnteredFormat.backgroundColor",
        },
    }


# ----- Node_Output weekly summary row (inserted after each Sunday, Mon-Sun weeks) -----

COLOR_YELLOW_WEEKLY = COLOR_YELLOW_PURE  # matches the pre-existing manual weekly total row


def compute_weekly_chain(sum_g: float, sum_h: float, sum_i: float) -> dict:
    """Run the IDENTICAL per-day function chain on a weekly-summed G/H/I input.

    This is the exact same sequence Phase 3 runs per day on sum_g/sum_h/sum_i:
    mod_arcanum -> get_zodiac_card -> elem_main/elem_sub -> hot_cold_net /
    moist_dry_net. No new formula is introduced; only the input (weekly sum
    instead of daily sum) differs.
    """
    mod_g = mod_arcanum(sum_g)
    mod_h = mod_arcanum(sum_h)
    mod_i = mod_arcanum(sum_i)
    zodiac_r = get_zodiac_card(mod_g)
    zodiac_s = get_zodiac_card(mod_h)
    zodiac_t = get_zodiac_card(mod_i)
    elem_u = elem_main(zodiac_r, mod_g)
    elem_v = elem_main(zodiac_s, mod_h)
    elem_w = elem_main(zodiac_t, mod_i)
    elem_x = elem_sub(zodiac_r, mod_g)
    elem_y = elem_sub(zodiac_s, mod_h)
    elem_z = elem_sub(zodiac_t, mod_i)
    hot_cold_aa = hot_cold_net(elem_u, elem_v, elem_w)
    moist_dry_ab = moist_dry_net(elem_x, elem_y, elem_z)
    return {
        "modG": mod_g, "modH": mod_h, "modI": mod_i,
        "zodiacR": zodiac_r, "zodiacS": zodiac_s, "zodiacT": zodiac_t,
        "elemU": elem_u, "elemV": elem_v, "elemW": elem_w,
        "elemX": elem_x, "elemY": elem_y, "elemZ": elem_z,
        "hotColdNetAA": hot_cold_aa, "moistDryNetAB": moist_dry_ab,
    }


def build_weekly_summary_row(week_rows: list[list], first_row: int, last_row: int) -> tuple[list, float, float, float]:
    """Build the weekly total row inserted immediately after each Sunday.

    first_row/last_row are the ACTUAL sheet row numbers (1-indexed; Node_Output
    has no header row) of the first and last daily rows in THIS week only.
    The caller guarantees this range is a contiguous block of daily rows with
    no weekly-total row inside it, so the SUM formula can never re-sum a prior
    week's total (that was the root cause of the runaway cumulative bug).
    Cols G/H/I get a real =SUM() formula over exactly those daily rows
    (matching the pre-existing manual weekly row). Col A = "Node" and col E =
    "WEEKLY" (mirrors daily Node-row col A, distinguishes from daily weekday
    names in col E). Col K = sum_g + sum_h + sum_i for the week, matching what
    col K holds on a daily Node row (item["sum"]). Cols L/M are intentionally
    left blank -- on daily rows they come from that day's own raw
    aspect-degree data, which has no weekly equivalent. Cols O-AB reuse
    compute_weekly_chain() -- the identical daily function chain -- fed with
    the numeric SUM of the week's G/H/I values.

    Returns (row, sum_g, sum_h, sum_i): the row has live =SUM() formulas in
    G/H/I (valid only on the sheet whose row numbers they reference, i.e.
    Node_Output); callers writing this row to a DIFFERENT sheet must swap in
    the returned numeric sums instead, or the formula's row-range can land on
    an unrelated (or its own) row there and produce a circular reference.
    """
    sum_g = sum(r[6] if isinstance(r[6], (int, float)) and not isinstance(r[6], bool) else 0.0 for r in week_rows)
    sum_h = sum(r[7] if isinstance(r[7], (int, float)) and not isinstance(r[7], bool) else 0.0 for r in week_rows)
    sum_i = sum(r[8] if isinstance(r[8], (int, float)) and not isinstance(r[8], bool) else 0.0 for r in week_rows)

    chain = compute_weekly_chain(sum_g, sum_h, sum_i)

    row = [""] * 34
    row[0] = "Node"
    row[4] = "WEEKLY"
    row[6] = f"=SUM(G{first_row}:G{last_row})"
    row[7] = f"=SUM(H{first_row}:H{last_row})"
    row[8] = f"=SUM(I{first_row}:I{last_row})"
    row[10] = sum_g + sum_h + sum_i
    row[14] = chain["modG"]
    row[15] = chain["modH"]
    row[16] = chain["modI"]
    row[17] = chain["zodiacR"]
    row[18] = chain["zodiacS"]
    row[19] = chain["zodiacT"]
    row[20] = chain["elemU"]
    row[21] = chain["elemV"]
    row[22] = chain["elemW"]
    row[23] = chain["elemX"]
    row[24] = chain["elemY"]
    row[25] = chain["elemZ"]
    row[26] = chain["hotColdNetAA"]
    row[27] = chain["moistDryNetAB"]
    return row, sum_g, sum_h, sum_i


# ----- main process function (4 phases, port of process.js) -----

COLOR_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}


N_BASE_COLS = 34          # A..AH : the original 34-column result layout
HORSE_NO_COL = 34         # AI (0-based 34)
HORSE_NAME_COL = 35       # AJ (0-based 35)
N_OUT_COLS = 36           # A..AJ


def process_data(
    rows: list[list],
    sheet_id: int,
    node_sheet_id: int | None = None,
    row_offset: int = 0,
    node_row_offset: int = 0,
    wipe_node_format: bool = True,
):
    """4-phase processor (unchanged logic).

    row_offset / node_row_offset: number of rows already written to Sheet1 /
    Node_Output by earlier horse groups; every colour request and the weekly
    =SUM() row range are shifted by them so a per-horse run lands on the right
    absolute rows.  wipe_node_format: emit the one-off "reset Node_Output
    background to white" request (only wanted once per Step-3 run).
    """
    trimmed = list(rows)
    if trimmed and str((trimmed[0][0] if trimmed[0] else "")).strip().lower() == "planet":
        trimmed.pop(0)

    output: list[dict] = []
    current_date_nature = ""

    # Phase 1
    for row in trimmed:
        row = row or []
        first_cell = row[0] if row else ""
        if is_date_row(first_cell):
            d3 = row[3] if len(row) > 3 else ""
            d4 = row[4] if len(row) > 4 else ""
            current_date_nature = extract_nature(d3, d4)

        col_b = row[1] if len(row) > 1 else ""
        col_c = row[2] if len(row) > 2 else ""
        col_d = row[3] if len(row) > 3 else ""

        if is_date_row(first_cell):
            deg_b = deg_c = deg_d = deg_e = ""
        else:
            deg_b = zod_aspect_deg(col_b)
            deg_c = zod_aspect_deg(col_c)
            deg_d = zod_aspect_deg(col_d)
            deg_e = zod_aspect_deg(row[4] if len(row) > 4 else "")

        nums = [v for v in (deg_b, deg_c, deg_d) if isinstance(v, (int, float)) and not isinstance(v, bool)]
        s = sum(nums) if nums else ""

        elem_g = aspect_element(deg_b)
        elem_h = aspect_element(deg_c)
        elem_i = aspect_element(deg_d)

        em_l = em_m = em_n = False
        if is_planet_row(first_cell) and current_date_nature:
            date_element = quality_to_element(current_date_nature)
            if date_element:
                em_l = elem_g == date_element
                em_m = elem_h == date_element
                em_n = elem_i == date_element

        base_hl_g = get_aspect_highlight(deg_b)
        base_hl_h = get_aspect_highlight(deg_c)
        base_hl_i = get_aspect_highlight(deg_d)

        hl_g = base_hl_g if em_l else ""
        hl_h = base_hl_h if em_m else ""
        hl_i = base_hl_i if em_n else ""

        first_lower = str(first_cell or "").strip().lower()
        is_node = first_lower == "node"
        formatted_date_f = format_serial_date_f(row[5] if len(row) > 5 else "") if is_node else ""

        output.append({
            "rowData": row,
            "degrees": [deg_b, deg_c, deg_d, deg_e],
            "sum": s,
            "elements": [elem_g, elem_h, elem_i],
            "elementMatchL": em_l,
            "elementMatchM": em_m,
            "elementMatchN": em_n,
            "highlightG": hl_g,
            "highlightH": hl_h,
            "highlightI": hl_i,
            "modG": mod_arcanum(deg_b) if isinstance(deg_b, (int, float)) and not isinstance(deg_b, bool) else "",
            "modH": mod_arcanum(deg_c) if isinstance(deg_c, (int, float)) and not isinstance(deg_c, bool) else "",
            "modI": mod_arcanum(deg_d) if isinstance(deg_d, (int, float)) and not isinstance(deg_d, bool) else "",
            "isNodeRow": is_node,
            "formattedDateF": formatted_date_f,
            "isStrongestAspect": False,
        })

    # Phase 2 — strongest aspect per day
    day_start = -1
    for i in range(len(output) + 1):
        is_date = i < len(output) and is_date_row(output[i]["rowData"][0] if output[i]["rowData"] else "")
        is_end = i == len(output)
        if (is_date or is_end) and day_start >= 0:
            best_idx = -1
            best_sum = -1.0
            for j in range(day_start, i):
                item = output[j]
                if not is_planet_row(item["rowData"][0] if item["rowData"] else ""):
                    continue
                if not (item["elementMatchL"] or item["elementMatchM"] or item["elementMatchN"]):
                    continue
                s = item["sum"] if isinstance(item["sum"], (int, float)) and not isinstance(item["sum"], bool) else -1
                if s > best_sum:
                    best_sum = s
                    best_idx = j
            if best_idx >= 0:
                output[best_idx]["isStrongestAspect"] = True
        if is_date:
            day_start = i

    # Phase 3 — Node row aggregation
    day_start2 = -1
    for i in range(len(output) + 1):
        is_date2 = i < len(output) and is_date_row(output[i]["rowData"][0] if output[i]["rowData"] else "")
        is_end2 = i == len(output)
        if (is_date2 or is_end2) and day_start2 >= 0:
            node_idx = -1
            for j in range(day_start2, i):
                fc = str(output[j]["rowData"][0] if output[j]["rowData"] else "").strip().lower()
                if "node" in fc:
                    node_idx = j
                    break
            if node_idx >= 0:
                sum_g = sum_h = sum_i = 0
                for j in range(day_start2 + 1, node_idx):
                    dg = output[j]["degrees"]
                    if isinstance(dg[0], (int, float)) and not isinstance(dg[0], bool):
                        sum_g += dg[0]
                    if isinstance(dg[1], (int, float)) and not isinstance(dg[1], bool):
                        sum_h += dg[1]
                    if isinstance(dg[2], (int, float)) and not isinstance(dg[2], bool):
                        sum_i += dg[2]
                node = output[node_idx]
                node["degrees"][0] = sum_g
                node["degrees"][1] = sum_h
                node["degrees"][2] = sum_i
                node["sum"] = sum_g + sum_h + sum_i
                node["isNodeRow"] = True
                node["modG"] = mod_arcanum(sum_g)
                node["modH"] = mod_arcanum(sum_h)
                node["modI"] = mod_arcanum(sum_i)
                node["zodiacR"] = get_zodiac_card(node["modG"])
                node["zodiacS"] = get_zodiac_card(node["modH"])
                node["zodiacT"] = get_zodiac_card(node["modI"])
                node["elemU"] = elem_main(node["zodiacR"], node["modG"])
                node["elemV"] = elem_main(node["zodiacS"], node["modH"])
                node["elemW"] = elem_main(node["zodiacT"], node["modI"])
                node["elemX"] = elem_sub(node["zodiacR"], node["modG"])
                node["elemY"] = elem_sub(node["zodiacS"], node["modH"])
                node["elemZ"] = elem_sub(node["zodiacT"], node["modI"])
                node["hotColdNetAA"] = hot_cold_net(node["elemU"], node["elemV"], node["elemW"])
                node["moistDryNetAB"] = moist_dry_net(node["elemX"], node["elemY"], node["elemZ"])
                ds_row = output[day_start2]["rowData"]
                node["dateDforAC"] = ds_row[3] if len(ds_row) > 3 else ""
                node["dateEforAD"] = ds_row[4] if len(ds_row) > 4 else ""
                node["hotColdNet4AE"] = hot_cold_net(node["hotColdNetAA"], node["moistDryNetAB"], node["dateDforAC"], node["dateEforAD"])
                node["moistDryNet4AF"] = moist_dry_net(node["hotColdNetAA"], node["moistDryNetAB"], node["dateDforAC"], node["dateEforAD"])

                def _abs_int_str(v):
                    try:
                        f = float(str(v).split()[0]) if v not in ("", None) else 0.0
                    except (ValueError, IndexError):
                        f = 0.0
                    return str(abs(int(f)))

                ae_str = _abs_int_str(node["hotColdNet4AE"])
                af_str = _abs_int_str(node["moistDryNet4AF"])
                try:
                    node["numberAG"] = int(af_str + ae_str)
                except ValueError:
                    node["numberAG"] = ""
                node["dateBforAH"] = ds_row[1] if len(ds_row) > 1 else ""
        if is_date2:
            day_start2 = i

    # Phase 4 — build values + format requests
    values: list[list] = []
    format_requests: list[dict] = []
    node_output_rows: list[list] = []
    # Weekly accumulation: one Monday-Sunday window at a time, daily Node rows
    # bucketed per horse (insertion order) so each horse gets its own weekly row.
    week_rows_by_horse: dict[tuple[str, str], list[list]] = {}
    week_first_row_num: int | None = None
    current_week_start = None

    if node_sheet_id is not None and wipe_node_format:
        # Wipe ANY stale background (e.g. yellow left over from a prior run
        # whose weekly rows landed on different row numbers) across the
        # whole Node_Output sheet before re-applying yellow only to this
        # run's actual weekly rows. ws.clear() only clears cell values, not
        # formatting, so without this a daily row can inherit yellow from a
        # previous run's weekly row that used to occupy that row index.
        format_requests.append({
            "repeatCell": {
                "range": {"sheetId": node_sheet_id},
                "cell": {"userEnteredFormat": {"backgroundColor": COLOR_WHITE}},
                "fields": "userEnteredFormat.backgroundColor",
            },
        })

    def _horse_key(raw_row: list) -> tuple[str, str]:
        no = str(raw_row[6]).strip() if len(raw_row) > 6 and raw_row[6] is not None else ""
        name = str(raw_row[7]).strip() if len(raw_row) > 7 and raw_row[7] is not None else ""
        return no, name

    def close_week(first_row: int | None, week_start=None) -> None:
        """Emit one weekly row per horse for the window just finished.

        first_row .. last_row = the contiguous block of this week's DAILY rows
        in Node_Output (all horses interleaved, no weekly rows inside).  The
        per-horse weekly sums come from build_weekly_summary_row() exactly as
        before; only the live formula is swapped for a SUMIF filtered on the
        horse column when horses are interleaved.
        """
        if not WEEKLY_ROWS_ENABLED or not week_rows_by_horse or first_row is None:
            week_rows_by_horse.clear()
            return
        a = first_row + node_row_offset
        b = len(node_output_rows) + node_row_offset
        multi = len(week_rows_by_horse) > 1 or any(k[0] != "" for k in week_rows_by_horse)
        for (h_no, h_name), week_rows in week_rows_by_horse.items():
            weekly_row, sum_g, sum_h, sum_i = build_weekly_summary_row(week_rows, a, b)
            weekly_row = list(weekly_row) + [""] * (N_OUT_COLS - len(weekly_row))
            if multi:
                crit = h_no if h_no.lstrip("-").isdigit() else f'"{h_no}"'
                for col_idx, letter in ((6, "G"), (7, "H"), (8, "I")):
                    weekly_row[col_idx] = f"=SUMIF($AI${a}:$AI${b},{crit},{letter}{a}:{letter}{b})"
            weekly_row[HORSE_NO_COL] = h_no
            weekly_row[HORSE_NAME_COL] = h_name
            node_output_rows.append(weekly_row)
            if node_sheet_id is not None:
                format_requests.append(
                    bg_color_row_request(
                        node_sheet_id, len(node_output_rows) - 1 + node_row_offset,
                        COLOR_YELLOW_WEEKLY, n_cols=N_OUT_COLS,
                    )
                )
        week_rows_by_horse.clear()

    for i, item in enumerate(output):
        r = item["rowData"] or []
        row = [""] * N_OUT_COLS
        row[HORSE_NO_COL], row[HORSE_NAME_COL] = _horse_key(r)
        for c in range(6):
            v = r[c] if c < len(r) else ""
            row[c] = v if v is not None else ""
        if is_date_row(r[0] if r else ""):
            row[5] = row[HORSE_NAME_COL]
        for c in range(4):
            v = item["degrees"][c] if c < len(item["degrees"]) else ""
            row[6 + c] = "" if v is None else v
        row[10] = "" if item["sum"] is None else item["sum"]
        for c in range(3):
            row[11 + c] = item["elements"][c] or ""
        row[14] = item["modG"] if item["modG"] != "" else ""
        row[15] = item["modH"] if item["modH"] != "" else ""
        row[16] = item["modI"] if item["modI"] != "" else ""

        if item["isNodeRow"]:
            row[17] = item.get("zodiacR", "")
            row[18] = item.get("zodiacS", "")
            row[19] = item.get("zodiacT", "")
            row[20] = item.get("elemU", "")
            row[21] = item.get("elemV", "")
            row[22] = item.get("elemW", "")
            row[23] = item.get("elemX", "")
            row[24] = item.get("elemY", "")
            row[25] = item.get("elemZ", "")
            row[26] = item.get("hotColdNetAA", "")
            row[27] = item.get("moistDryNetAB", "")
            row[28] = item.get("dateDforAC", "")
            row[29] = item.get("dateEforAD", "")
            row[30] = item.get("hotColdNet4AE", "")
            row[31] = item.get("moistDryNet4AF", "")
            ag = item.get("numberAG", "")
            row[32] = "" if ag == "" or ag is None else str(ag)
            row[33] = item.get("dateBforAH", "")
            row[1] = item.get("dateBforAH", "")

        values.append(row)

        if item["isNodeRow"]:
            node_row = list(row)
            node_row[5] = item.get("formattedDateF", "")
            weekday_name, weekday_num, week_start = date_info_from_serial(r[5] if len(r) > 5 else "")
            if weekday_name:
                node_row[4] = weekday_name

            # A new row belongs to a different Monday-Sunday window than the
            # one currently being accumulated -> the previous week is done
            # (even if it never contained a Sunday row, e.g. date gaps).
            # Emits one weekly row per horse seen in that window.
            if week_rows_by_horse and week_start is not None and week_start != current_week_start:
                close_week(week_first_row_num, current_week_start)
                week_first_row_num = None
                current_week_start = None

            node_output_rows.append(node_row)
            week_rows_by_horse.setdefault(_horse_key(r), []).append(node_row)
            if week_first_row_num is None:
                week_first_row_num = len(node_output_rows)
                current_week_start = week_start

        if sheet_id is None:
            continue

        ri = i + row_offset
        if item["isNodeRow"]:
            format_requests.append(bg_color_request(sheet_id, ri, 32, COLOR_YELLOW_PURE))
            continue

        cols_ghi = [
            (6, item["highlightG"], item["elementMatchL"], 11),
            (7, item["highlightH"], item["elementMatchM"], 12),
            (8, item["highlightI"], item["elementMatchN"], 13),
        ]
        for col, hl, match, lcol in cols_ghi:
            if hl == "blue":
                format_requests.append(bg_color_request(sheet_id, ri, col, COLOR_BLUE))
            elif hl == "red":
                format_requests.append(bg_color_request(sheet_id, ri, col, COLOR_RED))
            if match and hl == "blue":
                format_requests.append(bg_color_request(sheet_id, ri, lcol, COLOR_GREEN))

        if item["isStrongestAspect"]:
            format_requests.append(bg_color_request(sheet_id, ri, 10, COLOR_YELLOW))

    # Flush any trailing partial week (data ended before hitting the next
    # week's window, e.g. no Sunday row present) -- still gets its own
    # yellow total row per the "place after the last present day" rule.
    close_week(week_first_row_num, current_week_start)

    return values, format_requests, node_output_rows


# ----- I/O -----

def col_letter(n: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA, 34 -> AH."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def ensure_worksheet(ss: gspread.Spreadsheet, title: str, rows: int = 100, cols: int = 34) -> gspread.Worksheet:
    try:
        return ss.worksheet(title)
    except WorksheetNotFound:
        return ss.add_worksheet(title=title, rows=rows, cols=cols)


def replace_tab(ws: gspread.Worksheet, rows: list[list], n_cols: int,
                chunk_size: int = 2000, sleep_between: float = 0.5) -> None:
    """Clear the worksheet then write rows in retried, chunked batches.

    Header row (rows[0]) is written separately; data rows are written starting
    at A2 in chunks. Each call is wrapped in sheets_retry. Resizes the sheet
    up-front so chunked writes don't need to grow it mid-stream.
    """
    total = max(len(rows), 1)
    if ws.row_count < total:
        sheets_retry(ws.add_rows, total - ws.row_count)
    if ws.col_count < n_cols:
        sheets_retry(ws.add_cols, n_cols - ws.col_count)

    log(f"  clearing {ws.title}...")
    sheets_retry(ws.clear)

    if not rows:
        if ws.row_count > total or ws.col_count > n_cols:
            sheets_retry(ws.resize, rows=total, cols=n_cols)
        return

    last_col = col_letter(n_cols)
    header = rows[0]
    data = rows[1:]

    header_rng = f"A1:{last_col}1"
    log(f"  writing {ws.title} header (1 row, {n_cols} cols)")
    resp = sheets_retry(
        ws.update,
        [header],
        header_rng,
        value_input_option="USER_ENTERED",
    )
    cells = resp.get("updatedCells", 0)
    log(f"    -> updatedCells={cells} updatedRange={resp.get('updatedRange')}")
    if cells != n_cols:
        raise RuntimeError(
            f"{ws.title} header write returned updatedCells={cells}, expected {n_cols} "
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
            log(f"  writing {ws.title} chunk {idx}/{total_chunks}: rows {start_row}-{end_row}")
            resp = sheets_retry(
                ws.update,
                chunk,
                rng,
                value_input_option="USER_ENTERED",
            )
            cells = resp.get("updatedCells", 0)
            total_written += cells
            log(f"    -> updatedCells={cells} updatedRange={resp.get('updatedRange')}")
            if cells != expected:
                raise RuntimeError(
                    f"{ws.title} chunk {idx} returned updatedCells={cells}, expected {expected} "
                    f"(range={rng}, sent {len(chunk)} rows × {n_cols} cols); response={resp}"
                )
            if idx < total_chunks:
                time.sleep(sleep_between)
        log(f"  {ws.title} total cells written: {total_written}")

    if ws.row_count > total or ws.col_count > n_cols:
        sheets_retry(ws.resize, rows=total, cols=n_cols)


def apply_format_requests(ss: gspread.Spreadsheet, requests: list[dict],
                          chunk: int = 500, sleep_between: float = 0.75) -> int:
    """Send formatting batchUpdate in retried chunks of `chunk` requests."""
    if not requests:
        return 0
    sent = 0
    total = len(requests)
    total_chunks = (total + chunk - 1) // chunk
    for idx, i in enumerate(range(0, total, chunk), start=1):
        slice_ = requests[i:i + chunk]
        log(f"  format batch {idx}/{total_chunks}: {len(slice_)} requests")
        sheets_retry(ss.batch_update, {"requests": slice_})
        sent += len(slice_)
        if idx < total_chunks:
            time.sleep(sleep_between)
    return sent


def run() -> None:
    log("[1/5] Reading Aspects sheet (A:E formatted, F unformatted, G:H horse tag)...")
    in_ss = open_sheet(INPUT_SPREADSHEET_ID)
    in_ws = in_ss.worksheet(INPUT_TAB)
    ae_rows = sheets_retry(
        in_ws.get_values,
        "A:E",
        value_render_option="FORMATTED_VALUE",
        date_time_render_option="FORMATTED_STRING",
    )
    f_rows = sheets_retry(
        in_ws.get_values,
        "F:F",
        value_render_option="UNFORMATTED_VALUE",
        date_time_render_option="SERIAL_NUMBER",
    )
    try:
        gh_rows = sheets_retry(
            in_ws.get_values,
            "G:H",
            value_render_option="FORMATTED_VALUE",
            date_time_render_option="FORMATTED_STRING",
        )
    except APIError as exc:  # legacy 6-column Aspects sheet: no horse columns
        log(f"  no G:H horse columns on Aspects ({str(exc)[:80]}); legacy single-point mode")
        gh_rows = []
    n = max(len(ae_rows), len(f_rows), len(gh_rows))
    rows: list[list] = []
    for i in range(n):
        ae = ae_rows[i] if i < len(ae_rows) else []
        f = f_rows[i] if i < len(f_rows) else []
        gh = gh_rows[i] if i < len(gh_rows) else []
        rows.append([
            ae[0] if len(ae) > 0 else "",
            ae[1] if len(ae) > 1 else "",
            ae[2] if len(ae) > 2 else "",
            ae[3] if len(ae) > 3 else "",
            ae[4] if len(ae) > 4 else "",
            f[0] if len(f) > 0 else "",
            gh[0] if len(gh) > 0 else "",
            gh[1] if len(gh) > 1 else "",
        ])
    log(f"  merged {len(rows)} input rows from Aspects")

    # Drop a leading 'Planet' header row once, before grouping (same check
    # process_data() performs on its own first row).
    if rows and str(rows[0][0] or "").strip().lower() == "planet":
        rows.pop(0)

    horse_keys: list[tuple[str, str]] = []
    for r in rows:
        k = (str(r[6]).strip() if len(r) > 6 else "", str(r[7]).strip() if len(r) > 7 else "")
        if k not in horse_keys:
            horse_keys.append(k)
    log(f"  {len(horse_keys)} horse(s): " + ", ".join(f"{no} {name}".strip() or "(no horse)" for no, name in horse_keys))

    log("[2/5] Opening output workbook + ensuring tabs...")
    out_ss = open_sheet(OUTPUT_SPREADSHEET_ID)
    out_ws = ensure_worksheet(out_ss, OUTPUT_TAB, rows=len(rows) + 100, cols=N_OUT_COLS)
    node_ws = ensure_worksheet(out_ss, NODE_OUTPUT_TAB, rows=200, cols=N_OUT_COLS)
    sheet_gid = out_ws.id
    log(f"  output sheetId(gid)={sheet_gid}")

    log(f"[3/5] Running 4-phase processor (date-major; weekly rows {'ON' if WEEKLY_ROWS_ENABLED else 'OFF'})...")
    values, format_requests, node_output_rows = process_data(rows, sheet_gid, node_ws.id)
    per_horse_stats: list[dict] = []
    for h_no, h_name in horse_keys:
        daily = sum(1 for r in node_output_rows if r[HORSE_NO_COL] == h_no and r[4] != "WEEKLY")
        weekly = sum(1 for r in node_output_rows if r[HORSE_NO_COL] == h_no and r[4] == "WEEKLY")
        per_horse_stats.append({"horse": f"{h_no} {h_name}".strip(), "nodeRows": daily, "weeklyRows": weekly})
        log(f"  horse {h_no or '-'} {h_name or '-'}: {daily} Node rows" + (f", {weekly} weekly rows" if WEEKLY_ROWS_ENABLED else ""))
    log(
        f"  built {len(values)} Result Degree rows, "
        f"{len(node_output_rows)} Node_Output rows, "
        f"{len(format_requests)} format requests"
    )

    log(
        f"[4/5] Writing Result Degree ({OUTPUT_TAB}) + Node_Output ({NODE_OUTPUT_TAB})..."
    )
    # Build 60-column Node_Output (A..BH) with frozen Header Row 1, AE=HORSE_NO, AF=HORSE, AG..BH=28 Decan cols
    lotto_headers_60 = [
        "DAY", "DATE", "DEG_SUM_1 (G)", "DEG_SUM_2 (H)", "DEG_SUM_3 (I)", "TEAM (F)", "TOTAL_DEG (K)",
        "ASPECT_EL_1", "ASPECT_EL_2", "ASPECT_EL_3", "TAROT22_1", "TAROT22_2", "TAROT22_3",
        "ZODIAC22_1", "ZODIAC22_2", "ZODIAC22_3", "T22_HC_1", "T22_HC_2", "T22_HC_3",
        "T22_MD_1", "T22_MD_2", "T22_MD_3", "T22_S3_HC (W)", "T22_S3_MD (X)", "T22_S1_EL1 (Y)",
        "T22_S1_EL2 (Z)", "T22_FINAL_HC (AA)", "T22_FINAL_MD (AB)", "NUMBER_AG_22 (AC)", "PRIC_CH (AD)",
        "TEAM_NO (AE)", "TEAM (AF)",
        "DECAN36_1 (AG)", "DECAN36_2 (AH)", "DECAN36_3 (AI)", "DECAN_CARD_1 (AJ)", "DECAN_CARD_2 (AK)",
        "DECAN_CARD_3 (AL)", "DEC_HC_1 (AM)", "DEC_HC_2 (AN)", "DEC_HC_3 (AO)", "DEC_MD_1 (AP)",
        "DEC_MD_2 (AQ)", "DEC_MD_3 (AR)", "DEC_S3_HC (AS)", "DEC_S3_MD (AT)", "DEC_S1_EL1 (AU)",
        "DEC_S1_EL2 (AV)", "DEC_FINAL_HC (AW)", "DEC_FINAL_MD (AX)", "DEC_NUMBER_AG (AY)",
        "DEC_MODALITY_SUMMARY (AZ)", "GD_CARD_HC (BA)", "GD_CARD_MD (BB)", "GD_NUMBER_AG (BC)",
        "DEC_ELE_P (BD)", "DEC_GEO_FIG (BE)", "RULER_HC (BF)", "RULER_MD (BG)", "RULER_GEO_FIG (BH)",
    ]
    _SIGNS_36 = [("Aries","Fire","Cardinal","Wands"),("Taurus","Earth","Fixed","Pentacles"),("Gemini","Air","Mutable","Swords"),("Cancer","Water","Cardinal","Cups"),("Leo","Fire","Fixed","Wands"),("Virgo","Earth","Mutable","Pentacles"),("Libra","Air","Cardinal","Swords"),("Scorpio","Water","Fixed","Cups"),("Sagittarius","Fire","Mutable","Wands"),("Capricorn","Earth","Cardinal","Pentacles"),("Aquarius","Air","Fixed","Swords"),("Pisces","Water","Mutable","Cups")]
    _RULERS_7 = ["Mars","Sun","Venus","Mercury","Moon","Saturn","Jupiter"]
    _RULER_EL = {"Mars":"Fire","Sun":"Fire","Venus":"Water","Mercury":"Earth","Moon":"Water","Saturn":"Earth","Jupiter":"Air"}
    _EL_QUAL = {"Fire":(1,-1,"Hot","Dry"),"Earth":(-1,-1,"Cold","Dry"),"Air":(1,1,"Hot","Moist"),"Water":(-1,1,"Cold","Moist")}
    _GEO_BITS = {0:[0,0,0,0],1:[0,0,0,1],2:[0,0,1,0],3:[0,0,1,1],4:[0,1,0,0],5:[0,1,0,1],6:[0,1,1,0],7:[0,1,1,1],8:[1,0,0,0],9:[1,0,0,1],10:[1,0,1,0],11:[1,0,1,1],12:[1,1,0,0],13:[1,1,0,1],14:[1,1,1,0],15:[1,1,1,1]}
    _WDAY_NUM = {"MONDAY":9,"TUESDAY":5,"WEDNESDAY":8,"THURSDAY":4,"FRIDAY":7,"SATURDAY":6,"SUNDAY":3}
    # Dynamic (F, F2, F3) lookup directly from NBA-Astro_Input so Home/Away DEG2 & DEG3 flow 100% dynamically!
    _ASTRO_F_MAP = {}
    try:
        _astro_ss = open_sheet(os.environ.get("TENNIS_ASTRO_INPUT_SHEET_ID", ""))
        for _ar in _astro_ss.sheet1.get_values("A2:K50000", value_render_option="UNFORMATTED_VALUE"):
            if len(_ar) >= 11:
                _dt_k = str(_ar[0]).strip()
                _tno_k = str(_ar[9]).strip()
                _tnm_k = str(_ar[10]).strip()
                _f1_v = float(_ar[1]) if _ar[1] not in ("", None) else 71.0
                _f2_v = float(_ar[2]) if _ar[2] not in ("", None) else 132.0
                _f3_v = float(_ar[3]) if _ar[3] not in ("", None) else 363.0
                _ASTRO_F_MAP[(_dt_k, _tno_k, _tnm_k)] = (_f1_v, _f2_v, _f3_v)
                _ASTRO_F_MAP[(_dt_k, _tno_k)] = (_f1_v, _f2_v, _f3_v)
    except Exception as _e:
        log(f"  WARNING: could not load dynamic F/F2/F3 from NBA-Astro_Input: {_e}")
    def _d_meta(d):
        d = ((int(round(float(d))) - 1) % 36) + 1
        si, face = (d - 1) // 3, ((d - 1) % 3) + 1
        sign, se, mod, suit = _SIGNS_36[si]
        cn = (1 if mod == "Cardinal" else (4 if mod == "Fixed" else 7)) + face
        rul = _RULERS_7[(d - 1) % 7]
        re_el = _RULER_EL[rul]
        tc = f"{cn} of {suit}"
        return {"d":d, "label":f"{sign} D{face} ({tc} - {rul}) - [{se}]", "mod":mod, "cn":cn, "rul":rul, "tc":tc,
                "s_hc":_EL_QUAL[se][0], "s_md":_EL_QUAL[se][1], "s_hl":_EL_QUAL[se][2], "s_ml":_EL_QUAL[se][3],
                "r_hc":_EL_QUAL[re_el][0], "r_md":_EL_QUAL[re_el][1]}
    def _fmt_n(v, pos, neg):
        iv = int(round(v))
        return f"{iv} {pos}" if iv > 0 else (f"{abs(iv)} {neg}" if iv < 0 else "0 NEUTRAL")
    def _geo_vec(hc_v, md_v):
        ih, im = abs(int(round(hc_v))), abs(int(round(md_v)))
        f = a = w = e = 0
        for x in (ih // 10, ih % 10, im // 10, im % 10):
            b = _GEO_BITS.get(min(15, max(0, x)), [0,0,0,0])
            f += b[0]; a += b[1]; w += b[2]; e += b[3]
        return f"{f},{a},{w},{e}", chr(39) + f"{f%2}{a%2}{w%2}{e%2}"
    final_node_60 = [lotto_headers_60]
    for raw_r in node_output_rows:
        r32 = list(raw_r[4:36])
        while len(r32) < 32: r32.append("")
        wday_u = str(r32[0] or "").strip().upper()
        dt_s = str(r32[1] or "").strip()
        cv = float(r32[2]) if r32[2] not in ("", None) else 0.0
        dv = float(r32[3]) if r32[3] not in ("", None) else 0.0
        ev = float(r32[4]) if r32[4] not in ("", None) else 0.0
        tno_s = str(r32[30] or "").strip()
        tnm_s = str(r32[31] or "").strip()
        r32[5] = tnm_s
        mg, mh, mi = _d_meta(cv), _d_meta(dv), _d_meta(ev)
        s3_dhc = sum(m["d"] * m["s_hc"] for m in (mg, mh, mi))
        s3_dmd = sum(m["d"] * m["s_md"] for m in (mg, mh, mi))
        try:
            mm, dd, yy = [int(x) for x in dt_s.split("/")]
            fh = _WDAY_NUM.get(wday_u, 3) + sum(int(c) for c in f"{yy:04d}{mm:02d}{dd:02d}")
        except Exception:
            fh = 30
        f_triple = _ASTRO_F_MAP.get((dt_s, tno_s, tnm_s)) or _ASTRO_F_MAP.get((dt_s, tno_s))
        if f_triple is not None:
            mf1, mf2, mf3 = _d_meta(f_triple[0]), _d_meta(f_triple[1]), _d_meta(f_triple[2])
        else:
            mf1, mf2, mf3 = _d_meta(56 + fh), _d_meta(117 + fh), _d_meta(348 + fh)
        s1_dhc = sum(m["d"] * m["s_hc"] for m in (mf1, mf2, mf3))
        s1_dmd = sum(m["d"] * m["s_md"] for m in (mf1, mf2, mf3))
        aw_v, ax_v = s3_dhc + s1_dhc, s3_dmd + s1_dmd
        mods = [mg["mod"], mh["mod"], mi["mod"]]
        bm = max(("Cardinal","Fixed","Mutable"), key=lambda x: mods.count(x))
        dom = bm.upper() if mods.count(bm) >= 2 else "BALANCED"
        trio = f"D{mf1['d']}/D{mf2['d']}/D{mf3['d']} ({mf1['tc']}-{mf1['rul']} | {mf2['tc']}-{mf2['rul']} | {mf3['tc']}-{mf3['rul']})"
        all6 = (mg, mh, mi, mf1, mf2, mf3)
        ba_v = sum(m["cn"] * m["s_hc"] for m in all6)
        bb_v = sum(m["cn"] * m["s_md"] for m in all6)
        bf_v = sum(m["cn"] * m["r_hc"] for m in all6)
        bg_v = sum(m["cn"] * m["r_md"] for m in all6)
        v_gd, c_gd = _geo_vec(ba_v, bb_v)
        _, c_rl = _geo_vec(bf_v, bg_v)
        r32.extend([
            mg["d"], mh["d"], mi["d"], mg["label"], mh["label"], mi["label"],
            f"{mg['d']}{mg['s_hl']}", f"{mh['d']}{mh['s_hl']}", f"{mi['d']}{mi['s_hl']}",
            f"{mg['d']}{mg['s_ml']}", f"{mh['d']}{mh['s_ml']}", f"{mi['d']}{mi['s_ml']}",
            _fmt_n(s3_dhc, "HOT", "COLD"), _fmt_n(s3_dmd, "MOIST", "DRY"),
            _fmt_n(s1_dhc, "HOT", "COLD"), _fmt_n(s1_dmd, "MOIST", "DRY"),
            _fmt_n(aw_v, "HOT", "COLD"), _fmt_n(ax_v, "MOIST", "DRY"),
            str(int(f"{abs(int(ax_v))}{abs(int(aw_v))}")), f"/".join(mods) + f" [{dom}] | {trio}",
            _fmt_n(ba_v, "HOT", "COLD"), _fmt_n(bb_v, "MOIST", "DRY"),
            str(int(f"{abs(int(bb_v))}{abs(int(ba_v))}")), v_gd, c_gd,
            _fmt_n(bf_v, "HOT", "COLD"), _fmt_n(bg_v, "MOIST", "DRY"), c_rl,
        ])
        final_node_60.append(r32)
    node_ws = ensure_worksheet(out_ss, NODE_OUTPUT_TAB, rows=len(final_node_60) + 10, cols=60)
    replace_tab(node_ws, final_node_60, 60)
    replace_tab(out_ws, values, N_OUT_COLS)
    log("  values + Node_Output written successfully")

    sent = 0
    format_status = "OK"
    format_error: str | None = None
    if not FORMAT_ENABLED or len(values) > 10000:
        log("[5/5] Formatting skipped (FORMAT_ENABLED=False)")
        format_status = "SKIPPED"
    elif not format_requests:
        log("[5/5] No format requests to apply")
    else:
        log(f"[5/5] Applying {len(format_requests)} background-color requests in chunks...")
        try:
            sent = apply_format_requests(out_ss, format_requests)
            log(f"  formatting complete: {sent}/{len(format_requests)} applied")
        except APIError as exc:
            format_status = "WARNING"
            format_error = str(exc)
            log(f"  WARNING: formatting failed after values were written: {exc}")

    msg_parts = [
        f"Wrote {len(values)} Result Degree rows",
        f"{len(node_output_rows)} Node_Output rows",
        f"applied {sent}/{len(format_requests)} color formats" if format_requests else "no color formats",
    ]
    if format_status == "SKIPPED":
        msg_parts.append("(formatting skipped)")
    elif format_status == "WARNING":
        msg_parts.append("(formatting WARNING — values OK)")
    msg = "; ".join(msg_parts)

    log(f"Step 3 complete: {msg}")
    emit_result(
        ok=True,
        rows_written=len(values),
        message=msg,
        extra={
            "nodeRows": len(node_output_rows),
            "horses": len(horse_keys),
            "perHorse": per_horse_stats,
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
        emit_result(ok=False, error=str(e), message="Step 3 failed")
        sys.exit(1)
