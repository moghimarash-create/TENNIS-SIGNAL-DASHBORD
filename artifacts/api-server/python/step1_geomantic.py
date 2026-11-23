"""Step 1 - Dynamic NBA Geomantic Calculator (Home vs. Away Dynamic DEG2 & DEG3).

Reads NBA-GEOMANTIC-INPUT (leftmost tab Sheet1) + its NBA-GEM tab and writes:
  - NBA-Astro_Input          (DATE, F, F2, F3, E, Time, Zone, Lat, Lon, TEAM_NO, TEAM)
  - NBA-Astro_Header_Input   (DATE, PRIC, WEEKDAY, EL1, EL2, TEAM_NO, TEAM)

DYNAMIC HOME / AWAY LOGIC:
  - DEG1 is fixed per row from Sheet1.DEG1 (default 56).
  - DEG2 is dynamic per team: TEM-GEM(DEG2) = MOD(EnglishGem(Team_Name), 360).
      * For the Home row: DEG2 = Home Team's TEM-GEM(DEG2)
      * For the Away row: DEG2 = Away Team's TEM-GEM(DEG2)
  - DEG3 is dynamic based on the Host (Home) Stadium where the game is played:
      SUM-CITY-ARENA(DEG3) = MOD(EnglishGem(Home_State), 360) + MOD(EnglishGem(Home_Arena), 360).
      Both the Home team and the Away team in that game receive the Host (Home) Stadium's
      DEG3, Latitude, Longitude, and IANA Timezone!
  - Supported modes per row in Sheet1 (via HOME_TEAM and AWAY_TEAM columns):
      1. Head-to-Head Matchup (HOME_TEAM = Team A, AWAY_TEAM = Team B):
         Produces 2 rows for that date:
           - Row 1: Team A (HOME @ <Home Arena>) -> DEG2 = TeamA.deg2, DEG3 = TeamA.deg3
           - Row 2: Team B (AWAY @ <Home Code>)  -> DEG2 = TeamB.deg2, DEG3 = TeamA.deg3 (Host Arena!)
      2. Host Arena vs All Teams (HOME_TEAM = Team A, AWAY_TEAM = "ALL"):
         Produces 30 rows in Team A's stadium (DEG3 = TeamA.deg3, Lat/Lon/Zone = TeamA's arena),
         with Team A marked (HOME) and the other 29 teams marked (AWAY @ <Home Code>).
      3. All 30 Teams Home Baseline (HOME_TEAM = "ALL" or blank):
         Produces 30 rows where each team is evaluated in its own home arena.
"""
import os
import re
import sys
import traceback
from datetime import datetime, timedelta

from _lib.runner import emit_result, log
from _lib.sheets import open_sheet

INPUT_SHEET_ID = os.environ.get("TENNIS_DASHBORD_INPUT_SHEET_ID", "")
OUTPUT_SHEET_ID = os.environ.get("TENNIS_ASTRO_INPUT_SHEET_ID", "")
HEADER_SHEET_ID = os.environ.get("TENNIS_ASTRO_HEADER_SHEET_ID", "")

NBA_GEM_TAB = "NBA-GEM"
import os, json

