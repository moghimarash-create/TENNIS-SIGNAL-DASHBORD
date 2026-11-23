#!/usr/bin/env python3
"""verify_logic.py — independent re-check of Step 4's DJIA match logic.

This script does NOT modify step4_search_signals.py. It independently
re-implements the progressive-narrowing match rule from scratch, runs it against
KEY-MATCH-DJIA for EVERY forward day in SEARCH-SIGNALS, and compares the result
to what Step 4 actually wrote to the FINAL-SIGNAL sheet for the DJIA market.

It imports the geomantic figure system and signal map from step4
(GEOMANCY_FIGURES + figure_from_elements + mazzaj_quadrant + GEO_SIGNAL_MAP — no
side effects, since step4's run() is guarded by __main__) so both the geo-adjusted
SCORE recompute and the trailing FIGURE + QUADRANT TALLY stay in lockstep with
step4's definitions.

The rule being verified (must match Step 4 exactly):
  base   = DAY(A) + QULITY-FIN-1(D) + QULITY-FIN-2(E)   (case-insensitive, trimmed)
  - A blank in any of A/D/E makes a row unmatchable (DB row dropped; forward day skipped).
  - Historical DB rows must have DATE(B) strictly BEFORE the earliest forward date.
  - If base yields < 3 rows: keep base as-is (0/1/2 rows), no narrowing.
  - If base yields >= 3 rows: progressively narrow but NEVER below 3, adding element
    columns on top of the LAST ACCEPTED set (Option B = if a stage would drop below 3,
    SKIP that stage's criteria but still try later stages; stop once at the floor of 3):
      Stage 2: + ELE-P-1(F) & ELE-P-2(G)
      Stage 3: + ELE-P-3(H)
      Stage 4: + ELE-P-4(I)

Comparison is by a per-row fingerprint (parsed DATE + normalized PRICE + the four
element columns) collected into a sorted multiset per forward day — robust to how
Sheets re-displays USER_ENTERED values, and immune to two distinct rows sharing a date.

Auth: requires GOOGLE_SERVICE_ACCOUNT_JSON in the environment (read-only use).
Run:  python3 verify_logic.py
"""

import json
import os
import re
import sys
from datetime import datetime

import requests
import google.auth.transport.requests
from google.oauth2.service_account import Credentials

# Geomantic figure system + signal map — defined in step4 (the figure/quadrant
# multiplier IS wired into Stage 4 scoring). Imported so the geo-adjusted score
# recompute and the figure/quadrant tally below stay in lockstep with step4.
from step4_search_signals import (
    GEOMANCY_FIGURES,
    figure_from_elements,
    figure_num_from_elements,
    mazzaj_quadrant,
    GEO_SIGNAL_MAP,
    GEO_DEFAULT_MULTIPLIER,
    SCORE_NEUTRAL_BAND,
    BULLISH_FIGURES,
    BEARISH_FIGURES,
    detect_element_trigger,
    format_trigger_compact,
    build_block_trigger_text,
    element_trigger_overall,
    count_block_overall,
    agreement_label,
    _int_token,
)

# ---- Config: identical IDs / tab to step4_search_signals.py ----
SEARCH_SIGNALS_ID = os.environ.get("TENNIS_SEARCH_SIGNALS_SHEET_ID", "")
DATA_SEARCH_KEY_ID = os.environ.get("TENNIS_SEARCH_KEY_SHEET_ID", "")
FINAL_SIGNAL_ID = os.environ.get("TENNIS_FINAL_SIGNAL_SHEET_ID", "")

MARKET = "DJIA"
DJIA_TAB = "KEY-MATCH-DJIA"

# Element-narrowing stages: indices into the (F, G, H, I) element vector.
NARROW_STAGES = [
    ((0, 1), "Stage 2  + ELE-P-1(F) & ELE-P-2(G)"),
    ((2,), "Stage 3  + ELE-P-3(H)"),
    ((3,), "Stage 4  + ELE-P-4(I)"),
]

# The manually-verified case. NOTE: 1/19/1970 is a HISTORICAL DJIA candidate row
# (a Monday), NOT a forward day — every forward day lives in 2026/2027. Because the
# weekday (DAY) is part of the base key, this Monday history row can only ever land
# in the match set of a *Monday* forward day. We therefore spotlight this historical
# row and, by default, trace the forward day whose final match set actually keeps it.
SPOTLIGHT_HIST = "1/19/1970"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def parse_args(argv):
    # --trace MM/DD/YYYY : force the forward day to trace in detail
    # --hist  MM/DD/YYYY : the historical DJIA row to spotlight (default 1/19/1970)
    trace_fwd, hist = None, SPOTLIGHT_HIST
    for i, a in enumerate(argv):
        if a == "--trace" and i + 1 < len(argv):
            trace_fwd = argv[i + 1]
        elif a.startswith("--trace="):
            trace_fwd = a.split("=", 1)[1]
        elif a == "--hist" and i + 1 < len(argv):
            hist = argv[i + 1]
        elif a.startswith("--hist="):
            hist = a.split("=", 1)[1]
    return trace_fwd, hist


# ---- Helpers replicated EXACTLY from step4 (do not "improve" them) ----
def norm(s):
    return str(s).strip().upper() if s is not None else ""


def base_key3(day, qf1, qf2):
    parts = (norm(day), norm(qf1), norm(qf2))
    if any(p == "" for p in parts):
        return None
    return parts


def pad(row, n):
    return list(row) + [""] * (n - len(row))


def parse_date(s):
    s = str(s).strip()
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# ---- Sheets I/O ----
def get_token():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        sys.exit("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON is not set in the environment.")
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def read_range(token, sheet_id, a1_range):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{a1_range}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    resp.raise_for_status()
    return resp.json().get("values", [])


# ---- Core: independent re-implementation of the narrowing matcher ----
def narrow(fwd_base, fwd_elem, db_rows, trace=None):
    """db_rows: list of (row9, bk, ev). Returns list of matched row9 (order preserved).

    If `trace` is a list, append human-readable step descriptions to it.
    """
    accepted = [(row, ev) for (row, bk, ev) in db_rows if bk == fwd_base]
    base_count = len(accepted)
    depth = 0
    if trace is not None:
        trace.append(f"base (DAY+QF1+QF2): {base_count} row(s) matched")
    if base_count >= 3:
        for cols, label in NARROW_STAGES:
            if len(accepted) <= 3:
                if trace is not None:
                    trace.append(
                        f"  {label}: NOT TRIED — already at floor "
                        f"({len(accepted)} rows); narrowing stops"
                    )
                break
            cand = [
                (row, ev) for (row, ev) in accepted
                if all(ev[c] == fwd_elem[c] for c in cols)
            ]
            if len(cand) >= 3:
                accepted = cand
                depth += 1
                if trace is not None:
                    trace.append(
                        f"  {label}: candidates={len(cand)} >= 3 -> APPLIED "
                        f"(kept {len(accepted)})"
                    )
            else:
                if trace is not None:
                    trace.append(
                        f"  {label}: candidates={len(cand)} < 3 -> SKIPPED "
                        f"(keep last accepted {len(accepted)})"
                    )
    else:
        if trace is not None:
            trace.append("  base < 3 -> return base as-is (no narrowing)")
    return [row for (row, ev) in accepted], base_count, depth


