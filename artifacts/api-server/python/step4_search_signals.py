"""Step 4 - Search Signals (progressive-narrowing match, dynamic multi-market).

MARKETS ARE DISCOVERED AT RUNTIME from the VISIBLE KEY-MATCH-* tabs in
DATA-SEARCH-KEY. Hiding a tab in Google Sheets disables that market; unhiding
re-enables it — no code change needed to add/remove markets. The market code is
the tab name minus the 'KEY-MATCH-' prefix (KEY-MATCH-DJIA -> DJIA). Hidden tabs
are skipped. If 0 visible KEY-MATCH-* tabs exist, Step 4 aborts with a message.

CURRENT SCHEMA (9 cols A-I in SEARCH-SIGNALS and every KEY-MATCH-* tab):
  A = Weekday
  B = DATE
  C = DAILY PRICE
  D = QULITY-FIN-1   (e.g. '1 COLD')
  E = QULITY-FIN-2   (e.g. '3 DRY')
  F = ELE-P-1  (FIRE,  signed int)
  G = ELE-P-2  (AIR,   signed int)
  H = ELE-P-3  (WATER, signed int)
  I = ELE-P-4  (EARTH, signed int)

(Prior QULITY-DAY-1 / QULITY-DAY-2 columns have been REMOVED.)

SEARCH LOGIC (per forward day, PROGRESSIVE NARROWING — Option B "try-next"),
applied INDEPENDENTLY PER MARKET, all comparisons case-insensitive + trimmed:

  BASE (mandatory floor) — match on ALL THREE:
    1) DAY         (col A)   <-- weekday is now a MATCH KEY again
    2) QULITY-FIN-1 (col D)
    3) QULITY-FIN-2 (col E)
  If the base yields < 3 matches, RETURN whatever it has (0, 1, or 2 rows) —
  there is no NO-MATCH floor and no narrowing.

  If the base yields >= 3 matches, progressively narrow but NEVER below 3.
  Each stage adds its element column(s) on top of the LAST ACCEPTED set:
    Stage 2: + ELE-P-1 (col F) & ELE-P-2 (col G)
    Stage 3: + ELE-P-3 (col H)
    Stage 4: + ELE-P-4 (col I)
  After each stage, KEEP the narrowed set only if it still has >= 3 rows;
  otherwise SKIP that stage's criteria (Option B) and still attempt the
  remaining stages on the last accepted set. Once the accepted set is at the
  floor of 3, narrowing stops.

  If 0 historical rows match the base -> single 'NO MATCH' row for that day.

Day separator tag:
  [MATCH]    - at least one historical row matched (base, possibly narrowed)
  [NO MATCH] - zero base matches across all markets

Historical-only cutoff: search-DB rows must have date strictly before earliest
forward search date (avoids self-match against future-dated rows).

MATCH-DEPTH SCORING (NEW — runs ALONGSIDE the count-based Overall, which is kept
unchanged for comparison):
  For each matched historical row of a forward day:
    match_weight = 1 (the base DAY+QF1+QF2 is always matched) + the number of
                   ELE-P cols (F/G/H/I) whose normalized value also equals the
                   forward day's element. Range 1..5, each element worth +1.
    direction    = +1 if PRICE > 0, -1 if PRICE < 0, 0 if exactly flat.
    day_score    = match_weight * direction.
  Aggregated per forward day:
    total_score  = Σ day_score
    sum_abs      = Σ |day_score|
    ratio        = total_score / sum_abs   (0 if sum_abs == 0)
  Overall direction via a NEUTRAL dead-band (SCORE_NEUTRAL_BAND, default 0.15):
    ratio >= +band -> UP, ratio <= -band -> DOWN, else NEUTRAL.
  SCORE-CONF = |total_score| / sum_abs as a percentage.
  Pure match-depth only — no recency or magnitude weighting.

Writes:
  - FINAL_SIGNAL (Sheet1!A2:P open-ended): 16-col output.
    Cols: MARKET | DAY/LABEL | DATE | PRICE | QULITY-FIN-1 | QULITY-FIN-2 |
          ELE-P-1 | ELE-P-2 | ELE-P-3 | ELE-P-4 | FWD-DATE-SCORED |
          PER-MARKET-COUNT | SCORE | SCORE-OVERALL | SCORE-CONF | GEO-FIG
    GEO-FIG (col P) is per-row: matched rows carry their OWN figure, the
    SEARCH-KEY row carries "KEY: <fwd_figure>", and the summary banner row
    carries "<fwd_figure> | FIG: nB/mb" (forward figure + bull/bear tally).
    Permanent header row 1, yellow SEARCH-KEY row + colored per-day separator.
    Match-row col B carries the (display-only) weekday; col L carries the
    per-market matched-row count (on the first row per market). Cols M:O carry
    the match-depth SCORE / SCORE-OVERALL / SCORE-CONF on the per-day summary
    (separator) row. Per-market grouping retained.
  - PREDICTION-FINAL (Sheet1!A1...): dynamic width = 3 fixed + 5*N + 9 summary
    (N = active markets), col C = QUALITY_SIG
    ('QF1 || QF2 || F=N A=N W=N E=N'). Summary block ends with the match-depth
    SCORE / SCORE_OVERALL / SCORE_CONF cols. OVERALL_SIGNAL / SCORE_OVERALL
    suffix:
      ""        — match day
      " (NM)"   — no-match day
"""
from __future__ import annotations

import json
import os
import re
import sys
import traceback
from datetime import datetime

import google.auth.transport.requests
import requests
from google.oauth2.service_account import Credentials

from _lib.runner import emit_result, log

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _mint_token() -> str:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var is not set.")
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


# Markets are discovered dynamically at runtime from the VISIBLE KEY-MATCH-* tabs
# in DATA-SEARCH-KEY (see discover_active_markets). Hiding a tab in Google Sheets
# disables that market; unhiding re-enables it. No code change needed to add/remove.
KEY_TAB_PREFIX = "KEY-MATCH-"

# FINAL-SIGNAL is an 18-col output (A:R): MARKET, DAY/LABEL, DATE, PRICE, QF1, QF2,
# ELE-P-1, ELE-P-2, ELE-P-3, ELE-P-4, FWD-DATE-SCORED, PER-MARKET-COUNT, then the
# match-depth scoring columns SCORE, SCORE-OVERALL, SCORE-CONF, GEO-FIG (the forward
# day's own geomantic figure name), GEO-FIG-NUM (col Q, the 0-15 binary index of the
# SAME parity tuple as GEO-FIG: fire*8+air*4+water*2+earth*1), and ELEM-TRIGGER
# (col R, the per-block element trigger) — all on the per-day summary row.
FINAL_COLS = 18

# Match-depth scoring (alongside the legacy count-based Overall). Per matched
# historical day: match_weight = 1 (base DAY+QF1+QF2 always matched) + the number
# of ELE-P cols (F/G/H/I) that also equal the forward day (range 1-5); direction =
# +1 if PRICE>0, -1 if PRICE<0, 0 if flat; day_score = match_weight * direction.
# Aggregated per forward day: total_score = Σ day_score, sum_abs = Σ |day_score|,
# ratio = total_score / sum_abs (0 if sum_abs == 0). SCORE_NEUTRAL_BAND is the
# dead-zone around 0: ratio >= +band -> UP, <= -band -> DOWN, else NEUTRAL.
# SCORE-CONF = |total_score| / sum_abs as a percentage. Pure match-depth only
# (no recency or magnitude weighting). Tune the band here.
SCORE_NEUTRAL_BAND = 0.15

