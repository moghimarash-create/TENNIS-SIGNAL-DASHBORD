"""Step 2 - NEW-ASTRO-ASPECTS (pyswisseph).

Reads Astro_Input!Data (A:K) + Astro_Header_Input!Sheet1 (A:G),
computes planetary aspects against F/F2/F3/E "label degrees" using
swisseph, and replaces the contents of the Aspects sheet (Sheet1).

LOTTO / 12-HORSE MODE: Astro_Input carries 12 rows per DATE (one per horse,
cols J=HORSE_NO, K=HORSE) and Astro_Header_Input carries the matching
12 header rows (F=HORSE_NO, G=HORSE).  Each (DATE, HORSE) pair becomes its
own block in Aspects: one date-header row followed by the 12 planet rows.
The aspect computation itself is unchanged; only the block key gained the
horse and two tag columns were appended.

Output rows are 8 columns wide:
  - Date-header rows: (DATE, PRIC, WEEKDAY, EL1, EL2, "", HORSE_NO, HORSE)
  - Per-planet rows:  [PlanetName, sym1, sym2, sym3, sym4, date_key, HORSE_NO, HORSE]
Without horse columns (legacy input) the key falls back to DATE only and
cols G/H are left blank, so the old 6-column behaviour is preserved.
"""
import os
import sys
import traceback
from datetime import datetime

import pytz
import requests
import swisseph as swe

from _lib.runner import emit_result, log
from _lib.sheets import open_sheet

INPUT_DATA_SHEET_ID = os.environ.get("TENNIS_ASTRO_INPUT_SHEET_ID", "")
INPUT_DATA_TAB = "Data"
INPUT_HEADER_SHEET_ID = os.environ.get("TENNIS_ASTRO_HEADER_SHEET_ID", "")
INPUT_HEADER_TAB = "Sheet1"
OUTPUT_SHEET_ID = os.environ.get("TENNIS_ASTRO_ASPECTS_SHEET_ID", "")
OUTPUT_TAB = "Sheet1"

EPHE_URL = "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/seas_18.se1"
EPHE_PATH = "/tmp"
EPHE_FILE = "/tmp/seas_18.se1"


def _init_ephe():
    if not os.path.exists(EPHE_FILE):
        log("Downloading swisseph ephemeris file...")
        r = requests.get(EPHE_URL, timeout=30)
        r.raise_for_status()
        with open(EPHE_FILE, "wb") as f:
            f.write(r.content)
    swe.set_ephe_path(EPHE_PATH)


ASPECTS = [
    ("\u2609", 0,          9),
    ("\u260D", 180,        9),
    ("\u25B3", 120,        9),
    ("\u25A1", 90,         9),
    ("\u2217", 60,         6),
    ("\u26BB", 150,        3),
    ("\u26BA", 30,         2),
    ("\u2220", 45,         2.5),
    ("\u26BC", 135,        2.5),
    ("Q",   72,         2.5),
    ("bQ",  144,        2.5),
    ("D",   36,         2),
    ("D3",  108,        2),
    ("S",   51.428571,  2),
    ("S2",  102.857143, 2),
    ("S3",  154.285714, 2),
    ("N",   40,         2),
    ("N2",  80,         2),
    ("N4",  160,        2),
    ("U",   32.727273,  2),
    ("U2",  65.454545,  2),
    ("U3",  98.181818,  2),
    ("U4",  130.909091, 2),
    ("U5",  163.636363, 2),
]