def load_db(token, cutoff):
    """Build DJIA db rows exactly as step4 does (cutoff + base + element vector)."""
    rows = read_range(token, DATA_SEARCH_KEY_ID, f"{DJIA_TAB}!A2:I")
    db_rows = []
    dropped_future = dropped_bad = 0
    for r in rows:
        r = pad(r, 9)
        row_date = parse_date(r[1])  # B = DATE
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
        db_rows.append((r, bk, ev))
    return db_rows, len(rows), dropped_future, dropped_bad


def load_step4_djia(token):
    """Read FINAL-SIGNAL; group DJIA data rows by forward date -> list of row fingerprints.

    DJIA data rows have A==DJIA, C=historical DATE, K(idx10)=FWD-DATE-SCORED.
    Each kept row is fingerprinted (date + price + 4 element cols) so the comparison
    cannot be fooled by two distinct DB rows that happen to share the same date.
    """
    # Read A2:R (cols include GEO-FIG col P, GEO-FIG-NUM col Q, ELEM-TRIGGER col R).
    # The match set is built from data rows (cols A:J) only, so the extra columns do
    # not affect the fingerprints — the comparison is unchanged by the display columns.
    rows = read_range(token, FINAL_SIGNAL_ID, "Sheet1!A2:R")
    by_fwd = {}
    for r in rows:
        r = pad(r, 18)
        if str(r[0]).strip().upper() != MARKET:
            continue
        fwd = parse_date(r[10])
        key = fwd.isoformat() if fwd else f"RAW:{str(r[10]).strip()}"
        # FINAL-SIGNAL data row: C(2)=hist date, D(3)=price, G:J(6..9)=ELE-P-1..4.
        fp = (
            date_iso(r[2]), pnum(r[3]),
            norm(r[6]), norm(r[7]), norm(r[8]), norm(r[9]),
        )
        by_fwd.setdefault(key, []).append(fp)
    return by_fwd


def load_step4_summary(token):
    """Read FINAL-SIGNAL per-day summary (banner) rows -> what Step 4 actually wrote.

    Returns (summary, active_markets) where summary maps forward-date-iso ->
    {"score", "score_overall", "geo_fig"} taken from the banner row (cols M/N/P),
    and active_markets is the set of market names seen in the DJIA-style data rows.
    The banner row (col B starts '>>>') is paired with the SEARCH-KEY row that
    immediately follows it (its col C holds the forward date being scored).
    """
    rows = read_range(token, FINAL_SIGNAL_ID, "Sheet1!A2:R")
    summary = {}
    active_markets = set()
    pending = None
    for r in rows:
        r = pad(r, 18)
        a = str(r[0]).strip()
        b = str(r[1]).strip()
        if b.startswith(">>>"):
            # SCORE = col M(12), SCORE-OVERALL = col N(13), GEO-FIG = col P(15).
            # Col P now reads "<fwd_figure> | FIG: nB/mb": the figure is the token
            # before " |"; the tally tail (if any) is kept raw for the tally check.
            raw_p = str(r[15]).strip()
            geo_fig = raw_p.split("|")[0].strip()
            tally = ""
            if "FIG:" in raw_p:
                tally = raw_p.split("FIG:", 1)[1].strip()
            pending = {"score": r[12], "score_overall": str(r[13]).strip(),
                       "geo_fig": geo_fig, "geo_p_raw": raw_p, "tally": tally}
        elif b.upper() == "SEARCH-KEY" and pending is not None:
            fwd = parse_date(r[2])
            key = fwd.isoformat() if fwd else f"RAW:{str(r[2]).strip()}"
            # SEARCH-KEY col P holds "KEY: <fwd_figure>"; strip the label.
            keyp = str(r[15]).strip()
            pending["key_fig"] = (
                keyp[4:].strip() if keyp.upper().startswith("KEY:") else keyp
            )
            summary[key] = pending
            pending = None
        elif a and a != "—":
            active_markets.add(a.upper())
    return summary, active_markets


def load_step4_rowfigs(token):
    """Per-row GEO-FIG check across ALL market data rows: each data row's col P must
    equal the figure of its OWN element cols G:J. The per-row figure is computed from
    a row's own elements, so this is market-independent — it verifies feature #1
    regardless of which KEY-MATCH market happens to be active. Returns (expected, written).
    """
    rows = read_range(token, FINAL_SIGNAL_ID, "Sheet1!A2:R")
    out = []
    for r in rows:
        r = pad(r, 18)
        a = str(r[0]).strip()
        b = str(r[1]).strip()
        # Skip banner (">>> ..."), SEARCH-KEY, NO-MATCH ("—"), and blank-A rows;
        # keep only true per-market data rows (col A = market name).
        if not a or a == "—" or b.startswith(">>>") or b.upper() == "SEARCH-KEY":
            continue
        # Data row elements ELE-P-1..4 live in cols G:J (idx 6..9); written fig in P(15).
        expected = figure_from_elements(
            _intensity(r[6]) or 0, _intensity(r[7]) or 0,
            _intensity(r[8]) or 0, _intensity(r[9]) or 0,
        )
        out.append((expected, str(r[15]).strip()))
    return out


def load_step4_fignums(token):
    """GEO-FIG-NUM check across ALL figure-bearing rows (data rows, SEARCH-KEY rows,
    and per-day summary banner rows). For every row that carries a GEO-FIG figure in
    col P (idx15), extract the bare figure name and read GEO-FIG-NUM in col Q (idx16),
    then verify:
      (a) consistency: the written num equals the canonical binary index of that
          figure's parity tuple (FIRE MSB) via figure_num_from_elements(*pattern);
      (b) bijection: figure<->num is 1:1 across every row (no figure maps to two
          nums, no num maps to two figures).
    Returns (rows, fig_to_nums, num_to_figs) where rows is a list of
    (figure_name, written_num, expected_num, ok).
    P-cell formats: data row = "<Figure>"; SEARCH-KEY row = "KEY: <Figure>";
    banner row = "<Figure> | FIG: nB/mb".
    """
    name_to_pattern = {v: k for k, v in GEOMANCY_FIGURES.items()}
    rows = read_range(token, FINAL_SIGNAL_ID, "Sheet1!A2:R")
    out = []
    fig_to_nums: dict[str, set] = {}
    num_to_figs: dict[str, set] = {}
    for r in rows:
        r = pad(r, 18)
        p = str(r[15]).strip()
        if not p:
            continue
        # Extract the bare figure name from any of the three P-cell formats.
        name = p
        if name.upper().startswith("KEY:"):
            name = name.split(":", 1)[1].strip()
        if " |" in name:
            name = name.split(" |", 1)[0].strip()
        # Only verify recognized figure names (skip anything non-figure in col P).
        pattern = name_to_pattern.get(name)
        if pattern is None:
            continue
        written = str(r[16]).strip()
        expected = str(figure_num_from_elements(*pattern))
        ok = written == expected
        out.append((name, written, expected, ok))
        fig_to_nums.setdefault(name, set()).add(written)
        num_to_figs.setdefault(written, set()).add(name)
    return out, fig_to_nums, num_to_figs