# --- Geomantic / Mazzaj trigger thresholds ---
# NOTE: defined for analysis/experimentation only — NOT wired into any scoring
# logic yet. Used by verify_logic.py's geomantic trigger tally.
# Bearish: melancholic dominance (cold+dry earth heavy)
GEO_BEAR_EARTH_MIN = 3        # ELE-P-4 (EARTH) intensity >= this
GEO_BEAR_PASSIVE   = "DRY"    # QULITY-FIN-2 must be DRY

# Bullish: sanguine dominance (hot+moist, fire+air heavy)
GEO_BULL_FIRE_MIN  = 1        # ELE-P-1 (FIRE) intensity >= this
GEO_BULL_AIR_MIN   = 2        # ELE-P-2 (AIR) intensity >= this
GEO_BULL_EARTH_MAX = 1        # ELE-P-4 (EARTH) intensity <= this

# Neutral: no decisive humoral lean
GEO_NEUTRAL_COLD   = 0        # QULITY-FIN-1 number == 0 (i.e. NEUTRAL)

# --- Geomantic Signal Map ---
# (figure_name, quadrant) -> directional bias multiplier
# Derived from 14,220-row DJIA history tally (verify_logic.py)
# Bullish combos (UP% > 55%, n >= 100) get positive boost
# Bearish combos (DOWN% > 55%, n >= 100) get negative boost
# All others get 1.0 (neutral)
GEO_SIGNAL_MAP = {
    ("Albus", "SANGUINE"): 1.20,         # 60.3% UP, n=237 (strongest)
    ("Acquisitio", "PHLEGMATIC"): 1.15,  # 58.1% UP, n=186
    ("Acquisitio", "MELANCHOLIC"): 1.10, # 56.7% UP, n=201
    ("Conjunctio", "PHLEGMATIC"): 0.85,  # 56.4% DOWN, n=163 (bearish)
}
GEO_DEFAULT_MULTIPLIER = 1.0

# --- Geomantic Figure System ---
# Each figure is a 4-bit pattern from parity (odd=1, even=0) of
# ELE-P-1(FIRE), ELE-P-2(AIR), ELE-P-3(WATER), ELE-P-4(EARTH)
GEOMANCY_FIGURES = {
    (0, 0, 0, 0): "Populus",
    (0, 0, 0, 1): "Tristitia",
    (0, 0, 1, 0): "Rubeus",
    (0, 0, 1, 1): "Fortuna_Major",
    (0, 1, 0, 0): "Albus",
    (0, 1, 0, 1): "Acquisitio",
    (0, 1, 1, 0): "Conjunctio",  # Coniunctio (classical spelling); kept "Conjunctio" to match GEO_SIGNAL_MAP / BEARISH_FIGURES
    (0, 1, 1, 1): "Caput_Draconis",
    (1, 0, 0, 0): "Laetitia",
    (1, 0, 0, 1): "Carcer",
    (1, 0, 1, 0): "Amissio",
    (1, 0, 1, 1): "Puer",
    (1, 1, 0, 0): "Fortuna_Minor",
    (1, 1, 0, 1): "Puella",
    (1, 1, 1, 0): "Cauda_Draconis",
    (1, 1, 1, 1): "Via",
}


# --- Bullish / bearish figure families (display-only tally on the summary row) ---
# Validated gain/joy/fortune vs loss/sorrow/restriction families. Used ONLY for the
# "FIG: nB/mb" tally shown in FINAL-SIGNAL col P; never affects matching or scoring.
BULLISH_FIGURES = {"Albus", "Acquisitio", "Laetitia", "Fortuna_Major"}
BEARISH_FIGURES = {"Conjunctio", "Amissio", "Tristitia", "Cauda_Draconis", "Carcer"}


def figure_from_elements(fire_int, air_int, water_int, earth_int):
    """Convert 4 element intensities to a geomantic figure name via odd/even parity."""
    pattern = (fire_int % 2, air_int % 2, water_int % 2, earth_int % 2)
    return GEOMANCY_FIGURES.get(pattern, "UNKNOWN")


def figure_num_from_elements(fire_int, air_int, water_int, earth_int):
    """Binary index (0-15) of the geomantic figure from the SAME parity tuple as
    figure_from_elements: FIRE is the most-significant bit (odd=1, even=0),
    value = fire*8 + air*4 + water*2 + earth*1. Always consistent with GEO-FIG."""
    return (
        (fire_int % 2) * 8 + (air_int % 2) * 4
        + (water_int % 2) * 2 + (earth_int % 2) * 1
    )


def _row_figure(row9):
    """Geomantic figure of a 9-col A:I row from its OWN element cols F:I (5..8)."""
    return figure_from_elements(
        _int_token(row9[5]), _int_token(row9[6]),
        _int_token(row9[7]), _int_token(row9[8]),
    )


def _row_figure_num(row9):
    """Binary index (0-15) of a 9-col A:I row from its OWN element cols F:I (5..8)."""
    return figure_num_from_elements(
        _int_token(row9[5]), _int_token(row9[6]),
        _int_token(row9[7]), _int_token(row9[8]),
    )


def mazzaj_quadrant(cold_num, passive_quality):
    """Classify into Mazzaj quadrant from QULITY-FIN-1 number and QULITY-FIN-2 text.
    High cold (>=4) vs Low cold (<4), crossed with DRY vs MOIST/NEUTRAL."""
    cold_high = cold_num >= 4
    is_dry = passive_quality.strip().upper() == "DRY"
    if cold_high and is_dry:
        return "MELANCHOLIC"   # cold+dry
    elif cold_high and not is_dry:
        return "PHLEGMATIC"    # cold+moist
    elif not cold_high and is_dry:
        return "CHOLERIC"      # warm+dry
    else:
        return "SANGUINE"      # warm+moist


def _int_token(cell):
    """Leading integer of a cell like '1 FIRE' or '3 COLD' -> 1 / 3. 0 if blank/bad."""
    parts = str(cell).strip().split()
    if not parts:
        return 0
    try:
        return int(parts[0])
    except ValueError:
        return 0


def _text_token(cell):
    """Text label of a quality cell like '6 DRY' -> 'DRY' (upper). '' if absent."""
    parts = str(cell).strip().split()
    return parts[1].upper() if len(parts) >= 2 else ""


def _row_figure_quadrant(row9):
    """(figure, quadrant) for a 9-col A:I row using its element + quality cols.
    cols: D(3)=QF1, E(4)=QF2, F-I(5..8)=ELE-P-1..4 (FIRE/AIR/WATER/EARTH)."""
    figure = figure_from_elements(
        _int_token(row9[5]), _int_token(row9[6]),
        _int_token(row9[7]), _int_token(row9[8]),
    )
    quadrant = mazzaj_quadrant(_int_token(row9[3]), _text_token(row9[4]))
    return figure, quadrant


def _price_to_float(s):
    # Parse a PRICE cell to float for match-depth direction. Returns None if the
    # value is blank/unparseable (treated as flat -> direction 0).
    txt = str(s).strip().replace(",", "")
    if not txt:
        return None
    try:
        return float(txt)
    except ValueError:
        return None


# ---- ELEMENT TRIGGER detector (per match block) -----------------------------
# For a match block (the matched history rows under a >>> [MATCH] <<< header),
# find which ONE element cleanly separates UP from DOWN. Source 9-col A:I row:
# price=idx2, ELE-P-1..4 (FIRE/AIR/WATER/EARTH)=idx5..8. In FINAL-SIGNAL output
# those elements land in cols G:J (idx6..9), used for the green highlight.
TRIGGER_ELEMENTS = [
    # (name, source_idx_in_9col_row, final_signal_out_col_index)
    ("FIRE", 5, 6),
    ("AIR", 6, 7),
    ("WATER", 7, 8),
    ("EARTH", 8, 9),
]
# Tiebreak priority when several elements qualify with equal coverage.
TRIGGER_PRIORITY = {"EARTH": 4, "WATER": 3, "AIR": 2, "FIRE": 1}
# Light-green background for the winning element's trigger cells.
GREEN_HL = {"red": 0.7137, "green": 0.8784, "blue": 0.7137}