PLANETS = [
    ("Sun",     swe.SUN),
    ("Moon",    swe.MOON),
    ("Mercury", swe.MERCURY),
    ("Venus",   swe.VENUS),
    ("Mars",    swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturn",  swe.SATURN),
    ("Uranus",  swe.URANUS),
    ("Neptune", swe.NEPTUNE),
    ("Pluto",   swe.PLUTO),
    ("Node",    swe.TRUE_NODE),
    ("Chiron",  swe.CHIRON),
]

TZ_MAP = {
    "EST": "US/Eastern",
    "EDT": "US/Eastern",
    "PST": "US/Pacific",
    "PDT": "US/Pacific",
    "CST": "US/Central",
    "UTC": "UTC",
}

SUN_MOON = {"Sun", "Moon"}


def _best_aspect(label_deg, planet_deg, planet_name):
    orb_bonus = 1.0 if planet_name in SUN_MOON else 0.0
    diff = abs(label_deg - planet_deg)
    if diff > 180.0:
        diff = 360.0 - diff
    best_sym = None
    best_d = None
    for sym, ang, orb in ASPECTS:
        d = abs(diff - ang)
        if d <= orb + orb_bonus:
            if best_d is None or d < best_d:
                best_d = d
                best_sym = sym
    return best_sym


def compute(rows_main, rows_headers):
    _init_ephe()

    errors: list[str] = []
    output_rows: list[list] = []
    processed_input_rows = 0

    def _horse_tag(row, no_idx, name_idx):
        """(HORSE_NO as str, HORSE name) from a row, or ('', '') if absent."""
        no = str(row[no_idx]).strip() if len(row) > no_idx and row[no_idx] is not None else ""
        name = str(row[name_idx]).strip() if len(row) > name_idx and row[name_idx] is not None else ""
        return no, name

    # key = (date, horse_no) ; horse_no == "" for legacy single-point input
    header_dates: dict[tuple, list] = {}
    for r in rows_headers:
        if len(r) > 0:
            h_no, _h_name = _horse_tag(r, 5, 6)
            header_dates[(str(r[0]).strip(), h_no)] = r

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    dates_inserted: set[tuple] = set()

    for r in rows_main:
        if len(r) < 9:
            continue
        if r[0] in ("date", "Date", "DATE"):
            continue

        try:
            date_str = r[0]
            f1 = r[1]
            f2 = r[2]
            f3 = r[3] if len(r) > 3 else None
            E = r[4] if len(r) > 4 else None
            time_str = r[5]
            tz_str = r[6]
            horse_no, horse_name = _horse_tag(r, 9, 10)

            tz_name = TZ_MAP.get(tz_str.strip(), tz_str.strip())
            tz = pytz.timezone(tz_name)

            time_clean = time_str.strip()
            if "AM" in time_clean.upper() or "PM" in time_clean.upper():
                _t = datetime.strptime(time_clean.upper().replace(".", ""), "%I:%M %p")
                hour = _t.hour
                minute = _t.minute
            else:
                time_parts = time_clean.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0

            date_parts = date_str.strip().split("/")
            if len(date_parts) == 3:
                m, d, y = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
            else:
                date_parts = date_str.strip().split("-")
                y, m, d = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])

            local_dt = tz.localize(datetime(y, m, d, hour, minute, 0))
            utc_dt = local_dt.astimezone(pytz.utc)

            jd = swe.julday(
                utc_dt.year, utc_dt.month, utc_dt.day,
                utc_dt.hour + utc_dt.minute / 60.0,
            )

            date_key = date_str.strip()
            block_key = (date_key, horse_no)

            if block_key in header_dates and block_key not in dates_inserted:
                src = list(header_dates[block_key])
                # A..E from Astro_Header_Input, F blank (as before), G/H = horse tag
                header_row = [src[c] if c < len(src) else "" for c in range(5)]
                header_row += ["", horse_no, horse_name]
                output_rows.append(header_row)
                dates_inserted.add(block_key)

            labels = [f1, f2, f3 if f3 is not None else "", E if E is not None else ""]

            for pname, pid in PLANETS:
                result = swe.calc_ut(jd, pid, flags)
                p_deg = result[0][0] % 360.0

                row_out = [pname]
                for label_val in labels:
                    lv = str(label_val).strip() if label_val is not None else ""
                    if lv == "":
                        row_out.append("")
                    else:
                        try:
                            label_deg = float(lv) % 360.0
                        except (ValueError, TypeError):
                            row_out.append("")
                            continue
                        sym = _best_aspect(label_deg, p_deg, pname)
                        row_out.append(sym if sym is not None else "")

                row_out.append(date_key)
                row_out.append(horse_no)
                row_out.append(horse_name)
                output_rows.append(row_out)

            processed_input_rows += 1

            if processed_input_rows % 200 == 0:
                log(f"  Processed {processed_input_rows} input rows...")

        except Exception as e:
            errors.append(f"row {r[0] if r else '?'}: {e}")

    return output_rows, processed_input_rows, errors


OUTPUT_COLS = 8
WRITE_CHUNK = 20000


def write_output(rows: list[list]) -> None:
    """Replace OUTPUT_TAB contents wholesale with rows. Each row is 8 columns wide.

    Written in chunks: 12 horses multiply the row count, and a single
    values.update request has a payload-size limit.
    """
    ws = open_sheet(OUTPUT_SHEET_ID).worksheet(OUTPUT_TAB)
    total_rows = max(len(rows), 1)
    ncols = OUTPUT_COLS
    if ws.row_count < total_rows:
        ws.add_rows(total_rows - ws.row_count)
    if ws.col_count < ncols:
        ws.add_cols(ncols - ws.col_count)
    ws.clear()
    for start in range(0, len(rows), WRITE_CHUNK):
        chunk = [list(r) + [""] * (ncols - len(r)) for r in rows[start:start + WRITE_CHUNK]]
        ws.update(range_name=f"A{start + 1}:H{start + len(chunk)}", values=chunk)
        log(f"  wrote rows {start + 1}-{start + len(chunk)}")
    if ws.row_count > total_rows or ws.col_count > ncols:
        ws.resize(rows=total_rows, cols=ncols)


def run() -> None:
    log("[1/3] Reading Astro_Input!Data (A:K) and Astro_Header_Input!Sheet1 (A:G)...")
    main_ws = open_sheet(INPUT_DATA_SHEET_ID).worksheet(INPUT_DATA_TAB)
    rows_main = main_ws.get_values("A:K")
    header_ws = open_sheet(INPUT_HEADER_SHEET_ID).worksheet(INPUT_HEADER_TAB)
    rows_headers = header_ws.get_values("A:G")
    n_horses = len({str(r[9]).strip() for r in rows_main[1:] if len(r) > 9 and str(r[9]).strip()})
    log(f"  rows_main={len(rows_main)} rows_headers={len(rows_headers)} horses={n_horses or 'none (legacy)'}")

    log("[2/3] Computing aspects with swisseph...")
    output_rows, processed, errors = compute(rows_main, rows_headers)
    log(
        f"  produced {len(output_rows)} output rows from {processed} inputs "
        f"({len(errors)} input errors)"
    )
    if errors[:5]:
        log("  First errors: " + "; ".join(errors[:5]))

    log(f"[3/3] Writing {len(output_rows)} rows to Aspects/{OUTPUT_TAB}...")
    write_output(output_rows)

    msg = f"Wrote {len(output_rows)} aspect rows from {processed} inputs"
    if errors:
        msg += f" ({len(errors)} input rows skipped)"
    emit_result(
        ok=True,
        rows_written=len(output_rows),
        message=msg,
        extra={"processedInputs": processed, "inputErrors": len(errors), "horses": n_horses},
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log("ERROR: " + str(e))
        log(traceback.format_exc())
        emit_result(ok=False, error=str(e), message="Step 2 failed")
        sys.exit(1)
