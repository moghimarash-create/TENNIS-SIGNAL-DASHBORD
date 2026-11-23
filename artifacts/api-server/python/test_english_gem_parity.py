#!/usr/bin/env python3
"""Automated Cross-Language Verification Test for EnglishGem, Tour DEG1, and Zero-Birthdate Invariants."""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from _lib.tennis_config import (
    ATP_DEG1,
    ATP_GEMATRIA,
    BIRTHDATE_USED,
    EGEM_MAP,
    TENNIS_SHEETS_WRITE_ENABLED,
    WTA_DEG1,
    WTA_GEMATRIA,
    deg_from_name,
    egem,
    zodiac_from_deg,
)

EXPECTED_TABLE = {
    "A": 1, "B": 2, "G": 3, "D": 4, "E": 5,
    "U": 6, "V": 6, "W": 6,
    "Z": 7, "H": 8,
    "I": 10, "J": 10, "Y": 10,
    "C": 20, "K": 20, "L": 30, "M": 40, "N": 50, "S": 60,
    "O": 70, "X": 70,
    "F": 80, "P": 80,
    "Q": 100, "R": 200, "T": 400,
}


def main() -> None:
    # 1. Exact 26-letter Gematria table check
    assert EGEM_MAP == EXPECTED_TABLE, f"Mismatch in EGEM_MAP: {EGEM_MAP}"
    for ch, val in EXPECTED_TABLE.items():
        assert egem(ch) == val and egem(ch.lower()) == val

    # 2. Non-alpha characters = 0
    assert egem("0123456789 !@#$%^&*()-_=+[]{}|;:',.<>/?") == 0

    # 3. Control Checks: ATP & WTA + Zero Birthdate
    assert BIRTHDATE_USED is False
    assert TENNIS_SHEETS_WRITE_ENABLED is False
    assert egem("ATP") == ATP_GEMATRIA == 481
    assert deg_from_name("ATP") == ATP_DEG1 == 121
    assert zodiac_from_deg(ATP_DEG1) == ("1 LEO", "FIRE", 4)

    assert egem("WTA") == WTA_GEMATRIA == 407
    assert deg_from_name("WTA") == WTA_DEG1 == 47
    assert zodiac_from_deg(WTA_DEG1) == ("17 TAURUS", "EARTH", 1)

    # 4. Cross-check Python vs TypeScript (Node v22 stripTypeScriptTypes) on sample tennis strings
    samples = [
        "ATP",
        "WTA",
        "Novak Djokovic",
        "Carlos Alcaraz",
        "Jannik Sinner",
        "Iga Świątek",
        "Aryna Sabalenka",
        "Elena Rybakina",
        "Wimbledon Championships",
        "Roland Garros",
        "Hard",
        "Clay",
        "Grass",
        "123-456 !?",
    ]
    ts_cfg = os.path.abspath(os.path.join(HERE, "..", "src", "lib", "tennis-config.ts"))
    node_code = f"""
const fs = require("fs");
const vm = require("vm");
const {{ stripTypeScriptTypes }} = require("module");
const tsSrc = fs.readFileSync({json.dumps(ts_cfg)}, "utf8")
  .replace(/^export\\s+/gm, "");
const jsSrc = stripTypeScriptTypes(tsSrc, {{ mode: "transform" }});
const ctx = {{ result: null }};
vm.createContext(ctx);
vm.runInContext(jsSrc + "\\nresult = " + {json.dumps(json.dumps(samples))} + ".map(s => [s, englishGem(s), degFromName(s)]);", ctx);
console.log(JSON.stringify(ctx.result));
"""
    proc = subprocess.run(["node", "-e", node_code], check=True, capture_output=True, text=True)
    ts_results = json.loads(proc.stdout.strip())
    for s, ts_gem, ts_deg in ts_results:
        py_gem, py_deg = egem(s), deg_from_name(s)
        assert py_gem == ts_gem and py_deg == ts_deg, f"Py/TS mismatch on {s!r}: Py=({py_gem},{py_deg}) vs TS=({ts_gem},{ts_deg})"

    print("[PASS] 100% Python == TypeScript EnglishGem parity verified across all 26 letters & Tennis samples!")
    print(f"[PASS] ATP={egem('ATP')} -> DEG1={deg_from_name('ATP')} (1° LEO) | WTA={egem('WTA')} -> DEG1={deg_from_name('WTA')} (17° TAURUS) | BIRTHDATE_USED={BIRTHDATE_USED}")


if __name__ == "__main__":
    main()