def _trigger_direction(price_cell):
    """Price sign -> 'UP' (>0) / 'DOWN' (<0) / None (FLAT==0 or unparseable)."""
    f = _price_to_float(price_cell)
    if f is None or f == 0:
        return None
    return "UP" if f > 0 else "DOWN"


def detect_element_trigger(matched_rows):
    """Find the ONE element that cleanly separates UP from DOWN across a block.

    A value is PURE if >=2 matched rows hold that element value (FLAT/0-price rows
    ignored) and they ALL share the same price direction. An element qualifies if
    it has >=1 pure value. Winner = element whose pure values cover the MOST rows;
    tie -> fixed priority EARTH > WATER > AIR > FIRE.

    Returns (element_name | None, pure_values) where pure_values is a list of
    (value:int, direction:str, count:int), ordered by count desc then value desc.
    """
    candidates = []
    for name, idx, _out in TRIGGER_ELEMENTS:
        by_val: dict[int, list[str]] = {}
        for r in matched_rows:
            r9 = list(r) + [""] * (9 - len(r))  # local pad (run().pad is nested)
            d = _trigger_direction(r9[2])
            if d is None:
                continue  # FLAT row ignored when forming pure groups
            by_val.setdefault(_int_token(r9[idx]), []).append(d)
        pure = []
        for val, dirs in by_val.items():
            if len(dirs) >= 2 and len(set(dirs)) == 1:
                pure.append((val, dirs[0], len(dirs)))
        if pure:
            pure.sort(key=lambda p: (p[2], p[0]), reverse=True)
            coverage = sum(c for _v, _d, c in pure)
            candidates.append((coverage, TRIGGER_PRIORITY[name], name, pure))
    if not candidates:
        return (None, [])
    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
    _cov, _pri, name, pure = candidates[0]
    return (name, pure)


def format_trigger_compact(market, name, pure):
    """Per-market compact trigger for FINAL-SIGNAL col R (ELEM-TRIGGER).
    e.g. 'BTC EARTH:2->DOWN(2/2),1->UP(2/2)' or 'BTC none'."""
    if not name:
        return f"{market} none"
    parts = ",".join(f"{v}->{d}({c}/{c})" for v, d, c in pure)
    return f"{market} {name}:{parts}"


def build_block_trigger_text(matched_by_market, markets):
    """Compose FINAL-SIGNAL col R: run detect_element_trigger SEPARATELY per market
    (markets' elements/directions differ), keep markets that have matched rows in
    `markets` order, and join compactly with ' | '. Empty string if no market has
    rows. Used by step4 (write) and verify_logic (recompute) so both stay in sync."""
    parts = []
    for m in markets:
        rows = matched_by_market.get(m) or []
        if not rows:
            continue
        name, pure = detect_element_trigger(rows)
        parts.append(format_trigger_compact(m, name, pure))
    return " | ".join(parts)


def element_trigger_vote(matched_rows, fwd_value_by_element):
    """ONE market's element-trigger-driven vote for the block's Overall direction.

    Rule (per market):
      1. Deciding element = the ELEM-TRIGGER WINNER (detect_element_trigger) for this
         market's matched rows — the element whose pure values cover the most rows.
      2. Read the forward/search-key day's value for that winning element.
      3. Consider ONLY the matched rows that share that exact value for that element
         (FLAT/0-price rows have no direction and are ignored, as in the trigger).
      4. UP if all considered rows are UP; DOWN if all DOWN; NEUTRAL if NO matched row
         shares the forward value, or the considered rows are split (mixed UP/DOWN).

    Returns (vote, agree, considered) where vote in {UP, DOWN, NEUTRAL},
    considered = number of (non-FLAT) matched rows sharing the forward value, and
    agree = rows agreeing with vote (== considered when directional, else 0).
    """
    name, _pure = detect_element_trigger(matched_rows)
    if not name:
        return ("NEUTRAL", 0, 0)
    sidx = None
    for _nm, _sidx, _ocol in TRIGGER_ELEMENTS:
        if _nm == name:
            sidx = _sidx
            break
    fwd_val = fwd_value_by_element.get(name)
    if sidx is None or fwd_val is None:
        return ("NEUTRAL", 0, 0)
    dirs = []
    for r in matched_rows:
        r9 = list(r) + [""] * (9 - len(r))
        if _int_token(r9[sidx]) != fwd_val:
            continue  # different value for the deciding element -> ignored
        d = _trigger_direction(r9[2])
        if d is None:
            continue  # FLAT/unparseable price -> no direction, ignored
        dirs.append(d)
    considered = len(dirs)
    if considered == 0:
        return ("NEUTRAL", 0, 0)
    if all(x == "UP" for x in dirs):
        return ("UP", considered, considered)
    if all(x == "DOWN" for x in dirs):
        return ("DOWN", considered, considered)
    return ("NEUTRAL", 0, considered)  # split -> NEUTRAL


def element_trigger_overall(matched_by_market, markets, fwd_value_by_element):
    """Block-level Overall driven by the per-market element-trigger votes.

    Each active market casts element_trigger_vote(); combine by MAJORITY of clean
    directional votes. up-votes > down-votes -> UP; down > up -> DOWN; tie or no
    votes -> NEUTRAL. Confidence = of the markets that cast a directional vote, the
    fraction of their considered rows on the winning side (single market 2/2 -> 100%).
    Agreement = number of markets whose vote == the block Overall (0 when NEUTRAL).

    Returns (overall, overall_conf, votes, agreement) where votes maps
    market -> (vote, agree, considered). Single source of truth shared by step4
    (write path) and verify_logic (independent recompute) so they cannot drift.
    """
    votes = {}
    for m in markets:
        rows = matched_by_market.get(m) or []
        if not rows:
            continue
        votes[m] = element_trigger_vote(rows, fwd_value_by_element)
    up_markets = [m for m, (v, _a, _c) in votes.items() if v == "UP"]
    dn_markets = [m for m, (v, _a, _c) in votes.items() if v == "DOWN"]
    if len(up_markets) > len(dn_markets):
        overall = "UP"
    elif len(dn_markets) > len(up_markets):
        overall = "DOWN"
    else:
        overall = "NEUTRAL"
    if overall == "NEUTRAL":
        overall_conf = 0.0
        agreement = 0
    else:
        win_markets = up_markets if overall == "UP" else dn_markets
        voting = up_markets + dn_markets
        considered_total = sum(votes[m][2] for m in voting)
        agreeing_rows = sum(votes[m][2] for m in win_markets)
        overall_conf = (agreeing_rows / considered_total * 100) if considered_total else 0.0
        agreement = len(win_markets)
    return overall, overall_conf, votes, agreement


