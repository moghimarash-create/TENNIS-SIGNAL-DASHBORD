#!/usr/bin/env python3
"""accuracy_report.py — standalone accuracy comparison for Step 4 signals.

Reads two Google Sheets produced by step4_search_signals.py:
  - PREDICTION-FINAL : one row per forward date with the OLD count-based
    OVERALL_SIGNAL/OVERALL_CONF and the NEW match-depth SCORE_OVERALL/SCORE_CONF.
  - FINAL-SIGNAL     : the per-day detail; each forward date has a yellow
    "SEARCH-KEY" row whose col C = forward DATE and col D = actual BTC daily
    price/return (positive => actual UP, negative => actual DOWN).

For every forward date it lines up:
  1) ACTUAL direction  (sign of the SEARCH-KEY price)
  2) OLD prediction     (OVERALL_SIGNAL, count method)
  3) NEW prediction     (SCORE_OVERALL, match-depth method)

and prints:
  A) Old-method directional accuracy %, excluding NEUTRAL predictions
  B) New-method directional accuracy %, excluding NEUTRAL predictions
  C) NEUTRAL frequency for each method
  D) Accuracy bucketed by the method's reported confidence level

Auth: requires GOOGLE_SERVICE_ACCOUNT_JSON (full service-account key JSON) in
the environment, the same secret Step 4 uses. The service account must have at
least read access to both spreadsheets.

Run:  python3 accuracy_report.py
"""

import json
import os
import re
import sys

import requests
import google.auth.transport.requests
from google.oauth2.service_account import Credentials

# Spreadsheet IDs (match steps-config.ts / step4_search_signals.py).
PREDICTION_FINAL_ID = os.environ.get("TENNIS_PREDICTION_FINAL_SHEET_ID", "")
FINAL_SIGNAL_ID = os.environ.get("TENNIS_FINAL_SIGNAL_SHEET_ID", "")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

CONF_BUCKETS = [
    (0.0, 50.0, "[ 0-50%)"),
    (50.0, 60.0, "[50-60%)"),
    (60.0, 70.0, "[60-70%)"),
    (70.0, 80.0, "[70-80%)"),
    (80.0, 90.0, "[80-90%)"),
    (90.0, 100.01, "[90-100%]"),
]


def get_token():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        sys.exit("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON is not set in the environment.")
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def read_range(token, sheet_id, a1_range):
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
        f"/values/{a1_range}"
    )
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    resp.raise_for_status()
    return resp.json().get("values", [])


def to_float(s):
    """Parse a possibly messy numeric string; return float or None."""
    if s is None:
        return None
    t = str(s).strip().replace(",", "").replace("$", "").replace(" ", "")
    if t == "":
        return None
    m = re.search(r"[-+]?\d*\.?\d+", t)
    return float(m.group(0)) if m else None


def to_conf(s):
    """Parse '62%' -> 62.0; return float or None."""
    if s is None:
        return None
    t = str(s).replace("%", "").strip()
    try:
        return float(t)
    except ValueError:
        return None


def base_signal(s):
    """Strip the ' (NM)' no-match suffix; uppercase. -> UP/DOWN/NEUTRAL/''."""
    if s is None:
        return ""
    return str(s).replace("(NM)", "").strip().upper()


def actual_dir(price):
    if price is None:
        return None
    if price > 0:
        return "UP"
    if price < 0:
        return "DOWN"
    return "FLAT"


def pct(num, den):
    return (num / den * 100.0) if den else 0.0


def accuracy(records, pred_key):
    """Directional accuracy excluding NEUTRAL preds and FLAT/missing actuals."""
    correct = scored = 0
    for r in records:
        pred = r[pred_key]
        act = r["actual"]
        if pred not in ("UP", "DOWN"):
            continue
        if act not in ("UP", "DOWN"):
            continue
        scored += 1
        if pred == act:
            correct += 1
    return correct, scored, pct(correct, scored)


