"""READ-ONLY diagnostic for the QULITY-FIN-2 bug on forward days.

Reads the raw SEARCH-SIGNALS source row for a target forward date and prints
every column it reads (A:I), the parsed QF1/QF2 values, and exactly what step4
would write into the yellow SEARCH-KEY row of FINAL-SIGNAL.

No writes, no formatting — pure reads.
"""
import os
import re
import sys
import json

import requests
import google.auth.transport.requests
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SEARCH_SIGNALS_ID = os.environ.get("TENNIS_SEARCH_SIGNALS_SHEET_ID", "")

TARGET = sys.argv[1] if len(sys.argv) > 1 else "6/6/2026"


def mint_token():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var is not set.")
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def parse_quality(c):
    m = re.match(r"(-?\d+)\s+([A-Za-z]+)", str(c).strip())
    return (int(m.group(1)), m.group(2).upper()) if m else None


def norm_date(s):
    return str(s).strip()


COL = ["A=DAY", "B=DATE", "C=PRICE", "D=QULITY-FIN-1", "E=QULITY-FIN-2",
       "F=ELE-P-1/FIRE", "G=ELE-P-2/AIR", "H=ELE-P-3/WATER", "I=ELE-P-4/EARTH"]


def fetch(token, rng, render):
    u = (f"https://sheets.googleapis.com/v4/spreadsheets/{SEARCH_SIGNALS_ID}"
         f"/values/{rng}?valueRenderOption={render}")
    x = requests.get(u, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    x.raise_for_status()
    return x.json().get("values", [])


def main():
    token = mint_token()
    print(f"=== SEARCH-SIGNALS source diagnostic for forward day {TARGET} ===\n")

    # step4 reads with the DEFAULT render option (FORMATTED_VALUE). We also fetch
    # UNFORMATTED + FORMULA so we can see whether QF2 is a formula or a number
    # whose displayed text differs from its stored value.
    fmt = fetch(token, "Sheet1!A2:I", "FORMATTED_VALUE")
    unf = fetch(token, "Sheet1!A2:I", "UNFORMATTED_VALUE")
    formula = fetch(token, "Sheet1!A2:I", "FORMULA")

    def pad(r):
        return (list(r) + [""] * 9)[:9]

    found = False
    for idx, row in enumerate(fmt):
        r = pad(row)
        if norm_date(r[1]) == TARGET:
            found = True
            sheet_row = idx + 2  # A2 offset
            ur = pad(unf[idx]) if idx < len(unf) else [""] * 9
            fr = pad(formula[idx]) if idx < len(formula) else [""] * 9

            print(f"Matched at sheet row {sheet_row} (Sheet1!A{sheet_row}:I{sheet_row})\n")
            print("Per-column read (what step4's read_sheet returns = FORMATTED_VALUE):")
            for i in range(9):
                print(f"  {COL[i]:<18} FORMATTED={r[i]!r:<14} "
                      f"UNFORMATTED={ur[i]!r:<14} FORMULA={fr[i]!r}")

            print()
            qf1_raw, qf2_raw = r[3], r[4]
            print(f"  step4 sets qf1 = row[3] = {qf1_raw!r}")
            print(f"  step4 sets qf2 = row[4] = {qf2_raw!r}")
            print(f"  parse_quality(qf1) = {parse_quality(qf1_raw)}")
            print(f"  parse_quality(qf2) = {parse_quality(qf2_raw)}")

            print("\n  --> SEARCH-KEY row would write (cols E,F = qf1,qf2):")
            print(f"        E (QULITY-FIN-1) = {qf1_raw!r}")
            print(f"        F (QULITY-FIN-2) = {qf2_raw!r}")
            print(f"        G..J ELE-P-1..4  = {r[5]!r}, {r[6]!r}, {r[7]!r}, {r[8]!r}")
            break

    if not found:
        print(f"!! No row with DATE == {TARGET!r} found in SEARCH-SIGNALS A2:I.")
        print("   First 5 dates present (col B):")
        for row in fmt[:5]:
            print(f"     {pad(row)[1]!r}")


if __name__ == "__main__":
    main()