def count_block_overall(matched_by_market, markets):
    """Count-based block Overall (the ORIGINAL majority logic, restored as DIRECTION).

    Per market: dn = matched rows with a NEGATIVE price (cell starts with '-'),
    up = all other matched rows (flat/zero price counts as up, as before). Per-market
    signal = up>dn -> UP, dn>up -> DOWN, tie -> NEUTRAL. Block direction = UP if
    total_up>total_dn, DOWN if total_dn>total_up, NEUTRAL ONLY on a TRUE count tie.
    Confidence = max(total_up,total_dn)/total_matches*100.

    Returns (overall, overall_conf, per_market_signal, total_up, total_dn, total_matches).
    Shared by step4 (write) and verify_logic (recompute) so the two cannot drift. Rows
    carry price at index 2 (step4 9-col DB rows and verify detector rows both match).
    """
    per_market_signal = {}
    total_up = total_dn = total_matches = 0
    for m in markets:
        rows = matched_by_market.get(m) or []
        dn = sum(1 for r in rows if str(r[2]).strip().startswith("-"))
        up = len(rows) - dn
        per_market_signal[m] = "UP" if up > dn else "DOWN" if dn > up else "NEUTRAL"
        total_up += up
        total_dn += dn
        total_matches += len(rows)
    if total_up > total_dn:
        overall = "UP"
    elif total_dn > total_up:
        overall = "DOWN"
    else:
        overall = "NEUTRAL"
    overall_conf = (max(total_up, total_dn) / total_matches * 100) if total_matches else 0.0
    return overall, overall_conf, per_market_signal, total_up, total_dn, total_matches


def agreement_label(count_dir, elem_dir):
    """3-state AGREEMENT label comparing the element-trigger verdict (elem_dir, from
    element_trigger_overall) to the count-based DIRECTION (count_dir). It NEVER overrides
    the direction — it only annotates whether the element trigger backs it:
      SILENT    = element trigger gave no direction (no matching forward value / no pure
                  signal / market tie) -> elem_dir == NEUTRAL.
      CONFIRMED = element trigger gave a direction that AGREES with the count direction.
      CONFLICT  = element trigger gave a direction that DIFFERS from the count direction
                  (opposite, or count was a NEUTRAL tie).
    Shared by step4 (write) and verify_logic (recompute).
    """
    if elem_dir == "NEUTRAL":
        return "SILENT"
    if elem_dir == count_dir:
        return "CONFIRMED"
    return "CONFLICT"


def _parse_date(s: str):
    s = str(s).strip()
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_disabled_markets(argv) -> "set[str]":
    # Parse the optional `--disabled-markets BTC,DJIA,...` flag passed by the API
    # server: the market codes the user UNCHECKED on the dashboard. Returns a set
    # of normalized (upper/trimmed) codes to EXCLUDE. Absent or empty => empty set
    # (exclude nothing → run every visible market, preserving dynamic discovery).
    for i, a in enumerate(argv):
        val = None
        if a == "--disabled-markets" and i + 1 < len(argv):
            val = argv[i + 1]
        elif a.startswith("--disabled-markets="):
            val = a.split("=", 1)[1]
        if val is not None:
            return {m.strip().upper() for m in val.split(",") if m.strip()}
    return set()