def neutral_freq(records, pred_key):
    total = len(records)
    neutral = sum(1 for r in records if r[pred_key] == "NEUTRAL")
    return neutral, total, pct(neutral, total)


def accuracy_by_confidence(records, pred_key, conf_key):
    """Return list of (label, correct, scored, acc%) per confidence bucket."""
    out = []
    for lo, hi, label in CONF_BUCKETS:
        correct = scored = 0
        for r in records:
            pred = r[pred_key]
            act = r["actual"]
            conf = r[conf_key]
            if pred not in ("UP", "DOWN") or act not in ("UP", "DOWN"):
                continue
            if conf is None or not (lo <= conf < hi):
                continue
            scored += 1
            if pred == act:
                correct += 1
        out.append((label, correct, scored, pct(correct, scored)))
    return out


def build_actual_map(token):
    """date(str) -> actual price(float) from FINAL-SIGNAL SEARCH-KEY rows (B='SEARCH-KEY')."""
    rows = read_range(token, FINAL_SIGNAL_ID, "Sheet1!A:D")
    actual = {}
    for row in rows:
        row = (list(row) + ["", "", "", ""])[:4]
        if str(row[1]).strip().upper() == "SEARCH-KEY":
            date = str(row[2]).strip()
            price = to_float(row[3])
            if date:
                actual[date] = price
    return actual


def build_records(token):
    pf = read_range(token, PREDICTION_FINAL_ID, "Sheet1")
    if not pf:
        sys.exit("ERROR: PREDICTION-FINAL is empty.")
    header = [str(h).strip() for h in pf[0]]

    def col(name):
        try:
            return header.index(name)
        except ValueError:
            sys.exit(f"ERROR: PREDICTION-FINAL is missing column '{name}'. "
                     f"Header was: {header}")

    i_date = col("DATE")
    i_old = col("OVERALL_SIGNAL")
    i_oldc = col("OVERALL_CONF")
    i_new = col("SCORE_OVERALL")
    i_newc = col("SCORE_CONF")
    width = len(header)

    actual_price = build_actual_map(token)

    records = []
    flat = unmatched = blank = 0
    for row in pf[1:]:
        row = (list(row) + [""] * width)[:width]
        date = str(row[i_date]).strip()
        if not date:
            continue
        price = actual_price.get(date)
        if date not in actual_price:
            unmatched += 1
            act = None
        elif price is None:
            # SEARCH-KEY row exists but its price cell is blank -> the forward
            # date has not been realized yet (no actual BTC move to score).
            blank += 1
            act = None
        else:
            act = actual_dir(price)
            if act == "FLAT":
                flat += 1
        records.append({
            "date": date,
            "old": base_signal(row[i_old]),
            "old_conf": to_conf(row[i_oldc]),
            "new": base_signal(row[i_new]),
            "new_conf": to_conf(row[i_newc]),
            "price": price,
            "actual": act,
        })
    return records, flat, unmatched, blank


def fmt_bucket_table(rows):
    lines = []
    for label, correct, scored, acc in rows:
        if scored:
            lines.append(f"    {label}  acc {acc:5.1f}%   ({correct}/{scored})")
        else:
            lines.append(f"    {label}  acc    -      (0/0)")
    return "\n".join(lines)