def load_step4_triggers(token):
    """ELEM-TRIGGER (col R) self-consistency check — PER MARKET within each block.

    Group the sheet's OWN matched data rows by (forward date, market=col A), then
    recompute build_block_trigger_text (which runs detect_element_trigger SEPARATELY
    per market, in first-appearance market order = step4's MARKETS write order) and
    compare to col R (idx17) on the block's summary banner row. Returns (results,
    by_fwd) where results is a list of (fwd_iso, expected_text, written_text, ok) and
    by_fwd maps fwd_iso -> {market: (name, pure)} so callers can assert a specific
    market in a specific block (e.g. 5/27 BTC -> EARTH).

    NOTE: ELEM-TRIGGER moved from col Q to col R (idx17) when GEO-FIG-NUM was added.
    """
    rows = read_range(token, FINAL_SIGNAL_ID, "Sheet1!A2:R")
    rows = [pad(r, 18) for r in rows]
    # Pass 1: collect matched data rows per (forward date, market) as detector-shaped
    # 9-col rows (idx2=price, idx5..8=ELE-P-1..4 from sheet cols D, G:J), preserving
    # market first-appearance order so the recompute joins markets exactly as written.
    block_rows: dict[str, dict[str, list]] = {}
    mkt_order: dict[str, list[str]] = {}
    written: dict[str, str] = {}
    order: list[str] = []
    pending_fwd = None

    def _ensure(key):
        if key not in block_rows:
            block_rows[key] = {}
            mkt_order[key] = []
            order.append(key)

    for r in rows:
        a = str(r[0]).strip()
        b = str(r[1]).strip()
        if b.startswith(">>>"):
            # Summary banner: pair its col R with the forward date on the following
            # SEARCH-KEY row. Stash the written trigger keyed by that date.
            pending_fwd = {"q": str(r[17]).strip()}
            continue
        if b.upper() == "SEARCH-KEY" and pending_fwd is not None:
            fwd = parse_date(r[2])
            key = fwd.isoformat() if fwd else f"RAW:{str(r[2]).strip()}"
            written[key] = pending_fwd["q"]
            _ensure(key)
            pending_fwd = None
            continue
        if not a or a == "—":
            continue
        # Matched data row: build a 9-col detector row, bucketed by its market (col A).
        fwd = parse_date(r[10])
        key = fwd.isoformat() if fwd else f"RAW:{str(r[10]).strip()}"
        _ensure(key)
        if a not in block_rows[key]:
            block_rows[key][a] = []
            mkt_order[key].append(a)
        block_rows[key][a].append(["", "", r[3], "", "", r[6], r[7], r[8], r[9]])
    results = []
    by_fwd = {}
    for key in order:
        per_mkt = block_rows.get(key, {})
        markets = mkt_order.get(key, [])
        by_fwd[key] = {
            m: detect_element_trigger(per_mkt[m]) for m in markets
        }
        expected = build_block_trigger_text(per_mkt, markets)
        wrote = written.get(key, "")
        # A no-match block has no matched rows -> col R empty; recompute -> "".
        ok = (expected == wrote)
        results.append((key, expected, wrote, ok))
    return results, by_fwd


def load_step4_overall(token):
    """Independent recompute of the HYBRID Overall (banner cols D/E/F).

    DIRECTION (D) + CONFIDENCE (E) are recomputed count-based via the SHARED
    count_block_overall(); the AGREEMENT LABEL (F) is recomputed by comparing the SHARED
    element_trigger_overall() verdict to the count direction via agreement_label() — the
    exact code step4 uses to WRITE, so the two cannot drift.

    Mirrors load_step4_triggers' grouping: collect each block's matched data rows per
    (forward date, market) as detector-shaped 9-col rows (idx2=price from sheet D,
    idx5..8=ELE-P-1..4 from sheet G:J), and capture the forward day's element values
    from the yellow SEARCH-KEY row (sheet cols G:J = FIRE/AIR/WATER/EARTH). Compare to
    the written banner: D(idx3) 'Overall: X', E(idx4) 'Conf: Y%', F(idx5) 'Agree: LABEL'.

    Returns (results, by_fwd) where results is a list of
    (fwd_iso, exp_overall, exp_conf, wr_overall, wr_conf, exp_label, wr_label, ok) and
    by_fwd maps fwd_iso -> (exp_overall, exp_label) for targeted assertions
    (e.g. 3/27/2026 -> DOWN + CONFIRMED, 5/12/2026 -> UP, 5/15/2026 -> DOWN).
    """
    rows = read_range(token, FINAL_SIGNAL_ID, "Sheet1!A2:R")
    rows = [pad(r, 18) for r in rows]
    block_rows: dict[str, dict[str, list]] = {}
    mkt_order: dict[str, list[str]] = {}
    fwd_vals: dict[str, dict[str, int]] = {}
    written: dict[str, tuple] = {}
    order: list[str] = []
    pending = None

    def _ensure(key):
        if key not in block_rows:
            block_rows[key] = {}
            mkt_order[key] = []
            order.append(key)

    for r in rows:
        a = str(r[0]).strip()
        b = str(r[1]).strip()
        if b.startswith(">>>"):
            # Summary banner: stash written Overall/Conf/Agree, paired to next SEARCH-KEY.
            pending = {
                "overall": str(r[3]).strip(),
                "conf": str(r[4]).strip(),
                "agree": str(r[5]).strip(),
            }
            continue
        if b.upper() == "SEARCH-KEY" and pending is not None:
            fwd = parse_date(r[2])
            key = fwd.isoformat() if fwd else f"RAW:{str(r[2]).strip()}"
            written[key] = (pending["overall"], pending["conf"], pending["agree"])
            fwd_vals[key] = {
                "FIRE": _int_token(r[6]), "AIR": _int_token(r[7]),
                "WATER": _int_token(r[8]), "EARTH": _int_token(r[9]),
            }
            _ensure(key)
            pending = None
            continue
        if not a or a == "—":
            continue
        fwd = parse_date(r[10])
        key = fwd.isoformat() if fwd else f"RAW:{str(r[10]).strip()}"
        _ensure(key)
        if a not in block_rows[key]:
            block_rows[key][a] = []
            mkt_order[key].append(a)
        block_rows[key][a].append(["", "", r[3], "", "", r[6], r[7], r[8], r[9]])

    results = []
    by_fwd = {}
    for key in order:
        per_mkt = block_rows.get(key, {})
        markets = mkt_order.get(key, [])
        fv = fwd_vals.get(key, {})
        # DIRECTION + CONFIDENCE: count-based (shared SSOT).
        exp_overall, exp_conf, _pm_sig, _tu, _td, _tm = count_block_overall(
            per_mkt, markets
        )
        # AGREEMENT LABEL: element-trigger verdict vs count direction (shared SSOT).
        elem_dir, _ec, _votes, _ea = element_trigger_overall(per_mkt, markets, fv)
        exp_label = agreement_label(exp_overall, elem_dir)
        wr = written.get(key, ("", "", ""))
        wr_overall = wr[0].replace("Overall:", "").strip()
        wr_conf = wr[1].replace("Conf:", "").replace("%", "").strip()
        wr_label = wr[2].replace("Agree:", "").strip()
        exp_conf_str = f"{exp_conf:.0f}"
        ok = (
            exp_overall == wr_overall
            and exp_conf_str == wr_conf
            and exp_label == wr_label
        )
        results.append(
            (key, exp_overall, exp_conf_str, wr_overall, wr_conf, exp_label, wr_label, ok)
        )
        by_fwd[key] = (exp_overall, exp_label)
    return results, by_fwd