def run() -> dict:
    if os.environ.get("TENNIS_SHEETS_WRITE_ENABLED", "0") != "1":
        raise RuntimeError("TENNIS SHEET ISOLATION: Google Sheets sync/write is disabled (NBA/NHL sheets isolated).")
    token = _mint_token()
    disabled_markets = _parse_disabled_markets(sys.argv[1:])

    SEARCH_SIGNALS_ID = os.environ.get("TENNIS_SEARCH_SIGNALS_SHEET_ID", "")
    DATA_SEARCH_KEY_ID = os.environ.get("TENNIS_SEARCH_KEY_SHEET_ID", "")
    FINAL_SIGNAL_ID = os.environ.get("TENNIS_FINAL_SIGNAL_SHEET_ID", "")
    PREDICTION_FINAL_ID = os.environ.get("TENNIS_PREDICTION_FINAL_SHEET_ID", "")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def read_sheet(sid, r):
        u = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{r}"
        x = requests.get(u, headers=headers, timeout=60)
        x.raise_for_status()
        return x.json().get("values", [])

    def clear_sheet(sid, r):
        u = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{r}:clear"
        x = requests.post(u, headers=headers, timeout=60)
        x.raise_for_status()

    def write_sheet(sid, r, v, raw=False):
        opt = "RAW" if raw else "USER_ENTERED"
        u = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{r}"
            f"?valueInputOption={opt}"
        )
        x = requests.put(u, headers=headers, json={"values": v}, timeout=120)
        x.raise_for_status()
        return x.json()

    def format_sheet(sid, b):
        u = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}:batchUpdate"
        x = requests.post(u, headers=headers, json=b, timeout=60)
        if x.status_code >= 400:
            raise RuntimeError(f"batchUpdate {x.status_code}: {x.text[:800]}")
        return x.json()

    def get_sheet_gid(sid, tab_name=None):
        u = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=sheets.properties"
        x = requests.get(u, headers=headers, timeout=30)
        x.raise_for_status()
        sheets = x.json()["sheets"]
        if tab_name:
            for s in sheets:
                if s["properties"]["title"] == tab_name:
                    return s["properties"]["sheetId"]
            raise RuntimeError(f"tab {tab_name!r} not found in {sid}")
        return sheets[0]["properties"]["sheetId"]

    def parse_quality(c):
        # "9 COLD" -> (9, "COLD"); "0 NEUTRAL" -> (0, "NEUTRAL"); "28 HOT" -> (28, "HOT").
        # Label matters: HOT vs COLD, MOIST vs DRY differ in axis sign.
        m = re.match(r"(-?\d+)\s+([A-Za-z]+)", str(c).strip())
        return (int(m.group(1)), m.group(2).upper()) if m else None

    def norm(s):
        # Case-insensitive, trimmed string normalization for exact-equality match.
        return str(s).strip().upper() if s is not None else ""

    def base_key3(day, qf1, qf2):
        # MANDATORY base (floor) key for the progressive-narrowing matcher:
        #   DAY (A) + QULITY-FIN-1 (D) + QULITY-FIN-2 (E),
        # case-insensitive + trimmed. A blank in ANY of the three -> None
        # (row unmatchable on the base; a blank is never a real value).
        parts = (norm(day), norm(qf1), norm(qf2))
        if any(p == "" for p in parts):
            return None
        return parts

    def pad(row, n):
        return list(row) + [""] * (n - len(row))

    def col_a1(n):
        # 1-based column count -> A1 column letter (supports >26: 27 -> AA).
        s = ""
        while n > 0:
            n, rem = divmod(n - 1, 26)
            s = chr(65 + rem) + s
        return s

    def discover_active_markets(sid):
        # Dynamic switch: only VISIBLE tabs named KEY-MATCH-* are active markets.
        # Hiding a tab in Google Sheets disables that market; unhiding re-enables it.
        u = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
            "?fields=sheets.properties(title,hidden)"
        )
        x = requests.get(u, headers=headers, timeout=30)
        x.raise_for_status()
        active = {}          # market -> exact tab name
        hidden_skipped = []  # market codes for hidden KEY-MATCH-* tabs
        for s in x.json().get("sheets", []):
            props = s["properties"]
            title = props["title"]
            if not title.startswith(KEY_TAB_PREFIX):
                continue
            market = title[len(KEY_TAB_PREFIX):].strip()
            if not market:  # a tab literally named "KEY-MATCH-" has no market code
                continue
            if props.get("hidden", False):
                hidden_skipped.append(market)
            else:
                active[market] = title
        return active, sorted(hidden_skipped)

    # ---- Dynamic market discovery (visible KEY-MATCH-* tabs only) ----
    active_tabs, hidden_markets = discover_active_markets(DATA_SEARCH_KEY_ID)
    visible_markets = sorted(active_tabs.keys())
    log(
        f"Step 4 visible markets: {visible_markets}  "
        f"| Hidden/skipped: {hidden_markets}"
    )

    # ---- User enable/disable filter (dashboard checkboxes via --disabled-markets) ----
    # Effective markets = visible MINUS the user-unchecked set. Excluding (rather
    # than intersecting an allow-list) preserves dynamic discovery: any visible
    # KEY-MATCH-* tab the dashboard doesn't know about still runs unless it was
    # explicitly disabled.
    disabled_by_user = sorted(m for m in visible_markets if m in disabled_markets)
    MARKETS = sorted(m for m in visible_markets if m not in disabled_markets)
    if disabled_markets:
        log(
            f"Step 4 user filter (--disabled-markets): excluded={sorted(disabled_markets)}  "
            f"| disabled-by-user (visible & unchecked): {disabled_by_user}"
        )
    else:
        log("Step 4 user filter (--disabled-markets): none — running all visible markets")

    MARKET_TABS = {m: active_tabs[m] for m in MARKETS}
    n_markets = len(MARKETS)
    log(f"Step 4 active markets (visible − disabled): {MARKETS}")

    if not visible_markets:
        emit_result(
            ok=False,
            rows_written=0,
            error="No visible KEY-MATCH-* tabs",
            message="No visible KEY-MATCH-* tabs found. Unhide at least one to run Step 4.",
            extra={"status": "NO_VISIBLE_TABS", "hiddenMarkets": hidden_markets},
        )
        return {"status": "NO_VISIBLE_TABS"}
    if not MARKETS:
        emit_result(
            ok=False,
            rows_written=0,
            error="No markets enabled",
            message=(
                "No markets enabled for Step 4. Visible markets "
                f"{visible_markets} were all unchecked on the dashboard. "
                "Enable at least one market to run Step 4."
            ),
            extra={
                "status": "NO_ENABLED_MARKETS",
                "visibleMarkets": visible_markets,
                "hiddenMarkets": hidden_markets,
                "disabledByUser": disabled_by_user,
            },
        )
        return {"status": "NO_ENABLED_MARKETS"}

    log(f"[1/4] Reading SEARCH-SIGNALS and DATA-SEARCH-KEY ({n_markets} tab(s), 9-col schema A:I)...")
    search_data = read_sheet(SEARCH_SIGNALS_ID, "Sheet1!A2:I")
    if not search_data:
        emit_result(
            ok=True,
            rows_written=0,
            message="No rows in SEARCH-SIGNALS — nothing to score",
            extra={"status": "NO_INPUT", "daysProcessed": 0},
        )
        return {"status": "NO_INPUT"}

    forward_dates = [_parse_date(r[1]) for r in search_data if len(r) > 1]
    forward_dates = [d for d in forward_dates if d is not None]
    cutoff = min(forward_dates) if forward_dates else None
    if cutoff:
        log(f"  forward-date cutoff (search-DB rows must be < this): {cutoff.isoformat()}")
    else:
        log("  no parseable forward dates; not applying historical-only cutoff")

    # db_by_market[m] entries: (row, bk, ev)
    #   row = padded A:I (9 cols)
    #   bk  = base key (DAY, QF1, QF2) normalized — row dropped if any blank
    #   ev  = element vector (ELE-P-1..4 / F,G,H,I) normalized, used for narrowing
    db_by_market: dict[str, list] = {m: [] for m in MARKETS}
    db_counts = {}
    db_dropped_future = 0
    db_dropped_unparseable = 0
    db_unparseable_elements = 0  # kept for result schema compatibility (now always 0)
    for market, tab in MARKET_TABS.items():
        rows = read_sheet(DATA_SEARCH_KEY_ID, f"{tab}!A2:I")
        kept = 0
        dropped_future = 0
        dropped_bad = 0
        for r in rows:
            r = pad(r, 9)
            # Need DATE (B) for cutoff and the base cols (A,D,E) to be matchable.
            row_date = _parse_date(r[1])
            if cutoff is not None and (row_date is None or row_date >= cutoff):
                if row_date is None:
                    dropped_bad += 1
                else:
                    dropped_future += 1
                continue
            bk = base_key3(r[0], r[3], r[4])  # A=DAY, D=QF1, E=QF2
            if bk is None:
                dropped_bad += 1
                continue
            ev = (norm(r[5]), norm(r[6]), norm(r[7]), norm(r[8]))  # F, G, H, I
            db_by_market[market].append((r, bk, ev))
            kept += 1
        db_counts[market] = kept
        db_dropped_future += dropped_future
        db_dropped_unparseable += dropped_bad
        log(
            f"  {tab}: read={len(rows)} kept={kept} "
            f"dropped_future={dropped_future} dropped_unparseable={dropped_bad}"
        )
    db_total = sum(db_counts.get(m, 0) for m in MARKETS)
    _kept_parts = ", ".join(f"{m}={db_counts.get(m, 0)}" for m in MARKETS)
    log(f"  total search rows kept: {db_total} ({_kept_parts})")

    if not db_total:
        emit_result(
            ok=True,
            rows_written=0,
            message="DATA-SEARCH-KEY had no usable historical rows",
            extra={"status": "NO_DB_DATA", "daysProcessed": 0},
        )
        return {"status": "NO_DB_DATA"}

    log("[2/4] Clearing FINAL_SIGNAL output range (A1:T open-ended) + writing header row...")
    clear_sheet(FINAL_SIGNAL_ID, "Sheet1!A1:T")  # over-clear to wipe any stale prior-schema cols
    # Permanent header row so the col mapping is unambiguous when reading the sheet.
    # Cols A:L = MARKET, DAY/label, DATE, PRICE, QF1, QF2, ELE-P-1..4, FWD-DATE, PER-MARKET-COUNT;
    # cols M:O = SCORE, SCORE-OVERALL, SCORE-CONF (match-depth, populated on the per-day summary row);
    # col P = GEO-FIG (per-row): each matched row carries ITS OWN figure (from its ELE-P-1..4);
    #   the SEARCH-KEY row carries "KEY: <fwd_figure>"; the per-day summary row carries
    #   "<fwd_figure> | FIG: nB/mb" (forward figure + bullish/bearish tally of its matched rows).
    write_sheet(
        FINAL_SIGNAL_ID,
        "Sheet1!A1:R1",
        [["MARKET", "DAY/LABEL", "DATE", "PRICE",
          "QULITY-FIN-1", "QULITY-FIN-2",
          "ELE-P-1", "ELE-P-2", "ELE-P-3", "ELE-P-4",
          "FWD-DATE-SCORED", "PER-MARKET-COUNT",
          "SCORE", "SCORE-OVERALL", "SCORE-CONF", "GEO-FIG",
          "GEO-FIG-NUM", "ELEM-TRIGGER"]],
        raw=True,
    )
    sheet_gid = get_sheet_gid(FINAL_SIGNAL_ID, "Sheet1")

    log(
        "[3/4] Scoring matches per forward day "
        "(progressive narrowing, Option B: base A+D+E, narrow >=3 with F+G, H, I)..."
    )
    all_output: list[list] = []
    all_results: list[dict] = []
    separator_rows: list[dict] = []
    key_rows: list[int] = []
    green_cells: list[tuple[int, int]] = []  # (output_row_idx, col_idx) for trigger highlight
    match_days = 0      # >=1 historical row matched (base DAY+QF1+QF2, then narrowed)
    no_match_days = 0
    skipped_input = 0
    KEY_YELLOW = {"red": 1.0, "green": 0.97, "blue": 0.70}
    colors = [
        {"red": 0.85, "green": 0.92, "blue": 1.0},
        {"red": 1.0, "green": 0.90, "blue": 0.80},
        {"red": 0.85, "green": 1.0, "blue": 0.85},
        {"red": 1.0, "green": 0.85, "blue": 0.85},
        {"red": 0.95, "green": 0.90, "blue": 1.0},
        {"red": 1.0, "green": 1.0, "blue": 0.80},
        {"red": 0.80, "green": 0.95, "blue": 0.95},
        {"red": 1.0, "green": 0.85, "blue": 0.95},
    ]

    for day_idx, row in enumerate(search_data):
        row = pad(row, 9)
        search_day = row[0]
        search_date = row[1]
        projected_price = row[2]
        qf1, qf2 = row[3], row[4]
        fwd_fire, fwd_air, fwd_water, fwd_earth = row[5], row[6], row[7], row[8]

        # Build the mandatory base key (floor) for this forward day:
        #   DAY (A) + QULITY-FIN-1 (D) + QULITY-FIN-2 (E).
        fwd_base = base_key3(search_day, qf1, qf2)
        if fwd_base is None:
            skipped_input += 1
            log(
                f"  skip {search_day} {search_date}: blank in a base col "
                f"(A={search_day!r}, D={qf1!r}, E={qf2!r})"
            )
            continue
        # Forward element vector (F,G,H,I) used for progressive narrowing.
        fwd_elem = (norm(fwd_fire), norm(fwd_air), norm(fwd_water), norm(fwd_earth))
        # The forward day's OWN geomantic figure (compact, no quadrant) -> GEO-FIG col.
        fwd_figure = figure_from_elements(
            _int_token(fwd_fire), _int_token(fwd_air),
            _int_token(fwd_water), _int_token(fwd_earth),
        )
        # The same parity tuple as a 0-15 binary index -> GEO-FIG-NUM col.
        fwd_fig_num = figure_num_from_elements(
            _int_token(fwd_fire), _int_token(fwd_air),
            _int_token(fwd_water), _int_token(fwd_earth),
        )

        # ---- PROGRESSIVE NARROWING (Option B = try-next) per market ----
        # Base = rows matching DAY+QF1+QF2. If base < 3, return base as-is
        # (0/1/2 rows allowed). If base >= 3, progressively narrow but never
        # below 3: each stage adds element col(s) on top of the LAST ACCEPTED
        # set; if a stage would drop below 3, SKIP it but still try the rest.
        #   Stage 2: + ELE-P-1 (F) & ELE-P-2 (G)
        #   Stage 3: + ELE-P-3 (H)
        #   Stage 4: + ELE-P-4 (I)
        NARROW_STAGES = ((0, 1), (2,), (3,))  # indices into the element vector
        matched = {}
        narrow_depth = {}  # per-market count of element stages actually applied
        for m in MARKETS:
            accepted = [(r, ev) for (r, bk, ev) in db_by_market[m] if bk == fwd_base]
            depth = 0
            if len(accepted) >= 3:
                for stage_cols in NARROW_STAGES:
                    if len(accepted) <= 3:
                        break  # at the floor; further narrowing can't improve
                    cand = [
                        (r, ev) for (r, ev) in accepted
                        if all(ev[c] == fwd_elem[c] for c in stage_cols)
                    ]
                    if len(cand) >= 3:
                        accepted = cand
                        depth += 1
                    # else: skip this stage's criteria, keep last accepted set
            matched[m] = [r for (r, ev) in accepted]
            narrow_depth[m] = depth

        is_match = sum(len(v) for v in matched.values()) > 0

        # up/dn computed from the matched output rows only, per market.
        per_market = {}
        for m in MARKETS:
            rows = matched[m]
            dn = sum(1 for r in rows if str(r[2]).startswith("-"))
            per_market[m] = {"rows": rows, "up": len(rows) - dn, "dn": dn}

        # ---- HYBRID OVERALL: count-based DIRECTION + CONFIDENCE, annotated with an
        # element-trigger AGREEMENT label (CONFIRMED/SILENT/CONFLICT) ----
        # DIRECTION + CONFIDENCE are the ORIGINAL count-of-up-vs-down logic (restored).
        # total_matches/up/dn remain informational (banner G/H/I/J + PF per-market cols).
        # Shared with verify_logic via count_block_overall (single source of truth).
        overall, overall_conf, per_market_signal, total_up, total_dn, total_matches = (
            count_block_overall(matched, MARKETS)
        )
        # The element-trigger verdict (direction only) does NOT override the direction —
        # it only sets the AGREEMENT label vs the count direction. Per market the
        # ELEM-TRIGGER winning element decides; read the forward day's value for that
        # element; consider only matched rows sharing that value; markets combine by
        # majority -> elem_dir in {UP, DOWN, NEUTRAL}. Shared via element_trigger_overall.
        fwd_value_by_element = {
            "FIRE": _int_token(fwd_fire), "AIR": _int_token(fwd_air),
            "WATER": _int_token(fwd_water), "EARTH": _int_token(fwd_earth),
        }
        elem_dir, _elem_conf, _elem_votes, _elem_agree = element_trigger_overall(
            matched, MARKETS, fwd_value_by_element
        )
        agree_label = agreement_label(overall, elem_dir)

        # ---- MATCH-DEPTH SCORING (independent of Overall; cols M:O, unchanged) ----
        # Per matched historical row: match_weight = 1 (base DAY+QF1+QF2 always
        # matched) + the number of ELE-P cols (F/G/H/I -> indices 5..8) that also
        # equal the forward day; direction from PRICE sign; day_score = weight*dir.
        # Each matched row's day_score is then scaled by the GEOMANTIC multiplier
        # GEO_SIGNAL_MAP[(figure, quadrant)] of THAT row (1.0 = neutral, so rows
        # with no notable combo behave exactly as before).
        total_score = 0.0
        sum_abs = 0.0
        for m in MARKETS:
            for m_row in matched[m]:
                match_weight = 1 + sum(
                    1 for k in range(4) if norm(m_row[5 + k]) == fwd_elem[k]
                )
                price = _price_to_float(m_row[2])
                if price is None or price == 0:
                    direction = 0
                elif price > 0:
                    direction = 1
                else:
                    direction = -1
                # Geomantic bias of this matched history row (its own figure+quadrant).
                geo_fig, geo_quad = _row_figure_quadrant(pad(m_row, 9))
                geo_mult = GEO_SIGNAL_MAP.get((geo_fig, geo_quad), GEO_DEFAULT_MULTIPLIER)
                day_score = match_weight * direction * geo_mult
                total_score += day_score
                sum_abs += abs(day_score)
        total_score = round(total_score, 4)
        sum_abs = round(sum_abs, 4)
        score_ratio = (total_score / sum_abs) if sum_abs > 0 else 0.0
        if score_ratio >= SCORE_NEUTRAL_BAND:
            score_overall = "UP"
        elif score_ratio <= -SCORE_NEUTRAL_BAND:
            score_overall = "DOWN"
        else:
            score_overall = "NEUTRAL"
        score_conf = (abs(total_score) / sum_abs * 100) if sum_abs > 0 else 0.0

        # ---- BULLISH / BEARISH FIGURE TALLY (display-only, summary row col P) ----
        # Count matched rows whose OWN figure is in the bullish vs bearish family.
        # Pure display; does not touch matching, counts, or scoring.
        bull_count = 0
        bear_count = 0
        for m in MARKETS:
            for m_row in matched[m]:
                rf = _row_figure(pad(m_row, 9))
                if rf in BULLISH_FIGURES:
                    bull_count += 1
                elif rf in BEARISH_FIGURES:
                    bear_count += 1

        quality_sig = (
            f"{qf1} || {qf2} || "
            f"F={fwd_fire} A={fwd_air} W={fwd_water} E={fwd_earth}"
        )
        # ---- ELEMENT TRIGGER (PER MARKET within the block) ----
        # Run detect_element_trigger SEPARATELY on each market's matched rows (their
        # elements/directions differ). per_market_trigger[m] = (name, pure, src_idx,
        # out_col, values_set) for the green highlight; col R lists each market's
        # trigger compactly, joined ' | ', in MARKETS order (markets with >=1 row).
        per_market_trigger: dict[str, tuple] = {}
        for m in MARKETS:
            if not matched[m]:
                continue
            nm, pure = detect_element_trigger(matched[m])
            sidx = ocol = None
            vals: set[int] = set()
            if nm:
                for _nm, _sidx, _ocol in TRIGGER_ELEMENTS:
                    if _nm == nm:
                        sidx, ocol = _sidx, _ocol
                        break
                vals = {v for v, _d, _c in pure}
            per_market_trigger[m] = (nm, pure, sidx, ocol, vals)
        # col R text via the shared builder (same fn verify_logic recomputes with) so
        # the write path and the verifier can never drift on format/market ordering.
        trigger_text = build_block_trigger_text(matched, MARKETS) if is_match else ""

        # Separator banner tag (col B): MATCH / NO MATCH.
        tag = "MATCH" if is_match else "NO MATCH"

        _mkt_log = " ".join(
            f"{m} {per_market[m]['up']}u/{per_market[m]['dn']}d(d{narrow_depth[m]})"
            for m in MARKETS
        )
        log(
            f"  {search_day} {search_date} [{tag}]: {_mkt_log} "
            f"-> Overall {overall} ({overall_conf:.0f}%, agree={agree_label} "
            f"[elem={elem_dir}], total={total_matches})"
        )

        # ---- FINAL-SIGNAL row writes (12 cols A:L) ----
        header_idx = len(all_output)
        all_output.append([
            "",  # A
            f">>> {search_day} {search_date} [{tag}] <<<",  # B
            quality_sig,  # C
            f"Overall: {overall}",  # D
            f"Conf: {overall_conf:.0f}%",  # E
            f"Agree: {agree_label}",  # F (3-state element-trigger label vs count direction)
            f"Total: {total_matches}",  # G
            f"UP: {total_up}",  # H
            f"DOWN: {total_dn}",  # I
            f"Matches: {total_matches}",  # J
            " | ".join(
                f"{m} {per_market[m]['up']}u/{per_market[m]['dn']}d" for m in MARKETS
            ),  # K
            "",  # L
            total_score,  # M (SCORE: match-depth total)
            score_overall,  # N (SCORE-OVERALL: UP/DOWN/NEUTRAL)
            f"{score_conf:.0f}%",  # O (SCORE-CONF)
            f"{fwd_figure} | FIG: {bull_count}B/{bear_count}b",  # P (fwd figure + bull/bear tally)
            fwd_fig_num,  # Q (GEO-FIG-NUM: 0-15 binary index of fwd figure)
            trigger_text,  # R (ELEM-TRIGGER: per-market triggers joined ' | ')
        ])
        separator_rows.append({"row": header_idx, "color": colors[day_idx % len(colors)]})

        # SEARCH-KEY row (yellow) — 17 cols A:Q (P = search day's own figure, labeled;
        # Q = GEO-FIG-NUM, the 0-15 binary index of that figure)
        key_idx = len(all_output)
        all_output.append([
            "",                # A
            "SEARCH-KEY",      # B
            search_date,       # C
            projected_price,   # D
            qf1,               # E
            qf2,               # F
            fwd_fire,          # G
            fwd_air,           # H
            fwd_water,         # I
            fwd_earth,         # J
            "",                # K
            "",                # L
            "", "", "",        # M, N, O
            f"KEY: {fwd_figure}",  # P (search day's own geomantic figure, labeled)
            fwd_fig_num,           # Q (GEO-FIG-NUM: 0-15 binary index of fwd figure)
        ])
        key_rows.append(key_idx)

        if not is_match:
            no_match_days += 1
            all_output.append([
                "—", "NO MATCH", search_date,
                "", "", "", "", "", "", "", "", "",
            ])
        else:
            match_days += 1
            for market in MARKETS:
                rows = per_market[market]["rows"]
                mcount = len(rows)
                # This market's own trigger (element + pure values) for the green
                # highlight. Empty tuple when the market has no matched rows.
                m_trig = per_market_trigger.get(market, (None, [], None, None, set()))
                m_trig_src, m_trig_col, m_trig_vals = m_trig[2], m_trig[3], m_trig[4]
                for i, m_row in enumerate(rows):
                    weekday = m_row[0]
                    cdate = m_row[1]
                    cprice = m_row[2]
                    cqf1, cqf2 = m_row[3], m_row[4]
                    cfire, cair, cwater, cearth = m_row[5], m_row[6], m_row[7], m_row[8]
                    # This row's OWN geomantic figure (from its ELE-P-1..4) -> col P,
                    # and the same parity tuple as a 0-15 binary index -> col Q.
                    row_fig = _row_figure(pad(m_row, 9))
                    row_fig_num = _row_figure_num(pad(m_row, 9))
                    # GREEN-highlight this row's winning-element cell if its value is
                    # a pure trigger value (and the row is non-FLAT, i.e. part of the
                    # pure group). Records (output-row-index, col) for batch formatting.
                    row_out_idx = len(all_output)
                    if (
                        m_trig_src is not None
                        and _int_token(m_row[m_trig_src]) in m_trig_vals
                        and _trigger_direction(m_row[2]) is not None
                    ):
                        green_cells.append((row_out_idx, m_trig_col))
                    # Weekday is display-only (col B); col L holds PER-MARKET-COUNT.
                    all_output.append([
                        market,                            # A
                        weekday,                           # B (DAY/LABEL, display-only)
                        cdate,                             # C
                        cprice,                            # D
                        cqf1,                              # E
                        cqf2,                              # F
                        cfire,                             # G
                        cair,                              # H
                        cwater,                            # I
                        cearth,                            # J
                        search_date,                       # K (forward date being scored)
                        str(mcount) if i == 0 else "",     # L (per-market count on first row)
                        "", "", "",                        # M, N, O
                        row_fig,                           # P (this row's own geomantic figure)
                        row_fig_num,                       # Q (GEO-FIG-NUM: 0-15 binary index)
                    ])

        all_results.append({
            "search_day": search_day,
            "search_date": search_date,
            "quality_sig": quality_sig,
            "is_match": is_match,
            "per_market": {
                m: {
                    "matches": len(per_market[m]["rows"]),
                    "up": per_market[m]["up"],
                    "dn": per_market[m]["dn"],
                }
                for m in MARKETS
            },
            "per_market_signal": per_market_signal,
            "total_matches": total_matches,
            "total_up": total_up,
            "total_dn": total_dn,
            "overall": overall,
            "overall_conf": overall_conf,
            "agreement": agree_label,
            "score": total_score,
            "score_overall": score_overall,
            "score_conf": score_conf,
            "geo_fig": fwd_figure,
        })

    log(f"  scored {len(all_results)} days, skipped {skipped_input}; {len(all_output)} FINAL-SIGNAL rows")
    log(
        f"  MATCH summary: MATCH days={match_days}, NO MATCH days={no_match_days}"
    )

    log("[4/4] Writing FINAL_SIGNAL + PREDICTION-FINAL...")
    if all_output:
        # Make the payload rectangular: pad EVERY row to FINAL_COLS so the trailing
        # SCORE/SCORE-OVERALL/SCORE-CONF cols (M:O) are always addressed. Data /
        # SEARCH-KEY / NO-MATCH rows are only 12 cols wide; a jagged values.update
        # can leave the trailing score cells unwritten, which surfaced as empty
        # M:O whenever the summary rows were the only 15-col rows in the payload.
        rect_output = [pad(r, FINAL_COLS) for r in all_output]
        write_sheet(
            FINAL_SIGNAL_ID,
            f"Sheet1!A2:R{len(rect_output) + 1}",
            rect_output,
        )

    # Reset format across a wide range (cols A:T) to clear any stale tint from
    # prior-schema runs, then re-apply per-row tints.
    fmt_requests: list[dict] = [{
        "repeatCell": {
            "range": {
                "sheetId": sheet_gid,
                "startRowIndex": 1,
                "endRowIndex": 5000,
                "startColumnIndex": 0,
                "endColumnIndex": 20,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 1, "green": 1, "blue": 1},
                    "textFormat": {"bold": False},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat.bold)",
        }
    }]
    for sep in separator_rows:
        r = sep["row"] + 1
        fmt_requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_gid,
                    "startRowIndex": r,
                    "endRowIndex": r + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": FINAL_COLS,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": sep["color"],
                        "textFormat": {"bold": True},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        })
    for kr in key_rows:
        r = kr + 1
        fmt_requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_gid,
                    "startRowIndex": r,
                    "endRowIndex": r + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": FINAL_COLS,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": KEY_YELLOW,
                        "textFormat": {"bold": False},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat.bold)",
            }
        })
    # ELEMENT TRIGGER: green-highlight the winning element's cell on each matched
    # row that belongs to a pure trigger value (applied after the row tints above).
    for ridx, col in green_cells:
        r = ridx + 1
        fmt_requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_gid,
                    "startRowIndex": r,
                    "endRowIndex": r + 1,
                    "startColumnIndex": col,
                    "endColumnIndex": col + 1,
                },
                "cell": {"userEnteredFormat": {"backgroundColor": GREEN_HL}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        })
    format_sheet(FINAL_SIGNAL_ID, {"requests": fmt_requests})

    # PREDICTION-FINAL: dynamic width = 3 fixed + 5*N + 6 summary (N = active markets).
    # Col C = QUALITY_SIG ('QF1 || QF2 || F=N A=N W=N E=N').
    # OVERALL_SIGNAL suffix: "" match day, " (NM)" no-match day.
    # Columns are built ONLY for active (visible) markets.
    PF_HEADER = ["DAY", "DATE", "QUALITY_SIG"]
    for m in MARKETS:
        PF_HEADER += [
            f"{m}_MATCHES", f"{m}_UP", f"{m}_DOWN", f"{m}_SIGNAL", f"{m}_CONF",
        ]
    PF_HEADER += [
        "TOTAL_MATCHES", "TOTAL_UP", "TOTAL_DOWN",
        "OVERALL_SIGNAL", "OVERALL_CONF", "AGREEMENT",
        "SCORE", "SCORE_OVERALL", "SCORE_CONF", "GEO_FIG",
    ]
    pf_ncols = len(PF_HEADER)
    pf_last_col = col_a1(pf_ncols)
    pf_rows: list[list] = [PF_HEADER]
    for r in all_results:
        per_conf = {}
        for m in MARKETS:
            mu, md = r["per_market"][m]["up"], r["per_market"][m]["dn"]
            mc = r["per_market"][m]["matches"]
            per_conf[m] = f"{(max(mu, md) / mc * 100):.0f}%" if mc else "0%"
        stage_suffix = "" if r["is_match"] else " (NM)"
        rowvals = [r["search_day"], r["search_date"], r["quality_sig"]]
        for m in MARKETS:
            rowvals += [
                r["per_market"][m]["matches"], r["per_market"][m]["up"],
                r["per_market"][m]["dn"], r["per_market_signal"][m], per_conf[m],
            ]
        rowvals += [
            r["total_matches"], r["total_up"], r["total_dn"],
            r["overall"] + stage_suffix, f"{r['overall_conf']:.0f}%",
            r["agreement"],
            r["score"], r["score_overall"] + stage_suffix, f"{r['score_conf']:.0f}%",
            r["geo_fig"],
        ]
        pf_rows.append(rowvals)

    pf_written = 0
    pf_status = "OK"
    pf_error = None
    try:
        # Clear the entire sheet so a shrink in active-market count (e.g. 4 -> 2,
        # or any width) always wipes stale columns from a prior wider-schema run.
        clear_sheet(PREDICTION_FINAL_ID, "Sheet1")
        if len(pf_rows) > 1:
            write_sheet(
                PREDICTION_FINAL_ID,
                f"Sheet1!A1:{pf_last_col}{len(pf_rows)}",
                pf_rows,
                raw=True,
            )
        pf_gid = get_sheet_gid(PREDICTION_FINAL_ID, "Sheet1")
        # Per-market block tints cycle; summary block (last 9 cols) is bold grey.
        market_tints = [
            {"red": 0.92, "green": 0.96, "blue": 1.0},
            {"red": 1.0, "green": 0.99, "blue": 0.85},
            {"red": 1.0, "green": 0.95, "blue": 0.88},
            {"red": 0.92, "green": 1.0, "blue": 0.92},
        ]
        pf_fmt: list[dict] = [
            {"repeatCell": {
                "range": {"sheetId": pf_gid, "startRowIndex": 0, "endRowIndex": len(pf_rows),
                          "startColumnIndex": 0, "endColumnIndex": pf_ncols},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "0"}}},
                "fields": "userEnteredFormat.numberFormat",
            }},
            {"repeatCell": {
                "range": {"sheetId": pf_gid, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": pf_ncols},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.82, "green": 0.82, "blue": 0.82},
                    "textFormat": {"bold": True},
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }},
        ]
        _start = 3
        for _idx, _m in enumerate(MARKETS):
            pf_fmt.append({"repeatCell": {
                "range": {"sheetId": pf_gid, "startRowIndex": 1, "endRowIndex": len(pf_rows),
                          "startColumnIndex": _start, "endColumnIndex": _start + 5},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": market_tints[_idx % len(market_tints)]}},
                "fields": "userEnteredFormat.backgroundColor",
            }})
            _start += 5
        pf_fmt.append({"repeatCell": {
            "range": {"sheetId": pf_gid, "startRowIndex": 1, "endRowIndex": len(pf_rows),
                      "startColumnIndex": _start, "endColumnIndex": pf_ncols},
            "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.96, "green": 0.96, "blue": 0.96},
                                           "textFormat": {"bold": True}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }})
        format_sheet(PREDICTION_FINAL_ID, {"requests": pf_fmt})
        pf_written = len(pf_rows) - 1
    except Exception as exc:
        pf_status = "ERROR"
        pf_error = str(exc)
        log(f"  PREDICTION-FINAL write failed: {exc}")
        raise

    msg = (
        f"Scored {len(all_results)} days (MATCH={match_days}, NM={no_match_days}); "
        f"wrote {len(all_output)} FINAL-SIGNAL rows + {pf_written} PREDICTION-FINAL rows"
    )
    emit_result(
        ok=True,
        rows_written=len(all_output),
        message=msg,
        extra={
            "daysProcessed": len(all_results),
            "matchDays": match_days,
            "noMatchDays": no_match_days,
            "skippedInput": skipped_input,
            "dbCounts": db_counts,
            "dbDroppedFuture": db_dropped_future,
            "dbDroppedUnparseable": db_dropped_unparseable,
            "dbUnparseableElements": db_unparseable_elements,
            "activeMarkets": MARKETS,
            "hiddenMarkets": hidden_markets,
            "predictionFinalRows": pf_written,
            "predictionFinalStatus": pf_status,
            "predictionFinalError": pf_error,
        },
    )
    return {"status": "SUCCESS"}


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log("ERROR: " + str(e))
        log(traceback.format_exc())
        emit_result(ok=False, error=str(e), message="Step 4 failed")
        sys.exit(1)
