#!/usr/bin/env python3
"""
Live ESPN Tennis (ATP & WTA) Score Sync for TENNIS-SIGNAL-DASHBORD & TENNIS-FUSION-SIGNAL.
100% isolated from NBA/NHL endpoints and Google Sheets (TENNIS_SHEETS_WRITE_ENABLED=0).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone


def clean_name(raw: str) -> str:
    s = unicodedata.normalize("NFKD", str(raw or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip()


def fetch_espn_tennis_date(tour: str, d_iso: str) -> dict[tuple[str, str], tuple[str, int, int, str]]:
    ds = d_iso.replace("-", "")
    tlc = tour.lower()
    want_slug = "mens-singles" if tlc == "atp" else "womens-singles"
    url = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tlc}/scoreboard?dates={ds}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=12).read().decode("utf-8"))
    finals: dict[tuple[str, str], tuple[str, int, int, str]] = {}
    for ev in data.get("events", []):
        for grp in ev.get("groupings", []):
            if ((grp.get("grouping") or {}).get("slug") or "") != want_slug:
                continue
            for comp in grp.get("competitions", []):
                if str(comp.get("date") or "")[:10] != d_iso:
                    continue
                if not ((comp.get("status") or {}).get("type") or {}).get("completed"):
                    continue
                cs = comp.get("competitors") or []
                if len(cs) != 2:
                    continue
                w_c = next((x for x in cs if x.get("winner") is True), None)
                l_c = next((x for x in cs if x is not w_c), None)
                if not w_c or not l_c:
                    continue
                wn = clean_name(((w_c.get("athlete") or {}).get("displayName")) or "")
                ln = clean_name(((l_c.get("athlete") or {}).get("displayName")) or "")
                w_ls = [int(round(float(s.get("value", 0)))) for s in (w_c.get("linescores") or []) if s.get("value") is not None]
                l_ls = [int(round(float(s.get("value", 0)))) for s in (l_c.get("linescores") or []) if s.get("value") is not None]
                if not wn or not ln or not w_ls or not l_ls:
                    continue
                sc_str = " ".join(f"{wg}-{lg}" for wg, lg in zip(w_ls, l_ls))
                finals[(wn.lower(), ln.lower())] = (wn, sum(w_ls), sum(l_ls), sc_str)
                finals[(ln.lower(), wn.lower())] = (wn, sum(w_ls), sum(l_ls), sc_str)
    return finals


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-date", default="")
    ap.add_argument("--end-date", default="")
    ap.add_argument("--target-date", default="")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    pub_candidates = [
        os.path.abspath(os.path.join(here, "..", "..", "calc-dashboard", "public")),
        "/home/runner/workspace/artifacts/calc-dashboard/public",
    ]
    pub_dir = next((p for p in pub_candidates if os.path.isdir(p)), pub_candidates[0])

    today_iso = datetime.now(timezone.utc).date().isoformat()
    target_d = args.target_date if len(args.target_date) == 10 else today_iso
    dates_to_check = sorted({target_d, today_iso})

    finals_by_tour: dict[str, dict[tuple[str, str], tuple[str, int, int, str]]] = {"ATP": {}, "WTA": {}}
    for tour in ("ATP", "WTA"):
        for d_iso in dates_to_check:
            try:
                finals_by_tour[tour].update(fetch_espn_tennis_date(tour, d_iso))
            except Exception:
                continue

    updated_scores = 0
    total_done = 0
    pack_files = sorted(glob.glob(os.path.join(pub_dir, "fusion_*_opt*.json")) + glob.glob(os.path.join(pub_dir, "tennis_dashbord_*_opt*.json")))
    for pf in pack_files:
        doc = json.load(open(pf, "r", encoding="utf-8"))
        games = doc.get("games") or []
        changed = False
        for g in games:
            tour = str(g.get("tour") or "ATP").upper()
            key = (str(g.get("h") or "").lower(), str(g.get("a") or "").lower())
            hit = finals_by_tour.get(tour, {}).get(key)
            if hit and not g.get("done"):
                wn, wg, lg, sc_s = hit
                hp = wg if wn == g["h"] else lg
                ap_g = lg if wn == g["h"] else wg
                g["hp"], g["ap"] = hp, ap_g
                g["aw"] = wn
                g["sc"] = f"{sc_s} ({hp}-{ap_g})"
                g["done"] = True
                g["hw"] = bool(wn == g["h"])
                g["st"] = "WIN" if g.get("sys_win") == wn else "LOSS"
                if g.get("f1_wtp"):
                    g["fst"] = g["st"]
                changed = True
                updated_scores += 1
            if g.get("done"):
                total_done += 1
        if changed:
            json.dump(doc, open(pf, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    payload = {
        "ok": True,
        "updatedScores": updated_scores,
        "checkedDates": dates_to_check,
        "sheetSynced": False,
        "totalDone": total_done,
        "oosF1": {"w": 0, "n": 0, "pct": 0.0},
        "s2627": {"w": 0, "n": 0, "pct": 0.0},
    }
    print("__NBA_SYNC__ " + json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