def date_iso(s):
    d = parse_date(s)
    return d.isoformat() if d else f"RAW:{str(s).strip()}"


def pnum(x):
    # Normalize a price cell so RAW (KEY-MATCH) vs USER_ENTERED-reformatted
    # (FINAL-SIGNAL) values compare equal: parse to float when possible.
    s = str(x).strip().replace(",", "").replace("$", "")
    if s == "":
        return ""
    try:
        return f"{float(s):.6g}"
    except ValueError:
        return norm(x)


def fp_db(r):
    # Row fingerprint for a KEY-MATCH-DJIA db row (padded A:I), matching the
    # FINAL-SIGNAL fingerprint above: date + price + the four element columns
    # (source F,G,H,I = r[5..8], written to FINAL-SIGNAL cols G:J).
    return (
        date_iso(r[1]), pnum(r[2]),
        norm(r[5]), norm(r[6]), norm(r[7]), norm(r[8]),
    )


# ---- Geomantic trigger tally helpers (analysis-only) ----
def _intensity(cell):
    # Element / quality cell like "1 FIRE" or "3 COLD" -> leading int. None if blank/bad.
    parts = str(cell).strip().split()
    if not parts:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


def _qf_label(cell):
    # QULITY-FIN-2 cell like "6 DRY" -> humoral label "DRY" (upper). "" if absent.
    parts = str(cell).strip().split()
    return parts[1].upper() if len(parts) >= 2 else ""


def _price_dir(cell):
    # DAILY PRICE -> "UP" (>0) / "DOWN" (<0) / "FLAT" (==0); None if unparseable.
    s = str(cell).strip().replace(",", "").replace("$", "")
    if s == "":
        return None
    try:
        p = float(s)
    except ValueError:
        return None
    return "UP" if p > 0 else "DOWN" if p < 0 else "FLAT"


def _row_geo(r9):
    """(figure, quadrant) for a padded A:I row, matching step4._row_figure_quadrant.
    Uses a 0-fallback on blank/unparseable cells (identical to step4's _int_token)."""
    figure = figure_from_elements(
        _intensity(r9[5]) or 0, _intensity(r9[6]) or 0,
        _intensity(r9[7]) or 0, _intensity(r9[8]) or 0,
    )
    quadrant = mazzaj_quadrant(_intensity(r9[3]) or 0, _qf_label(r9[4]))
    return figure, quadrant


def _geo_score(matched, fwd_elem):
    """Recompute step4's DJIA geo-adjusted match-depth score for one forward day.
    Mirrors the scoring loop: day_score = match_weight * direction * geo_mult,
    summed over matched rows. Returns (total_score, sum_abs, score_overall)."""
    total = 0.0
    sabs = 0.0
    for r in matched:
        r9 = pad(r, 9)
        weight = 1 + sum(1 for k in range(4) if norm(r9[5 + k]) == fwd_elem[k])
        d = _price_dir(r9[2])
        direction = 1 if d == "UP" else -1 if d == "DOWN" else 0
        fig, quad = _row_geo(r9)
        mult = GEO_SIGNAL_MAP.get((fig, quad), GEO_DEFAULT_MULTIPLIER)
        ds = weight * direction * mult
        total += ds
        sabs += abs(ds)
    total = round(total, 4)
    sabs = round(sabs, 4)
    ratio = (total / sabs) if sabs > 0 else 0.0
    overall = (
        "UP" if ratio >= SCORE_NEUTRAL_BAND
        else "DOWN" if ratio <= -SCORE_NEUTRAL_BAND
        else "NEUTRAL"
    )
    return total, sabs, overall