TEAM_CODE_DEG2 = {
    "Denver Nuggets": ("DEN", 59, "29 TAURUS"),
    "Minnesota Timberwolves": ("MIN", 100, "10 CANCER"),
    "Oklahoma City Thunder": ("OKC", 110, "20 CANCER"),
    "Portland Trail Blazers": ("POR", 350, "20 PISCES"),
    "Utah Jazz": ("UTA", 47, "17 TAURUS"),
    "Golden State Warriors": ("GSW", 69, "9 GEMINI"),
    "Los Angeles Clippers": ("LAC", 51, "21 TAURUS"),
    "LA Clippers": ("LAC", 51, "21 TAURUS"),
    "Los Angeles Lakers": ("LAL", 61, "1 GEMINI"),
    "Phoenix Suns": ("PHX", 158, "8 VIRGO"),
    "Sacramento Kings": ("SAC", 81, "21 GEMINI"),
    "Dallas Mavericks": ("DAL", 35, "5 TAURUS"),
    "Houston Rockets": ("HOU", 84, "24 GEMINI"),
    "Memphis Grizzlies": ("MEM", 85, "25 GEMINI"),
    "New Orleans Pelicans": ("NOP", 200, "20 LIBRA"),
    "San Antonio Spurs": ("SAS", 121, "1 LEO"),
    "Boston Celtics": ("BOS", 132, "12 LEO"),
    "Brooklyn Nets": ("BKN", 72, "12 GEMINI"),
    "New York Knicks": ("NYK", 80, "20 GEMINI"),
    "Philadelphia 76ers": ("PHI", 98, "8 CANCER"),
    "Toronto Raptors": ("TOR", 310, "10 AQUARIUS"),
    "Chicago Bulls": ("CHI", 38, "8 TAURUS"),
    "Cleveland Cavaliers": ("CLE", 55, "25 TAURUS"),
    "Detroit Pistons": ("DET", 49, "19 TAURUS"),
    "Indiana Pacers": ("IND", 64, "4 GEMINI"),
    "Milwaukee Bucks": ("MIL", 80, "20 GEMINI"),
    "Atlanta Hawks": ("ATL", 71, "11 GEMINI"),
    "Charlotte Hornets": ("CHA", 29, "29 ARIES"),
    "Miami Heat": ("MIA", 51, "21 TAURUS"),
    "Orlando Magic": ("ORL", 300, "0 AQUARIUS"),
    "Washington Wizards": ("WAS", 67, "7 GEMINI"),
}

def _get_deg2_mode():
    for p in [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/schedule_sync_state.json")),
        "/home/runner/workspace/artifacts/api-server/data/schedule_sync_state.json",
        "/home/runner/workspace/data/schedule_sync_state.json",
    ]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("deg2Mode") in ("code", "full"):
                    return d["deg2Mode"]
            except Exception:
                pass
    return "full"

TEAMS_EXPECTED = 30

DEFAULT_TIME = "19:30"
DEFAULT_ZONE = "America/New_York"
DEFAULT_LAT = "40.750513"
DEFAULT_LON = "-73.993516"

WEEKDAY_NUM = {
    "Monday": 9, "Tuesday": 5, "Wednesday": 8,
    "Thursday": 4, "Friday": 7, "Saturday": 6, "Sunday": 3,
}

SHEETS_EPOCH = datetime(1899, 12, 30)


def serial_to_date(serial):
    return (SHEETS_EPOCH + timedelta(days=int(serial))).date()