def main():
    token = get_token()
    records, flat, unmatched, blank = build_records(token)

    total = len(records)
    actual_up = sum(1 for r in records if r["actual"] == "UP")
    actual_dn = sum(1 for r in records if r["actual"] == "DOWN")
    scorable = sum(1 for r in records if r["actual"] in ("UP", "DOWN"))

    old_correct, old_scored, old_acc = accuracy(records, "old")
    new_correct, new_scored, new_acc = accuracy(records, "new")
    old_n, _, old_nf = neutral_freq(records, "old")
    new_n, _, new_nf = neutral_freq(records, "new")
    old_buckets = accuracy_by_confidence(records, "old", "old_conf")
    new_buckets = accuracy_by_confidence(records, "new", "new_conf")

    L = []
    L.append("=" * 64)
    L.append("      BTC SIGNAL ACCURACY REPORT — Old vs. New (match-depth)")
    L.append("=" * 64)
    L.append(f"  PREDICTION-FINAL : {PREDICTION_FINAL_ID}")
    L.append(f"  FINAL-SIGNAL     : {FINAL_SIGNAL_ID}")
    L.append("")
    L.append(f"  Forward dates in PREDICTION-FINAL : {total}")
    L.append(f"  With a scorable actual (UP/DOWN)  : {scorable}")
    L.append(f"  Not yet realized (blank price)    : {blank}")
    L.append(f"  Actual FLAT (price == 0) excluded : {flat}")
    L.append(f"  No matching SEARCH-KEY row        : {unmatched}")
    L.append(f"  (check: {scorable}+{blank}+{flat}+{unmatched} = "
             f"{scorable + blank + flat + unmatched} of {total})")
    L.append(f"  Actual direction distribution     : UP={actual_up}  DOWN={actual_dn}")
    L.append("")
    L.append("-" * 64)
    L.append("  A) OLD METHOD  — OVERALL_SIGNAL (count of UP vs DOWN matches)")
    L.append("-" * 64)
    L.append(f"    Predictions: UP={sum(1 for r in records if r['old']=='UP')}  "
             f"DOWN={sum(1 for r in records if r['old']=='DOWN')}  "
             f"NEUTRAL={old_n}")
    L.append(f"    Scored (excl. NEUTRAL & flat): {old_scored}")
    L.append(f"    Correct={old_correct}  Wrong={old_scored - old_correct}")
    L.append(f"    >> ACCURACY: {old_acc:.1f}%")
    L.append("")
    L.append("-" * 64)
    L.append("  B) NEW METHOD  — SCORE_OVERALL (match-depth weighted score)")
    L.append("-" * 64)
    L.append(f"    Predictions: UP={sum(1 for r in records if r['new']=='UP')}  "
             f"DOWN={sum(1 for r in records if r['new']=='DOWN')}  "
             f"NEUTRAL={new_n}")
    L.append(f"    Scored (excl. NEUTRAL & flat): {new_scored}")
    L.append(f"    Correct={new_correct}  Wrong={new_scored - new_correct}")
    L.append(f"    >> ACCURACY: {new_acc:.1f}%")
    L.append("")
    L.append("-" * 64)
    L.append("  C) NEUTRAL FREQUENCY")
    L.append("-" * 64)
    L.append(f"    Old (OVERALL_SIGNAL): {old_n}/{total}  ({old_nf:.1f}%)")
    L.append(f"    New (SCORE_OVERALL) : {new_n}/{total}  ({new_nf:.1f}%)")
    L.append("")
    L.append("-" * 64)
    L.append("  D) ACCURACY BY CONFIDENCE LEVEL  (excl. NEUTRAL & flat)")
    L.append("-" * 64)
    L.append("  Old method (OVERALL_CONF):")
    L.append(fmt_bucket_table(old_buckets))
    L.append("  New method (SCORE_CONF):")
    L.append(fmt_bucket_table(new_buckets))
    L.append("")
    L.append("=" * 64)
    L.append("  HEAD-TO-HEAD")
    L.append("=" * 64)
    L.append(f"    Old: {old_acc:5.1f}%  (n={old_scored})")
    L.append(f"    New: {new_acc:5.1f}%  (n={new_scored})")
    if old_scored and new_scored:
        if new_acc > old_acc:
            winner = f"NEW method is more accurate by {new_acc - old_acc:.1f} pts"
        elif old_acc > new_acc:
            winner = f"OLD method is more accurate by {old_acc - new_acc:.1f} pts"
        else:
            winner = "Both methods tie on accuracy"
        L.append(f"    {winner}")
        L.append(f"    Coverage: old scored {old_scored}, new scored {new_scored} "
                 f"of {scorable} scorable days")
    L.append("=" * 64)

    print("\n".join(L))


if __name__ == "__main__":
    main()