def main():
    trace_fwd, spotlight_hist = parse_args(sys.argv[1:])
    token = get_token()

    # --- forward days + cutoff (identical derivation to step4) ---
    search_data = read_range(token, SEARCH_SIGNALS_ID, "Sheet1!A2:I")
    fdates = [parse_date(r[1]) for r in search_data if len(r) > 1]
    fdates = [d for d in fdates if d is not None]
    cutoff = min(fdates) if fdates else None

    db_rows, db_read, drop_future, drop_bad = load_db(token, cutoff)
    step4_djia = load_step4_djia(token)
    step4_summary, active_markets = load_step4_summary(token)

    # --- independent recomputation for every forward day ---
    mine = {}              # fwd-date-iso -> sorted list of hist-date-iso
    fwd_info = {}          # fwd-date-iso -> (sday, sdate_raw, fwd_base, fwd_elem)
    fwd_order = []         # preserve sheet order for default trace selection
    mine_matched = {}      # fwd-date-iso -> accumulated matched DJIA rows (for scoring)
    mine_geofig = {}       # fwd-date-iso -> forward day's own geomantic figure
    skipped = 0
    dup_fwd = 0
    seen_fwd = set()
    for r in search_data:
        r = pad(r, 9)
        sday, sdate_raw = r[0], r[1]
        fwd_base = base_key3(r[0], r[3], r[4])
        if fwd_base is None:
            skipped += 1
            continue
        fwd_elem = (norm(r[5]), norm(r[6]), norm(r[7]), norm(r[8]))
        fdate = parse_date(sdate_raw)
        key = fdate.isoformat() if fdate else f"RAW:{str(sdate_raw).strip()}"
        if key in seen_fwd:
            dup_fwd += 1
        seen_fwd.add(key)

        matched, base_count, depth = narrow(fwd_base, fwd_elem, db_rows)
        # Aggregate per forward-date key (mirrors Step 4 grouping all DJIA rows by
        # the FWD-DATE-SCORED column) so duplicate forward dates compare symmetrically.
        if key not in fwd_info:
            fwd_order.append(key)
        mine.setdefault(key, []).extend(fp_db(r) for r in matched)
        mine_matched.setdefault(key, []).extend(matched)
        # Forward day's OWN figure (GEO-FIG): from its element cols F:I (0-fallback).
        mine_geofig[key] = figure_from_elements(
            _intensity(r[5]) or 0, _intensity(r[6]) or 0,
            _intensity(r[7]) or 0, _intensity(r[8]) or 0,
        )
        fwd_info[key] = (sday, str(sdate_raw).strip(), fwd_base, fwd_elem)

    # --- spotlight: which forward days KEEP the historical row (e.g. 1/19/1970) ---
    spot_d = parse_date(spotlight_hist)
    spot_iso = spot_d.isoformat() if spot_d else None
    kept_with_spot = [
        k for k in fwd_order
        if spot_iso and any(fp[0] == spot_iso for fp in mine[k])
    ]
    # Locate the spotlight row in the DJIA db (after cutoff + base filtering) and
    # find which forward days even consider it as a BASE candidate (same base key).
    spot_db = [(r, bk, ev) for (r, bk, ev) in db_rows if parse_date(r[1]) == spot_d]
    spot_in_db = len(spot_db) > 0
    spot_bk = spot_db[0][1] if spot_in_db else None
    base_cand_fwds = [k for k in fwd_order if spot_bk and fwd_info[k][2] == spot_bk]

    # --- choose the forward day to trace in detail ---
    trace_key = None
    trace_note = ""
    if trace_fwd:
        td = parse_date(trace_fwd)
        cand = td.isoformat() if td else f"RAW:{trace_fwd.strip()}"
        if cand in fwd_info:
            trace_key = cand
            trace_note = "(requested via --trace)"
        else:
            trace_note = f"(requested {trace_fwd} is not a forward day)"
    if trace_key is None and kept_with_spot:
        trace_key = kept_with_spot[0]
        trace_note = f"(auto: first forward day whose match keeps {spotlight_hist})"
    if trace_key is None:
        mondays = [k for k in fwd_order if str(fwd_info[k][0]).strip().upper().startswith("MON")]
        trace_key = (mondays or fwd_order)[0]
        trace_note = "(auto: first Monday forward day)" if mondays else "(auto: first forward day)"

    sday, sdate_raw, fwd_base, fwd_elem = fwd_info[trace_key]
    trace_lines = []
    matched, base_count, depth = narrow(fwd_base, fwd_elem, db_rows, trace=trace_lines)
    trace_header = {
        "day": sday, "date": sdate_raw, "base": fwd_base, "elem": fwd_elem,
        "matched": matched, "base_count": base_count, "depth": depth, "key": trace_key,
    }

    # --- compare mine vs step4 over the union of forward dates ---
    all_keys = set(mine) | set(step4_djia)
    agree = 0
    discrepancies = []
    for k in sorted(all_keys):
        a = sorted(mine.get(k, []))
        b = sorted(step4_djia.get(k, []))
        if a == b:
            agree += 1
        else:
            discrepancies.append((k, a, b))

    # --- report ---
    out = []
    out.append("=" * 70)
    out.append("   INDEPENDENT VERIFICATION — Step 4 DJIA progressive-narrowing")
    out.append("=" * 70)
    out.append(f"  SEARCH-SIGNALS : {SEARCH_SIGNALS_ID}")
    out.append(f"  KEY-MATCH-DJIA : {DATA_SEARCH_KEY_ID} (tab {DJIA_TAB})")
    out.append(f"  FINAL-SIGNAL   : {FINAL_SIGNAL_ID}")
    out.append("")
    out.append(f"  Forward-date cutoff (DB rows must be < this): "
               f"{cutoff.isoformat() if cutoff else 'none'}")
    out.append(f"  DJIA DB rows: read={db_read}  kept={len(db_rows)}  "
               f"dropped_future={drop_future}  dropped_unmatchable={drop_bad}")
    out.append(f"  Forward days in SEARCH-SIGNALS: {len(search_data)}")
    out.append(f"  Forward days skipped (blank A/D/E): {skipped}")
    if dup_fwd:
        out.append(f"  WARNING: {dup_fwd} duplicate forward date(s) detected")
    out.append("")
    out.append("-" * 70)
    out.append("  RESULT — independent recompute vs. what Step 4 wrote (DJIA)")
    out.append("-" * 70)
    out.append(f"  Forward days compared : {len(all_keys)}")
    out.append(f"  MATCH (identical)     : {agree}")
    out.append(f"  DISCREPANCIES         : {len(discrepancies)}")
    if discrepancies:
        out.append("")
        out.append("  Discrepancy detail (fwd-date | mine | step4):")
        for k, a, b in discrepancies[:50]:
            only_mine = sorted(set(a) - set(b))
            only_s4 = sorted(set(b) - set(a))
            out.append(f"   - {k}: mine={len(a)} step4={len(b)}")
            if only_mine:
                out.append(f"       only in mine : {only_mine}")
            if only_s4:
                out.append(f"       only in step4: {only_s4}")
        if len(discrepancies) > 50:
            out.append(f"   ... and {len(discrepancies) - 50} more")
    else:
        out.append("")
        out.append("  >> PERFECT: every forward day's DJIA match set is identical.")
    out.append("")

    # --- GEO-FIG + geo-adjusted scoring verification ---
    # The geomantic multiplier (GEO_SIGNAL_MAP) only RE-WEIGHTS day_score; it never
    # changes which rows match, so the match-set comparison above is unaffected by it.
    # Here we independently recompute (a) each forward day's own GEO-FIG figure and
    # (b) the DJIA geo-adjusted SCORE, then compare to what Step 4 wrote.
    out.append("-" * 70)
    out.append("  GEO-FIG + GEO-ADJUSTED SCORING (col P + cols M/N)")
    out.append("-" * 70)
    out.append(f"  GEO_SIGNAL_MAP notable combos: {len(GEO_SIGNAL_MAP)} "
               f"(default multiplier = {GEO_DEFAULT_MULTIPLIER})")
    out.append(f"  Active markets in FINAL-SIGNAL: "
               f"{sorted(active_markets) if active_markets else '(none)'}")

    # (a) GEO-FIG: forward day's own figure, mine vs step4 (market-independent).
    geo_keys = [k for k in fwd_order if k in step4_summary]
    geo_match = 0
    geo_mismatch = []
    for k in geo_keys:
        if mine_geofig.get(k) == step4_summary[k]["geo_fig"]:
            geo_match += 1
        else:
            geo_mismatch.append((k, mine_geofig.get(k), step4_summary[k]["geo_fig"]))
    out.append("")
    out.append(f"  GEO-FIG forward days compared : {len(geo_keys)}")
    out.append(f"  GEO-FIG identical (mine==step4): {geo_match}")
    out.append(f"  GEO-FIG mismatches            : {len(geo_mismatch)}")
    for k, a, b in geo_mismatch[:20]:
        out.append(f"   - {k}: mine={a!r} step4={b!r}")
    if not geo_mismatch and geo_keys:
        out.append("  >> PERFECT: every forward day's GEO-FIG figure is identical.")

    # (a2) SEARCH-KEY "KEY: <fig>" should equal the forward day's own figure.
    key_match = 0
    key_mismatch = []
    for k in geo_keys:
        if step4_summary[k].get("key_fig") == mine_geofig.get(k):
            key_match += 1
        else:
            key_mismatch.append((k, mine_geofig.get(k), step4_summary[k].get("key_fig")))
    out.append("")
    out.append(f"  SEARCH-KEY figure identical    : {key_match}/{len(geo_keys)}")
    for k, a, b in key_mismatch[:20]:
        out.append(f"   - {k}: mine={a!r} key={b!r}")
    if not key_mismatch and geo_keys:
        out.append("  >> PERFECT: every SEARCH-KEY 'KEY:' figure matches the forward figure.")

    # (a3) Per-row GEO-FIG: each market data row's col P must equal the figure of its
    # OWN elements (market-independent — verifies feature #1 for every active market).
    row_figs = load_step4_rowfigs(token)
    rowfig_match = sum(1 for exp, wr in row_figs if exp == wr)
    rowfig_bad = [(exp, wr) for exp, wr in row_figs if exp != wr]
    out.append("")
    out.append(f"  Per-row GEO-FIG (all data rows): {rowfig_match}/{len(row_figs)} identical")
    for exp, wr in rowfig_bad[:20]:
        out.append(f"   - expected={exp!r} written={wr!r}")
    if not rowfig_bad and row_figs:
        out.append("  >> PERFECT: every matched data row carries its own correct figure.")

    # (a3a) GEO-FIG-NUM (col Q): every figure-bearing row's GEO-FIG-NUM must equal the
    # canonical 0-15 binary index of its GEO-FIG figure (FIRE MSB), AND the figure<->num
    # mapping must be bijective (1:1) across ALL rows.
    fignum_rows, fig_to_nums, num_to_figs = load_step4_fignums(token)
    fignum_match = sum(1 for _n, _w, _e, ok in fignum_rows if ok)
    fignum_bad = [(n, w, e) for n, w, e, ok in fignum_rows if not ok]
    out.append("")
    out.append(f"  GEO-FIG-NUM (all figure rows)  : {fignum_match}/{len(fignum_rows)} match binary index")
    for n, w, e in fignum_bad[:20]:
        out.append(f"   - {n}: written={w!r} expected={e!r}")
    fig_collisions = {f: sorted(ns) for f, ns in fig_to_nums.items() if len(ns) != 1}
    num_collisions = {n: sorted(fs) for n, fs in num_to_figs.items() if len(fs) != 1}
    out.append(f"  GEO-FIG-NUM bijection (fig<->num): "
               f"{len(fig_collisions)} figure-collisions, {len(num_collisions)} num-collisions")
    for f, ns in list(fig_collisions.items())[:20]:
        out.append(f"   - figure {f!r} -> multiple nums {ns}")
    for n, fs in list(num_collisions.items())[:20]:
        out.append(f"   - num {n!r} -> multiple figures {fs}")
    if not fignum_bad and not fig_collisions and not num_collisions and fignum_rows:
        out.append("  >> PERFECT: GEO-FIG-NUM is the correct binary index and bijective with GEO-FIG.")

    # (a3b) ELEM-TRIGGER (col R): recompute the trigger PER MARKET within each block
    # from the sheet's OWN matched rows and confirm col R matches the recompute.
    out.append("")
    out.append("-" * 70)
    out.append("  ELEM-TRIGGER (col R, per match block — PER MARKET)")
    out.append("-" * 70)
    trig_results, trig_by_fwd = load_step4_triggers(token)
    trig_match = sum(1 for _k, _e, _w, ok in trig_results if ok)
    trig_bad = [(k, e, w) for k, e, w, ok in trig_results if not ok]
    out.append(f"  Blocks compared (col R vs recompute): {trig_match}/{len(trig_results)} identical")
    for k, e, w in trig_bad[:20]:
        out.append(f"   - {k}: expected={e!r} written={w!r}")
    if not trig_bad and trig_results:
        out.append("  >> PERFECT: every block's per-market ELEM-TRIGGER matches the recompute.")
    # Assert the user's reference block: Wed 5/27/2026 BTC must resolve to EARTH.
    ref_key = "2026-05-27"
    ref_markets = trig_by_fwd.get(ref_key, {})
    ref_name, ref_pure = ref_markets.get("BTC", (None, []))
    ref_written = next((w for k, _e, w, _ok in trig_results if k == ref_key), "(block not found)")
    ref_ok = (ref_name == "EARTH")
    out.append("")
    out.append(f"  REF Wed 5/27/2026 BTC trigger element: {ref_name!r} "
               f"(expected 'EARTH') -> {'OK' if ref_ok else 'FAIL'}")
    out.append(f"       BTC segment: {format_trigger_compact('BTC', ref_name, ref_pure)!r}")
    out.append(f"       col R written: {ref_written!r}")
    if not ref_ok:
        out.append("  >> FAIL: 5/27/2026 BTC block did NOT resolve to EARTH.")

    # (a3c) HYBRID OVERALL (banner cols D/E/F): independently recompute the count-based
    # DIRECTION + CONFIDENCE via the SHARED count_block_overall AND the 3-state AGREEMENT
    # LABEL via element_trigger_overall + agreement_label, and confirm the written banner
    # Overall / Conf / Agree-label match.
    out.append("")
    out.append("-" * 70)
    out.append("  OVERALL (count-based direction/conf + element-trigger AGREEMENT label, banner D/E/F)")
    out.append("-" * 70)
    ovr_results, ovr_by_fwd = load_step4_overall(token)
    ovr_match = sum(1 for r in ovr_results if r[7])
    ovr_bad = [r for r in ovr_results if not r[7]]
    out.append(f"  Blocks compared (banner vs recompute): {ovr_match}/{len(ovr_results)} identical")
    for k, eo, ec, wo, wc, el, wl, _ok in ovr_bad[:20]:
        out.append(
            f"   - {k}: expected={eo} {ec}% label={el} | "
            f"written={wo} {wc}% label={wl}"
        )
    if not ovr_bad and ovr_results:
        out.append("  >> PERFECT: every block's Overall/Conf/AGREEMENT-label matches the recompute.")

    # Assert the user's reference blocks (direction must be COUNT-based, NOT forced
    # NEUTRAL when the element trigger is silent):
    #   5/12/2026 -> UP   (count majority up; element trigger may be SILENT)
    #   5/15/2026 -> UP   (pooled across all markets 12 up vs 6 down = UP; the BTC slice
    #                alone is 0u/3d, but Overall pools all active markets)
    #   3/27/2026 -> DOWN + CONFIRMED (count down AND element trigger agrees: EARTH winner,
    #                fwd EARTH=2, two matched rows EARTH=2 both DOWN)
    out.append("")
    ovr_refs = [
        ("2026-05-12", "UP", None),
        ("2026-05-15", "UP", None),
        ("2026-03-27", "DOWN", "CONFIRMED"),
    ]
    all_ref_ok = True
    for ref_key, exp_dir, exp_lbl in ovr_refs:
        got = ovr_by_fwd.get(ref_key)
        ref_row = next((r for r in ovr_results if r[0] == ref_key), None)
        if got is None:
            all_ref_ok = False
            out.append(f"  REF {ref_key} Overall: (block not found) -> FAIL")
            continue
        got_dir, got_lbl = got
        ref_ok = (got_dir == exp_dir) and (exp_lbl is None or got_lbl == exp_lbl)
        all_ref_ok = all_ref_ok and ref_ok
        want = f"'{exp_dir}'" + (f" + '{exp_lbl}'" if exp_lbl else "")
        out.append(
            f"  REF {ref_key} Overall: {got_dir!r} label={got_lbl!r} (expected {want}) "
            f"-> {'OK' if ref_ok else 'FAIL'}"
        )
        if ref_row is not None:
            out.append(f"       recompute: {ref_row[1]} conf={ref_row[2]}% label={ref_row[5]}")
            out.append(f"       banner written: {ref_row[3]} conf={ref_row[4]}% label={ref_row[6]}")
    if not all_ref_ok:
        out.append("  >> FAIL: one or more OVERALL reference blocks did not match.")

    # (a4) Bullish/bearish tally on the summary row. Step 4 tallies across ALL active
    # markets, so this is strictly comparable only when DJIA is the sole market;
    # otherwise the DJIA-only count is shown for reference.
    out.append("")
    if active_markets == {MARKET}:
        tally_match = 0
        tally_diffs = []
        for k in geo_keys:
            bull = sum(1 for r in mine_matched.get(k, [])
                       if figure_from_elements(
                           _intensity(pad(r, 9)[5]) or 0, _intensity(pad(r, 9)[6]) or 0,
                           _intensity(pad(r, 9)[7]) or 0, _intensity(pad(r, 9)[8]) or 0,
                       ) in BULLISH_FIGURES)
            bear = sum(1 for r in mine_matched.get(k, [])
                       if figure_from_elements(
                           _intensity(pad(r, 9)[5]) or 0, _intensity(pad(r, 9)[6]) or 0,
                           _intensity(pad(r, 9)[7]) or 0, _intensity(pad(r, 9)[8]) or 0,
                       ) in BEARISH_FIGURES)
            expected = f"{bull}B/{bear}b"
            if step4_summary[k].get("tally") == expected:
                tally_match += 1
            else:
                tally_diffs.append((k, expected, step4_summary[k].get("tally")))
        out.append(f"  FIG tally identical (DJIA-only): {tally_match}/{len(geo_keys)}")
        for k, mine_v, s4_v in tally_diffs[:20]:
            out.append(f"   - {k}: mine={mine_v!r} step4={s4_v!r}")
        if not tally_diffs and geo_keys:
            out.append("  >> PERFECT: every summary FIG tally matches the DJIA recompute.")
    else:
        out.append(f"  FIG tally check: SKIPPED — Step 4 tallies {len(active_markets)} markets "
                   f"but this verifier counts DJIA only (format presence verified above).")

    # (b) Geo-adjusted SCORE: only exactly comparable when DJIA is the sole active
    # market (Step 4's SCORE aggregates ALL active markets; this verifier is DJIA-only)
    # and there are no duplicate forward dates.
    out.append("")
    single_djia = active_markets == {MARKET}
    if not single_djia:
        out.append(f"  SCORE check: SKIPPED — Step 4's SCORE aggregates {len(active_markets)} "
                   f"markets but this verifier recomputes DJIA only.")
        out.append("  (DJIA-only geo-adjusted scores still computed below for reference.)")
    elif dup_fwd:
        out.append(f"  SCORE check: SKIPPED — {dup_fwd} duplicate forward date(s) make the "
                   f"per-banner comparison ambiguous.")
    else:
        score_match = 0
        score_overall_match = 0
        score_diffs = []
        for k in geo_keys:
            total, sabs, overall = _geo_score(mine_matched.get(k, []), fwd_info[k][3])
            try:
                written = float(str(step4_summary[k]["score"]).replace(",", ""))
            except (ValueError, TypeError):
                written = None
            if written is not None and abs(written - total) < 0.01:
                score_match += 1
            else:
                score_diffs.append((k, total, step4_summary[k]["score"]))
            if overall == step4_summary[k]["score_overall"]:
                score_overall_match += 1
        out.append(f"  SCORE forward days compared   : {len(geo_keys)}")
        out.append(f"  SCORE value identical         : {score_match}")
        out.append(f"  SCORE-OVERALL identical       : {score_overall_match}")
        for k, mine_v, s4_v in score_diffs[:20]:
            out.append(f"   - {k}: mine={mine_v} step4={s4_v!r}")
        if not score_diffs and geo_keys:
            out.append("  >> PERFECT: every forward day's geo-adjusted SCORE matches Step 4.")

    # How many forward days actually have a non-neutral geo multiplier applied.
    notable_days = 0
    for k in geo_keys:
        if any(
            GEO_SIGNAL_MAP.get(_row_geo(pad(r, 9)), GEO_DEFAULT_MULTIPLIER) != 1.0
            for r in mine_matched.get(k, [])
        ):
            notable_days += 1
    out.append("")
    out.append(f"  Forward days with >=1 geo-weighted matched row: {notable_days}/{len(geo_keys)}")
    out.append("")

    # --- spotlight on the manually-verified historical row ---
    out.append("-" * 70)
    out.append(f"  SPOTLIGHT — historical DJIA row {spotlight_hist}")
    out.append("-" * 70)
    out.append(f"  Note: {spotlight_hist} is a HISTORICAL DJIA candidate row, not a")
    out.append(f"        forward day. Forward days run {cutoff.isoformat() if cutoff else '?'} "
               f"onward, so this row")
    out.append("        can only land in a *Monday* forward day's match set (DAY is a key).")
    if spot_in_db:
        out.append(f"  This row IS in the DJIA history (kept after cutoff). "
                   f"Base key = DAY={spot_bk[0]!r} QF1={spot_bk[1]!r} QF2={spot_bk[2]!r}")
    else:
        out.append("  This row is NOT in the usable DJIA history (dropped: future-dated, "
                   "unparseable date, or blank A/D/E) — so it can never match.")
    out.append(f"  Forward days that consider it a BASE candidate (same DAY+QF1+QF2): "
               f"{len(base_cand_fwds)}")
    if base_cand_fwds:
        out.append(f"    {base_cand_fwds}")
    out.append(f"  Forward days whose FINAL DJIA match KEEPS {spotlight_hist}: "
               f"{len(kept_with_spot)}")
    if kept_with_spot:
        out.append(f"    {kept_with_spot}")
    elif base_cand_fwds:
        out.append("    (it is a base candidate on those days but gets narrowed out "
                   "by the element stages)")
    out.append("")

    # --- detailed trace for the chosen forward day ---
    th = trace_header
    out.append("=" * 70)
    out.append(f"  DETAILED TRACE — forward day {th['day']} {th['date']}  {trace_note}")
    out.append("=" * 70)
    out.append(f"  Base key    : DAY={th['base'][0]!r} QF1={th['base'][1]!r} "
               f"QF2={th['base'][2]!r}")
    out.append(f"  Fwd elements: ELE-P-1={th['elem'][0]!r} ELE-P-2={th['elem'][1]!r} "
               f"ELE-P-3={th['elem'][2]!r} ELE-P-4={th['elem'][3]!r}")
    out.append("")
    out.append("  Narrowing steps:")
    for line in trace_lines:
        out.append("    " + line)
    out.append("")
    out.append(f"  Stages applied (depth): {th['depth']}")
    out.append(f"  Final kept rows: {len(th['matched'])}")
    for row in th["matched"]:
        d = parse_date(row[1])
        diso = d.isoformat() if d else str(row[1])
        mark = "   <== manually-verified row" if diso == spot_iso else ""
        out.append(
            f"    - {str(row[0]):<10} {diso:<12} "
            f"price={str(row[2]):<10} "
            f"F={norm(row[5])} G={norm(row[6])} H={norm(row[7])} I={norm(row[8])}{mark}"
        )
    # cross-check this day against step4 output
    s4 = sorted(step4_djia.get(th["key"], []))
    mine_k = mine.get(th["key"], [])
    out.append("")
    out.append(f"  Cross-check vs Step 4 for this day: "
               f"{'MATCH' if mine_k == s4 else 'DISCREPANCY'} "
               f"(mine={len(mine_k)}, step4={len(s4)})")
    out.append("=" * 70)

    # ============ GEOMANTIC FIGURE + QUADRANT TALLY (analysis-only) ============
    # For EVERY KEY-MATCH-DJIA history row, derive the geomantic figure (element
    # parity) and the Mazzaj quadrant, then tally price direction by combo.
    geo_rows = read_range(token, DATA_SEARCH_KEY_ID, f"{DJIA_TAB}!A2:I")

    def _blank_dir():
        return {"count": 0, "UP": 0, "DOWN": 0, "FLAT": 0}

    combo = {}        # (figure, quadrant) -> {count, UP, DOWN, FLAT}
    fig_only = {}     # figure -> {count, UP, DOWN, FLAT}
    geo_total = 0
    geo_skipped_price = 0
    geo_skipped_elem = 0
    for r in geo_rows:
        r = pad(r, 9)
        if not any(str(c).strip() for c in r):
            continue
        direction = _price_dir(r[2])  # C = DAILY PRICE
        if direction is None:
            geo_skipped_price += 1
            continue
        fire = _intensity(r[5])   # F = ELE-P-1 (FIRE)
        air = _intensity(r[6])    # G = ELE-P-2 (AIR)
        water = _intensity(r[7])  # H = ELE-P-3 (WATER)
        earth = _intensity(r[8])  # I = ELE-P-4 (EARTH)
        cold_num = _intensity(r[3])  # D = QULITY-FIN-1 number
        passive = _qf_label(r[4])    # E = QULITY-FIN-2 label (DRY/MOIST/...)
        if None in (fire, air, water, earth, cold_num):
            geo_skipped_elem += 1
            continue

        figure = figure_from_elements(fire, air, water, earth)
        quadrant = mazzaj_quadrant(cold_num, passive)

        c = combo.setdefault((figure, quadrant), _blank_dir())
        c["count"] += 1
        c[direction] += 1
        f = fig_only.setdefault(figure, _blank_dir())
        f["count"] += 1
        f[direction] += 1
        geo_total += 1

    def pct(part, total):
        return (part / total * 100.0) if total else 0.0

    out.append("")
    out.append("=" * 78)
    out.append("  GEOMANTIC FIGURE + QUADRANT TALLY — all KEY-MATCH-DJIA history rows")
    out.append("=" * 78)
    out.append(f"  Rows tallied: {geo_total}   (skipped — unparseable price: "
               f"{geo_skipped_price}, incomplete elements/quality: {geo_skipped_elem})")
    out.append("  Figure = element parity (odd=1/even=0) of FIRE,AIR,WATER,EARTH.")
    out.append("  Quadrant = Mazzaj (cold>=4 vs <4) x (DRY vs MOIST/NEUTRAL).")
    out.append("")

    # ---- Table 1: figure-only (all 16 figures, aggregated across quadrants) ----
    out.append("  TABLE 1 — FIGURE-ONLY TALLY (aggregated across all quadrants)")
    out.append("  " + "-" * 70)
    out.append(f"  {'FIGURE':<16}{'TOTAL':>7}{'UP':>7}{'DOWN':>7}{'FLAT':>7}{'UP%':>8}{'DOWN%':>8}")
    out.append("  " + "-" * 70)
    for figure in GEOMANCY_FIGURES.values():
        d = fig_only.get(figure, _blank_dir())
        c = d["count"]
        out.append(
            f"  {figure:<16}{c:>7}{d['UP']:>7}{d['DOWN']:>7}{d['FLAT']:>7}"
            f"{pct(d['UP'], c):>7.1f}%{pct(d['DOWN'], c):>7.1f}%"
        )
    out.append("  " + "-" * 70)
    out.append("")

    # ---- Table 2: figure+quadrant (>= 50 rows), sorted by UP% desc ----
    MIN_COMBO_ROWS = 50
    out.append(f"  TABLE 2 — FIGURE + QUADRANT TALLY (only combos with >= {MIN_COMBO_ROWS} rows, sorted by UP% desc)")
    out.append("  " + "-" * 82)
    out.append(f"  {'FIGURE':<16}{'QUADRANT':<13}{'TOTAL':>7}{'UP':>6}{'DOWN':>6}{'FLAT':>6}{'UP%':>8}{'DOWN%':>8}")
    out.append("  " + "-" * 82)
    rows2 = [(figq, d) for figq, d in combo.items() if d["count"] >= MIN_COMBO_ROWS]
    rows2.sort(key=lambda kv: pct(kv[1]["UP"], kv[1]["count"]), reverse=True)
    for (figure, quadrant), d in rows2:
        c = d["count"]
        out.append(
            f"  {figure:<16}{quadrant:<13}{c:>7}{d['UP']:>6}{d['DOWN']:>6}{d['FLAT']:>6}"
            f"{pct(d['UP'], c):>7.1f}%{pct(d['DOWN'], c):>7.1f}%"
        )
    if not rows2:
        out.append(f"  (no combo reached {MIN_COMBO_ROWS} rows)")
    out.append("  " + "-" * 82)
    out.append("")

    # ---- Notable signals: UP%>55 (bullish) or DOWN%>55 (bearish), >= 100 rows ----
    NOTABLE_MIN_ROWS = 100
    NOTABLE_PCT = 55.0
    out.append(f"  NOTABLE SIGNALS — combos with >= {NOTABLE_MIN_ROWS} rows and UP% > {NOTABLE_PCT:.0f}% "
               f"or DOWN% > {NOTABLE_PCT:.0f}%")
    out.append("  " + "-" * 74)
    notable = []
    for (figure, quadrant), d in combo.items():
        c = d["count"]
        if c < NOTABLE_MIN_ROWS:
            continue
        up_p = pct(d["UP"], c)
        dn_p = pct(d["DOWN"], c)
        if up_p > NOTABLE_PCT:
            notable.append((up_p, "BULLISH", figure, quadrant, c, up_p, dn_p))
        elif dn_p > NOTABLE_PCT:
            notable.append((dn_p, "BEARISH", figure, quadrant, c, up_p, dn_p))
    notable.sort(key=lambda t: t[0], reverse=True)
    if notable:
        for _, tag, figure, quadrant, c, up_p, dn_p in notable:
            out.append(f"  [{tag}] {figure} / {quadrant}: n={c}  UP%={up_p:.1f}  DOWN%={dn_p:.1f}")
    else:
        out.append(f"  (none — no combo with >= {NOTABLE_MIN_ROWS} rows exceeded "
                   f"{NOTABLE_PCT:.0f}% in either direction)")
    out.append("  " + "-" * 74)
    out.append("=" * 78)

    print("\n".join(out))


if __name__ == "__main__":
    main()