def normalize_date(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return serial_to_date(value)
    s = str(value).strip()
    parts = s.split("/")
    if len(parts) != 3:
        raise ValueError(f"Bad date format: {value!r}")
    m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
    return datetime(y, m, d).date()


def digital_sum_from_date(dt):
    return sum(int(c) for c in f"{dt.year:04d}{dt.month:02d}{dt.day:02d}")


def format_time_value(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        frac = float(value) % 1.0
        total_minutes = int(round(frac * 24 * 60))
        hours_24, minutes = divmod(total_minutes, 60)
        hours_24 %= 24
        suffix = "AM" if hours_24 < 12 else "PM"
        hours_12 = hours_24 % 12 or 12
        return f"{hours_12}:{minutes:02d} {suffix}"
    return str(value).strip()


def calc_from_date(dt, weekday, deg1, deg2, deg3):
    weekday = weekday.strip()
    actual_wd = dt.strftime("%A")
    if actual_wd != weekday:
        weekday = actual_wd
    day_num = WEEKDAY_NUM[weekday]
    d_sum = digital_sum_from_date(dt)
    f_helper = day_num + d_sum
    p1 = int(float(deg1)) + f_helper
    p2 = int(float(deg2)) + f_helper
    p3 = int(float(deg3)) + f_helper
    return f"{dt.month}/{dt.day}/{dt.year}", weekday, p1, p2, p3


ARCANUM_TO_CARD = {
    1:  "Scorpio - [Water]",   2:  "Leo - [Fire]",
    3:  "Gemini - [Air]",      4:  "Aries - [Fire]",
    5:  "Gemini - [Air]",      6:  "Gemini - [Air]",
    7:  "Capricorn - [Earth]", 8:  "Libra - [Air]",
    9:  "Capricorn - [Earth]", 10: "Gemini - [Air]",
    11: "Taurus - [Earth]",    12: "Cancer - [Water]",
    13: "Gemini - [Air]",      14: "Leo - [Fire]",
    15: "Aries - [Fire]",      16: "Gemini - [Air]",
    17: "Taurus - [Earth]",    18: "Scorpio - [Water]",
    19: "Capricorn - [Earth]", 20: "Leo - [Fire]",
    21: "Aquarius - [Air]",    22: "Virgo - [Earth]",
}

ELEMENT_QUALITIES = {
    "Fire":  ("HOT",  "DRY"),
    "Earth": ("COLD", "DRY"),
    "Air":   ("HOT",  "MOIST"),
    "Water": ("COLD", "MOIST"),
}

_ELEM_RE = re.compile(r"\[(\w+)\]")


def _arcanum(value):
    r = value % 22
    return 22 if r == 0 else r


def _element(arcanum):
    card = ARCANUM_TO_CARD.get(arcanum, "")
    m = _ELEM_RE.search(card)
    return m.group(1) if m else ""


def _net(values, positive_label, negative_label):
    pos = sum(n for n, t in values if t == positive_label)
    neg = sum(n for n, t in values if t == negative_label)
    diff = pos - neg
    if diff > 0:
        return f"{diff} {positive_label}"
    if diff < 0:
        return f"{abs(diff)} {negative_label}"
    return "0 NEUTRAL"


def calc_el1_el2(p_digs):
    main_pairs, sub_pairs = [], []
    for p in p_digs:
        arc = _arcanum(int(p))
        elem = _element(arc)
        if not elem:
            continue
        primary, secondary = ELEMENT_QUALITIES[elem]
        main_pairs.append((arc, primary))
        sub_pairs.append((arc, secondary))
    return (
        _net(main_pairs, "HOT", "COLD"),
        _net(sub_pairs, "MOIST", "DRY"),
    )


def _zodiac_label(deg):
    signs = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO",
             "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES"]
    d = int(deg) % 360
    return f"{d % 30} {signs[d // 30]}"


def load_nba_teams(spreadsheet):
    """Read the NBA-GEM tab -> list of 30 team dicts + lookup by name/code/no."""
    ws = spreadsheet.worksheet(NBA_GEM_TAB)
    rows = ws.get_values(
        value_render_option="UNFORMATTED_VALUE",
        date_time_render_option="SERIAL_NUMBER",
    )
    if not rows or len(rows) < 2:
        raise RuntimeError(f"Tab '{NBA_GEM_TAB}' is empty")

    teams = []
    lookup = {}
    for idx, r in enumerate(rows[1:], start=1):
        if not r or str(r[0]).strip() == "":
            continue
        name = str(r[0]).strip()
        deg2_full = int(float(r[3]))
        code_tmp = str(r[17]).strip() if len(r) > 17 else ""
        deg2_code = int(float(r[24])) if len(r) > 24 and str(r[24]).strip() != "" else TEAM_CODE_DEG2.get(name, (code_tmp, deg2_full, ""))[1]
        deg2 = deg2_code if _get_deg2_mode() == "code" else deg2_full
        state = str(r[6]).strip() if len(r) > 6 else ""
        arena = str(r[7]).strip() if len(r) > 7 else ""
        deg3 = int(float(r[13]))
        no = int(float(r[16])) if len(r) > 16 and str(r[16]).strip() != "" else idx
        code = str(r[17]).strip() if len(r) > 17 else ""
        conf = str(r[18]).strip() if len(r) > 18 else ""
        lat = str(r[21]).strip() if len(r) > 21 and str(r[21]).strip() != "" else DEFAULT_LAT
        lon = str(r[22]).strip() if len(r) > 22 and str(r[22]).strip() != "" else DEFAULT_LON
        tz = str(r[23]).strip() if len(r) > 23 and str(r[23]).strip() != "" else "America/New_York"
        t = {
            "no": no,
            "name": name,
            "code": code,
            "conf": conf,
            "state": state,
            "arena": arena,
            "deg2": deg2,
            "deg3": deg3,
            "sign2": _zodiac_label(deg2),
            "sign3": _zodiac_label(deg3),
            "lat": lat,
            "lon": lon,
            "tz": tz,
        }
        teams.append(t)
        lookup[name.upper()] = t
        if code:
            lookup[code.upper()] = t
        lookup[str(no)] = t

    log(f"  Loaded {len(teams)} NBA teams from '{NBA_GEM_TAB}'")
    return teams, lookup


def _write_sheet(ws, header, rows, last_col_letter, label, chunk_size=5000):
    ncols = len(header)
    total_rows = len(rows) + 1
    payload = [header] + rows
    if ws.row_count < total_rows:
        ws.add_rows(total_rows - ws.row_count)
    if ws.col_count < ncols:
        ws.add_cols(ncols - ws.col_count)
    ws.clear()
    for start in range(0, len(payload), chunk_size):
        chunk = payload[start:start + chunk_size]
        ws.update(
            range_name=f"A{start + 1}:{last_col_letter}{start + len(chunk)}",
            values=chunk,
        )
    if ws.row_count > total_rows or ws.col_count > ncols:
        ws.resize(rows=total_rows, cols=ncols)
    n_chunks = (len(payload) + chunk_size - 1) // chunk_size
    log(f"  Wrote {len(rows)} data rows to {label} in {n_chunks} chunk(s)")


def run() -> None:
    log("[1/5] Opening INPUT sheet (NBA-GEOMANTIC-INPUT)...")
    input_ss = open_sheet(INPUT_SHEET_ID)
    input_ws = input_ss.sheet1
    input_rows = input_ws.get_values(
        value_render_option="UNFORMATTED_VALUE",
        date_time_render_option="SERIAL_NUMBER",
    )
    log(f"  Found {len(input_rows)} rows (including header)")

    teams, team_lookup = load_nba_teams(input_ss)
    header_row = [str(c).strip().upper() for c in (input_rows[0] if input_rows else [])]

    def col_idx(*aliases):
        for a in aliases:
            a = a.upper()
            if a in header_row:
                return header_row.index(a)
        return None

    idx_date      = col_idx("DATE")
    idx_weekday   = col_idx("WEEKDAY")
    idx_pric      = col_idx("PRIC-CH", "PRIC", "PRICE")
    idx_team      = col_idx("TEAM")
    idx_role      = col_idx("ROLE")
    idx_host      = col_idx("HOST_TEAM")
    idx_home      = col_idx("HOME_TEAM", "HOME")
    idx_away      = col_idx("AWAY_TEAM", "AWAY")
    idx_deg1      = col_idx("DEG1")
    idx_home_deg2 = col_idx("HOME_DEG2", "DEG2")
    idx_away_deg2 = col_idx("AWAY_DEG2")
    idx_deg3      = col_idx("ARENA_DEG3", "DEG3")
    idx_time      = col_idx("TIME")
    idx_zone      = col_idx("ZONE")
    idx_lat       = col_idx("LAT")
    idx_lon       = col_idx("LON")

    missing = [n for n, i in [("DATE", idx_date), ("DEG1", idx_deg1)] if i is None]
    if missing:
        raise RuntimeError(f"Missing required input columns: {missing}. Header was: {header_row}")

    log("[2/5] Running Dynamic Home/Away NBA calculations...")
    astro_rows: list[list] = []
    header_rows: list[list] = []
    sheet1_el_updates: list[list] = []
    errors = 0
    repaired = 0
    last_valid_date = None
    last_valid_idx = None
    dates_done = 0

    def _cell_str(row, idx, default=""):
        if idx is not None and len(row) > idx and row[idx] not in ("", None):
            return str(row[idx]).strip()
        return default

    def _cell_int(row, idx, default=None):
        s = _cell_str(row, idx, "")
        if s != "":
            try:
                return int(float(s))
            except (ValueError, TypeError):
                return default
        return default

    for i, row in enumerate(input_rows):
        if i == 0:
            continue
        if not row or len(row) <= idx_date:
            continue
        date_value = row[idx_date]
        if date_value in ("", None):
            continue

        try:
            is_broken = (not isinstance(date_value, (int, float))
                         and str(date_value).strip() in ("########", "", "None"))
            if is_broken:
                if last_valid_date is None:
                    raise ValueError("no anchor yet to repair from")
                dt = last_valid_date + timedelta(days=(i - last_valid_idx))
                repaired += 1
            else:
                dt = normalize_date(date_value)

            weekday = _cell_str(row, idx_weekday, dt.strftime("%A"))
            if weekday not in WEEKDAY_NUM:
                weekday = dt.strftime("%A")

            deg1_val = _cell_int(row, idx_deg1, 56)
            time_raw = row[idx_time] if (idx_time is not None and len(row) > idx_time and row[idx_time] not in ("", None)) else DEFAULT_TIME
            time_v = format_time_value(time_raw)
            pric_ch = row[idx_pric] if (idx_pric is not None and len(row) > idx_pric) else ""

            team_key = _cell_str(row, idx_team, "").upper() if idx_team is not None else ""
            role_key = _cell_str(row, idx_role, "").upper() if idx_role is not None else ""
            host_key = _cell_str(row, idx_host, "").upper() if idx_host is not None else ""

            home_key = _cell_str(row, idx_home, "ALL").upper()
            away_key = _cell_str(row, idx_away, "ALL").upper()

            single_team = team_lookup.get(team_key) if team_key else None
            host_team = team_lookup.get(host_key) if host_key else single_team
            home_team = team_lookup.get(home_key)
            away_team = team_lookup.get(away_key)

            # Build dynamic list of (team_no, display_label, deg2, deg3, tz, lat, lon, row_pch)
            row_entries = []
            if single_team and host_team:
                # 2-Row-Per-Game Mode: If deg2Mode is set, use single_team["deg2"] (which reflects Full vs 3-Letter Code mode!)
                row_deg2 = single_team["deg2"]
                arena_deg3 = _cell_int(row, idx_deg3, host_team["deg3"])
                r_zone = _cell_str(row, idx_zone, host_team["tz"])
                if r_zone.upper() in ("AUTO", "TEAM", "NBA-GEM", ""):
                    r_zone = host_team["tz"]
                r_lat = _cell_str(row, idx_lat, host_team["lat"])
                r_lon = _cell_str(row, idx_lon, host_team["lon"])
                if "AWAY" in role_key:
                    lbl = f"{single_team['name']} [AWAY @ {host_team['code']}]"
                else:
                    lbl = f"{single_team['name']} [HOME @ {host_team['arena']}]"
                row_entries.append((
                    single_team["no"],
                    lbl,
                    row_deg2,
                    arena_deg3,
                    r_zone,
                    r_lat,
                    r_lon,
                    pric_ch,
                ))
            elif home_team and away_team:
                h_deg2 = home_team["deg2"]
                a_deg2 = away_team["deg2"]
                arena_deg3 = _cell_int(row, idx_deg3, home_team["deg3"])

                r_zone = _cell_str(row, idx_zone, home_team["tz"])
                if r_zone.upper() in ("AUTO", "TEAM", "NBA-GEM", ""):
                    r_zone = home_team["tz"]
                r_lat = _cell_str(row, idx_lat, home_team["lat"])
                r_lon = _cell_str(row, idx_lon, home_team["lon"])

                # Build rich PRIC_CH (AD) label containing both team names + score/margin/winner
                hs_str = _cell_str(row, 16, "")
                as_str = _cell_str(row, 17, "")
                h_nm = home_team["name"]
                a_nm = away_team["name"]
                if hs_str.isdigit() and as_str.isdigit() and int(hs_str) > 0 and int(as_str) > 0:
                    hp, ap = int(hs_str), int(as_str)
                    win_nm = h_nm if hp > ap else a_nm
                    home_pric_ch = f"{h_nm} {hp}-{ap} {a_nm} ({hp-ap:+d} | WIN: {win_nm})"
                    away_pric_ch = f"{a_nm} {ap}-{hp} {h_nm} ({ap-hp:+d} | WIN: {win_nm})"
                else:
                    home_pric_ch = f"{h_nm} [HOME] vs {a_nm} [AWAY]"
                    away_pric_ch = f"{a_nm} [AWAY] @ {h_nm} [HOME]"

                # 1. Home Team row (DEG2 = Home Team, DEG3 = Home Arena)
                row_entries.append((
                    home_team["no"],
                    f"{home_team['name']} [HOME @ {home_team['arena']}]",
                    h_deg2,
                    arena_deg3,
                    r_zone,
                    r_lat,
                    r_lon,
                    home_pric_ch,
                ))
                # 2. Away Team row (DEG2 = Away Team, DEG3 = Home Arena!)
                row_entries.append((
                    away_team["no"],
                    f"{away_team['name']} [AWAY @ {home_team['code']}]",
                    a_deg2,
                    arena_deg3,
                    r_zone,
                    r_lat,
                    r_lon,
                    away_pric_ch,
                ))
            elif home_team and away_key in ("ALL", "", "*"):
                # Host Arena mode: Home Team + all 29 other teams evaluated inside Home Team's Stadium
                arena_deg3 = _cell_int(row, idx_deg3, home_team["deg3"])
                r_zone = _cell_str(row, idx_zone, home_team["tz"])
                if r_zone.upper() in ("AUTO", "TEAM", "NBA-GEM", ""):
                    r_zone = home_team["tz"]
                r_lat = _cell_str(row, idx_lat, home_team["lat"])
                r_lon = _cell_str(row, idx_lon, home_team["lon"])

                for t in teams:
                    role = f"HOME @ {home_team['arena']}" if t["no"] == home_team["no"] else f"AWAY @ {home_team['code']}"
                    row_entries.append((
                        t["no"],
                        f"{t['name']} [{role}]",
                        t["deg2"],
                        arena_deg3,
                        r_zone,
                        r_lat,
                        r_lon,
                        pric_ch,
                    ))
            else:
                # All 30 Teams in their own respective Home Arenas
                r_zone_override = _cell_str(row, idx_zone, "AUTO")
                use_own = r_zone_override.upper() in ("AUTO", "TEAM", "NBA-GEM", "")
                for t in teams:
                    row_entries.append((
                        t["no"],
                        f"{t['name']} [HOME]",
                        t["deg2"],
                        t["deg3"],
                        t["tz"] if use_own else r_zone_override,
                        t["lat"] if use_own else _cell_str(row, idx_lat, t["lat"]),
                        t["lon"] if use_own else _cell_str(row, idx_lon, t["lon"]),
                        pric_ch,
                    ))

            for t_no, t_label, d2, d3, z_use, lat_use, lon_use, row_pch in row_entries:
                date_str, wd_str, p1, p2, p3 = calc_from_date(dt, weekday, deg1_val, d2, d3)
                astro_rows.append([
                    date_str, p1, p2, p3, "",
                    time_v, z_use, lat_use, lon_use,
                    t_no, t_label,
                ])
                el1, el2 = calc_el1_el2((p1, p2, p3))
                header_rows.append([date_str, row_pch, wd_str, el1, el2, t_no, t_label])
                if len(row_entries) == 1:
                    sheet1_el_updates.append([d2, arena_deg3, p1, p2, p3, el1, el2])

            dates_done += 1
            last_valid_date = dt
            last_valid_idx = i

        except Exception as e:
            errors += 1
            if errors <= 5:
                log(f"  Error row {i+1} ({date_value!r}): {e}")
            continue

    log(
        f"  Calculated {len(astro_rows)} dynamic rows across {dates_done} input rows "
        f"({errors} errors, {repaired} dates repaired)"
    )

    if sheet1_el_updates and "EL1" in header_row and len(sheet1_el_updates) <= 6000:
        try:
            input_ws.update(range_name=f"H2:N{len(sheet1_el_updates)+1}", values=sheet1_el_updates)
            log(f"  Updated H2:N{len(sheet1_el_updates)+1} (DEG2, ARENA_DEG3, F, F2, F3, EL1, EL2) in Sheet1 (mode={_get_deg2_mode()})")
        except Exception as _e:
            log(f"  Note: could not update J:N in Sheet1: {_e}")

    log("[3/5] Writing NBA-Astro_Input...")
    output_ws = open_sheet(OUTPUT_SHEET_ID).sheet1
    _write_sheet(
        output_ws,
        ["DATE", "F", "F2", "F3", "E", "Time", "Zone", "Lat", "Lon", "TEAM_NO", "TEAM"],
        astro_rows, "K", "NBA-Astro_Input",
    )

    log("[4/5] Writing NBA-Astro_Header_Input...")
    header_ws = open_sheet(HEADER_SHEET_ID).sheet1
    _write_sheet(
        header_ws,
        ["DATE", "PRIC", "WEEKDAY", "EL1", "EL2", "TEAM_NO", "TEAM"],
        header_rows, "G", "NBA-Astro_Header_Input",
    )

    msg = (
        f"Wrote {len(astro_rows)} dynamic Home/Away rows ({dates_done} game rows) "
        "to NBA-Astro_Input and NBA-Astro_Header_Input"
    )
    if errors:
        msg += f" ({errors} input rows skipped due to errors)"
    log("[5/5] " + msg)
    emit_result(
        ok=True,
        rows_written=len(astro_rows),
        message=msg,
        extra={"errors": errors, "repaired": repaired, "dates": dates_done, "rows": len(astro_rows)},
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log("ERROR: " + str(e))
        log(traceback.format_exc())
        emit_result(ok=False, error=str(e), message="Step 1 failed")
        sys.exit(1)
