#!/usr/bin/env python3
"""
Master Zero-Lookahead Astro-Gematria Dual-Angle (T + P), 3-Option DEG3 & 16-Mode Fusion Pipeline
for ATP (DEG1=121, 1° LEO, FIRE) and WTA (DEG1=47, 17° TAURUS, EARTH) across 2024, 2025, and 2026
(warmed up strictly Zero-Lookahead on 2018-2023 ATP & WTA main-tour matches).

STRICT ARCHITECTURAL INVARIANTS:
- BIRTHDATE_USED = False (zero player birthdates or ages ever read or used).
- 100% exact EnglishGem mapping (ATP=481 -> 121, WTA=407 -> 47).
- 100% Zero-Lookahead (r.date < match.date) for Overall+Surface Elo, Player 1/2 ordering, and Twin Pools.
- 100% isolated from all NBA/NHL Google Sheets & state files.
"""
from __future__ import annotations

import bisect
import csv
import datetime
import glob
import json
import math
import os
import re
import shutil
import sys
import time
import unicodedata
from collections import defaultdict
from typing import Any

import pytz
import swisseph as swe

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from _lib.tennis_config import (
    ATP_DEG1,
    ATP_GEMATRIA,
    BIRTHDATE_USED,
    EGEM_MAP,
    WTA_DEG1,
    WTA_GEMATRIA,
    clean_ascii,
    egem,
)
from _lib.tennis_venues import resolve_tournament_geo
import fusion_player_eval as fpe

assert BIRTHDATE_USED is False
assert egem("ATP") == ATP_GEMATRIA == 481 and (ATP_GEMATRIA % 360) == ATP_DEG1 == 121
assert egem("WTA") == WTA_GEMATRIA == 407 and (WTA_GEMATRIA % 360) == WTA_DEG1 == 47

# Verify all 26 letters match exact user specification
_EXPECTED_GEM = {
    "A": 1, "B": 2, "G": 3, "D": 4, "E": 5,
    "U": 6, "V": 6, "W": 6,
    "Z": 7, "H": 8,
    "I": 10, "J": 10, "Y": 10,
    "C": 20, "K": 20, "L": 30, "M": 40, "N": 50, "S": 60,
    "O": 70, "X": 70,
    "F": 80, "P": 80,
    "Q": 100, "R": 200, "T": 400,
}
assert EGEM_MAP == _EXPECTED_GEM, f"EGEM_MAP mismatch: {EGEM_MAP}"
assert egem("123 !@# -_.") == 0

SIGNS_SHORT = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]

# Allowed ESPN WTA Main-Tour Event IDs (excludes WTA 125 Challenger events)
WTA_MAIN_TOUR_ESPN_IDS = {
    188, 189, 227, 232, 264, 306, 341, 345, 380, 381, 382, 401, 415, 421,
    444, 525, 635, 636, 718, 811, 866, 874, 887, 888, 889, 959, 963, 997,
    1002, 1005, 1009,
}

GREG_TO_SHAMSI_APPROX_MONTHS = [
    (1, 21, 10, "دی"), (2, 20, 11, "بهمن"), (3, 21, 12, "اسفند"),
    (4, 21, 1, "فروردین"), (5, 22, 2, "اردیبهشت"), (6, 22, 3, "خرداد"),
    (7, 23, 4, "تیر"), (8, 23, 5, "مرداد"), (9, 23, 6, "شهریور"),
    (10, 23, 7, "مهر"), (11, 22, 8, "آبان"), (12, 22, 9, "آذر"),
]


def shamsi_ym(d_iso: str) -> tuple[str, str]:
    y, m, d = map(int, d_iso.split("-"))
    gy_off = 621 if (m > 3 or (m == 3 and d >= 21)) else 622
    jy = y - gy_off
    jm_map = {
        1: (10 if d < 21 else 11), 2: (11 if d < 20 else 12), 3: (12 if d < 21 else 1),
        4: (1 if d < 21 else 2), 5: (2 if d < 22 else 3), 6: (3 if d < 22 else 4),
        7: (4 if d < 23 else 5), 8: (5 if d < 23 else 6), 9: (6 if d < 23 else 7),
        10: (7 if d < 23 else 8), 11: (8 if d < 22 else 9), 12: (9 if d < 22 else 10),
    }
    jm = jm_map[m]
    return f"{jy}-{jm:02d}", f"{jy}/{jm:02d}"


def norm_player_name(raw: str) -> str:
    s = clean_ascii(raw)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_first_last(full_name: str) -> tuple[str, str]:
    parts = [p for p in norm_player_name(full_name).split(" ") if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], " ".join(parts[1:])


def player_3code(full_name: str) -> str:
    _, last = split_first_last(full_name)
    letters = "".join(ch for ch in last.upper() if "A" <= ch <= "Z")
    if len(letters) >= 3:
        return letters[:3]
    all_l = "".join(ch for ch in norm_player_name(full_name).upper() if "A" <= ch <= "Z")
    return (all_l + "XXX")[:3]


def dec_label(deg: int) -> str:
    d = int(deg) % 360
    return f"{SIGNS_SHORT[d // 30]} D{(d % 30) // 10 + 1}"


def parse_sackmann_score(score_str: str) -> tuple[int, int] | None:
    s = str(score_str or "").strip()
    if not s:
        return None
    up = s.upper()
    if any(tok in up for tok in ("W/O", "DEF", "WALKOVER", "WEA", "UNP", "ABN")):
        return None
    w_g, l_g = 0, 0
    sets_parsed = 0
    for tok in s.split():
        m = re.match(r"^(\d+)-(\d+)", tok)
        if m:
            w_g += int(m.group(1))
            l_g += int(m.group(2))
            sets_parsed += 1
    if sets_parsed == 0:
        return None
    return w_g, l_g


def round_day_offset(draw_size: int, rnd: str, match_num: int) -> int:
    r = str(rnd or "").strip().upper()
    two_week = draw_size >= 96
    if two_week:
        mp = {
            "R128": 0 + (match_num % 2),
            "R64": 2 + (match_num % 2),
            "R32": 4 + (match_num % 2),
            "R16": 6 + (match_num % 2),
            "QF": 8 + (match_num % 2),
            "SF": 10 + (match_num % 2),
            "BR": 11,
            "F": 12,
            "RR": match_num % 5,
        }
        return mp.get(r, 2)
    mp = {
        "R64": 0,
        "R32": 1 + (match_num % 2),
        "R16": 2 + (match_num % 2),
        "QF": 4,
        "SF": 5,
        "BR": 5,
        "F": 6,
        "RR": match_num % 5,
    }
    return mp.get(r, 1)


def round_sort_order(rnd: str) -> int:
    r = str(rnd or "").strip().upper()
    mp = {
        "RR": 1, "R128": 1, "FIRST ROUND": 1, "1ST ROUND": 1, "ROUND OF 128": 1,
        "R64": 2, "SECOND ROUND": 2, "2ND ROUND": 2, "ROUND OF 64": 2,
        "R32": 3, "THIRD ROUND": 3, "3RD ROUND": 3, "ROUND OF 32": 3,
        "R16": 4, "FOURTH ROUND": 4, "4TH ROUND": 4, "ROUND OF 16": 4,
        "QF": 5, "QUARTERFINAL": 5, "QUARTERFINALS": 5,
        "SF": 6, "SEMIFINAL": 6, "SEMIFINALS": 6,
        "BR": 6,
        "F": 7, "FINAL": 7,
    }
    return mp.get(r, 3)


def normalize_espn_round(rnd_name: str) -> str:
    r = str(rnd_name or "").strip().upper()
    if "FINAL" in r and "SEMI" not in r and "QUARTER" not in r:
        return "F"
    if "SEMI" in r:
        return "SF"
    if "QUARTER" in r:
        return "QF"
    if "16" in r or "4TH" in r or "FOURTH" in r:
        return "R16"
    if "32" in r or "3RD" in r or "THIRD" in r:
        return "R32"
    if "64" in r or "2ND" in r or "SECOND" in r:
        return "R64"
    if "128" in r or "1ST" in r or "FIRST" in r:
        return "R128"
    if "ROBIN" in r:
        return "RR"
    return "R32"


def extract_flag_ioc(comp_obj: dict[str, Any], ioc_lookup: dict[str, str], pname: str) -> str:
    if pname in ioc_lookup:
        return ioc_lookup[pname]
    href = (((comp_obj.get("athlete") or {}).get("flag") or {}).get("href") or "").strip()
    m = re.search(r"/([a-z]{3})\.png", href.lower())
    if m:
        return m.group(1).upper()
    return "UNK"


def load_all_matches(raw_dir: str = "/tmp/tennis_raw") -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"ATP": [], "WTA": []}
    ioc_lookup: dict[str, str] = {}
    rank_lookup: dict[str, int] = {}

    for tour_lc in ("atp", "wta"):
        tour = tour_lc.upper()
        seen_keys: set[tuple[str, str, frozenset[str]]] = set()

        for csv_path in sorted(glob.glob(f"{raw_dir}/{tour_lc}/{tour_lc}_*.csv")):
            with open(csv_path, encoding="utf-8", errors="replace") as f:
                for row in csv.DictReader(f):
                    lvl = (row.get("tourney_level") or "").strip().upper()
                    tname_raw = (row.get("tourney_name") or "").strip()
                    if not tname_raw or lvl == "D":
                        continue
                    if any(bad in tname_raw for bad in ("Davis Cup", "Billie Jean", "BJK Cup", "Fed Cup", "W35", "W50", "W75", "W100", " 125", "Limoges")):
                        continue
                    tdate = str(row.get("tourney_date") or "").strip()
                    if len(tdate) != 8 or not tdate.isdigit():
                        continue
                    parsed_sc = parse_sackmann_score(row.get("score", ""))
                    if parsed_sc is None:
                        continue
                    w_name = norm_player_name(row.get("winner_name", ""))
                    l_name = norm_player_name(row.get("loser_name", ""))
                    if not w_name or not l_name or w_name == l_name:
                        continue

                    w_ioc = (row.get("winner_ioc") or "UNK").strip().upper() or "UNK"
                    l_ioc = (row.get("loser_ioc") or "UNK").strip().upper() or "UNK"
                    ioc_lookup[w_name] = w_ioc
                    ioc_lookup[l_name] = l_ioc

                    try:
                        w_rk = int(float(row.get("winner_rank") or 999))
                    except Exception:
                        w_rk = 999
                    try:
                        l_rk = int(float(row.get("loser_rank") or 999))
                    except Exception:
                        l_rk = 999
                    rank_lookup[w_name] = w_rk
                    rank_lookup[l_name] = l_rk

                    try:
                        draw_sz = int(float(row.get("draw_size") or 32))
                    except Exception:
                        draw_sz = 32
                    try:
                        m_num = int(float(row.get("match_num") or 1))
                    except Exception:
                        m_num = 1

                    base_dt = datetime.date(int(tdate[:4]), int(tdate[4:6]), int(tdate[6:8]))
                    rnd = (row.get("round") or "R32").strip().upper()
                    m_dt = base_dt + datetime.timedelta(days=round_day_offset(draw_sz, rnd, m_num))
                    # Clamp late-Dec start dates of Australian swing (e.g. 2024-12-27 United Cup) to their tour season year
                    season_yr = int(os.path.basename(csv_path).split("_")[1].split(".")[0])
                    d_iso = m_dt.isoformat()

                    geo = resolve_tournament_geo(tour, season_yr, tname_raw, row.get("surface", ""), "")
                    dedup_week = f"{season_yr}-{m_dt.isocalendar()[1]:02d}-{rnd}"
                    pair_key = (tour, dedup_week, frozenset((w_name.lower(), l_name.lower())))
                    if pair_key in seen_keys:
                        continue
                    seen_keys.add(pair_key)

                    out[tour].append({
                        "tour": tour,
                        "season": str(season_yr),
                        "d": d_iso,
                        "rnd": rnd,
                        "rnd_ord": round_sort_order(rnd),
                        "m_num": m_num,
                        "city": geo["city"],
                        "tourney": geo["tourney"],
                        "surface": geo["surface"],
                        "lat": geo["lat"],
                        "lon": geo["lon"],
                        "tz": geo["tz"],
                        "w_name": w_name,
                        "l_name": l_name,
                        "w_ioc": w_ioc,
                        "l_ioc": l_ioc,
                        "w_rk": w_rk,
                        "l_rk": l_rk,
                        "w_g": parsed_sc[0],
                        "l_g": parsed_sc[1],
                        "score_raw": str(row.get("score") or "").strip(),
                    })

        # Supplement late-2025 & May-Nov 2026 from ESPN Main-Tour scoreboard JSON
        espn_file = f"{raw_dir}/espn_{tour_lc}_25_26.json"
        if os.path.exists(espn_file):
            want_slug = "mens-singles" if tour == "ATP" else "womens-singles"
            evs = json.load(open(espn_file, encoding="utf-8"))
            for ev in evs:
                eid_str = str(ev.get("id") or "")
                num_id = int(eid_str.split("-")[0]) if eid_str.split("-")[0].isdigit() else 9999
                ename = str(ev.get("name") or "").strip()
                if any(bad in ename for bad in ("Davis Cup", "Billie Jean", "BJK", "Challenger", "125")):
                    continue
                if tour == "WTA" and num_id not in WTA_MAIN_TOUR_ESPN_IDS:
                    continue
                v_disp = ((ev.get("venue") or {}).get("displayName") or (ev.get("venue") or {}).get("fullName") or "").strip()
                for grp in ev.get("groupings", []):
                    if ((grp.get("grouping") or {}).get("slug") or "") != want_slug:
                        continue
                    for idx_c, comp in enumerate(grp.get("competitions", [])):
                        r_disp = ((comp.get("round") or {}).get("displayName") or "").strip()
                        if "qualif" in r_disp.lower():
                            continue
                        st_type = ((comp.get("status") or {}).get("type") or {})
                        if not st_type.get("completed"):
                            continue
                        st_desc = str(st_type.get("description") or "").upper()
                        if "WALKOVER" in st_desc:
                            continue
                        comps_arr = comp.get("competitors") or []
                        if len(comps_arr) != 2:
                            continue
                        w_c = next((x for x in comps_arr if x.get("winner") is True), None)
                        l_c = next((x for x in comps_arr if x is not w_c), None)
                        if not w_c or not l_c:
                            continue
                        w_name = norm_player_name(((w_c.get("athlete") or {}).get("displayName")) or "")
                        l_name = norm_player_name(((l_c.get("athlete") or {}).get("displayName")) or "")
                        if not w_name or not l_name or w_name == l_name or "TBD" in (w_name, l_name):
                            continue

                        w_ls = [int(round(float(s.get("value", 0)))) for s in (w_c.get("linescores") or []) if s.get("value") is not None]
                        l_ls = [int(round(float(s.get("value", 0)))) for s in (l_c.get("linescores") or []) if s.get("value") is not None]
                        if not w_ls or not l_ls or sum(w_ls) + sum(l_ls) == 0:
                            continue
                        sc_str = " ".join(f"{wg}-{lg}" for wg, lg in zip(w_ls, l_ls))

                        d_iso = str(comp.get("date") or ev.get("date") or "")[:10]
                        if len(d_iso) != 10 or d_iso < "2025-10-25":
                            continue
                        m_dt = datetime.date.fromisoformat(d_iso)
                        season_yr = m_dt.year
                        rnd = normalize_espn_round(r_disp)
                        # Check nearby weeks too so Sackmann Monday-offset vs ESPN exact date never duplicates!
                        iso_wk = m_dt.isocalendar()[1]
                        pair_set = frozenset((w_name.lower(), l_name.lower()))
                        if any((tour, f"{season_yr}-{wk:02d}-{rnd}", pair_set) in seen_keys for wk in (iso_wk - 1, iso_wk, iso_wk + 1)):
                            continue
                        seen_keys.add((tour, f"{season_yr}-{iso_wk:02d}-{rnd}", pair_set))

                        geo = resolve_tournament_geo(tour, season_yr, ename, "", v_disp)
                        w_ioc = extract_flag_ioc(w_c, ioc_lookup, w_name)
                        l_ioc = extract_flag_ioc(l_c, ioc_lookup, l_name)
                        ioc_lookup[w_name] = w_ioc
                        ioc_lookup[l_name] = l_ioc
                        w_rk = int(w_c.get("curatedRank", {}).get("current") or rank_lookup.get(w_name, 999) or 999)
                        l_rk = int(l_c.get("curatedRank", {}).get("current") or rank_lookup.get(l_name, 999) or 999)

                        out[tour].append({
                            "tour": tour,
                            "season": str(season_yr),
                            "d": d_iso,
                            "rnd": rnd,
                            "rnd_ord": round_sort_order(rnd),
                            "m_num": idx_c + 1,
                            "city": geo["city"],
                            "tourney": geo["tourney"],
                            "surface": geo["surface"],
                            "lat": geo["lat"],
                            "lon": geo["lon"],
                            "tz": geo["tz"],
                            "w_name": w_name,
                            "l_name": l_name,
                            "w_ioc": w_ioc,
                            "l_ioc": l_ioc,
                            "w_rk": w_rk if w_rk > 0 else 999,
                            "l_rk": l_rk if l_rk > 0 else 999,
                            "w_g": sum(w_ls),
                            "l_g": sum(l_ls),
                            "score_raw": sc_str,
                        })

        out[tour].sort(key=lambda x: (x["d"], x["tourney"], x["rnd_ord"], x["m_num"]))
    return out


# ---------------------------------------------------------------------------
# FAST SWISS EPHEMERIS TABLE CACHE & ASTRO-GEMATRIA HELPERS
# ---------------------------------------------------------------------------
_p_cache: dict[float, list[tuple[str, float]]] = {}
_d_cache: dict[tuple[float, int], int] = {}


class LazyTbl:
    def __init__(self, jd: float):
        self.jd = jd
        self.rk = round(jd, 4)

    def __getitem__(self, deg: int) -> int:
        p_degs = _p_cache.get(self.rk)
        if p_degs is None:
            p_degs = [(pn, swe.calc_ut(self.jd, pid, fpe.FLAGS)[0][0] % 360.0) for pn, pid in fpe.PLANETS_10]
            _p_cache[self.rk] = p_degs
        d_mod = int(deg) % 360
        ck = (self.rk, d_mod)
        v = _d_cache.get(ck)
        if v is not None:
            return v
        tot = 0
        fd = float(d_mod)
        for pn, pd in p_degs:
            sym = fpe.s2._best_aspect(fd, pd, pn)
            if sym is not None:
                val = fpe.s3.zod_aspect_deg(sym)
                if isinstance(val, (int, float)):
                    tot += int(val)
        _d_cache[ck] = tot
        return tot


_fawe_cache: dict[str, tuple[int, int, int, int]] = {}


def cached_fawe(name: str) -> tuple[int, int, int, int]:
    v = _fawe_cache.get(name)
    if v is None:
        v = tuple(fpe.s4.word_element_fawe(name))
        _fawe_cache[name] = v
    return v


def geo_code_from_ef(ef: tuple[int, int, int, int]) -> str:
    return "".join("1" if abs(x) % 2 == 1 else "0" for x in ef)


def calc_gf_fin(ef: tuple[int, int, int, int], gf_code: str) -> float:
    wts = (8, 4, 2, 1)
    acc = 0
    for i in range(4):
        b = 1 if gf_code[i] == "1" else 0
        acc += wts[i] * (2 * b - 1) * ef[i]
    return round(acc) / 10.0


def calc_pwr(m_d: dict[str, Any]) -> float:
    return round(
        0.35 * (m_d["qfin"][0] + m_d["qfin"][1])
        + 0.35 * (m_d["qdecf"][0] + m_d["qdecf"][1])
        + 0.15 * (m_d["gd"][0] + m_d["gd"][1])
        + 0.15 * (m_d["rul"][0] + m_d["rul"][1]),
        1,
    )


def fmt_qual_pair(pair: tuple[int, int], hc_mode: bool = True) -> str:
    hc, md = pair
    s1 = f"{abs(hc)} {'HOT' if hc >= 0 else 'COLD'}"
    s2 = f"{abs(md)} {'MOIST' if md >= 0 else 'DRY'}"
    return f"{s1} / {s2}"


def player_elem(p_str: float) -> str:
    if p_str >= 0.62:
        return "FIRE"
    if p_str >= 0.52:
        return "AIR"
    if p_str >= 0.44:
        return "WATER"
    return "EARTH"


def matchup_elem(l5_pick_pct: float) -> str:
    if l5_pick_pct >= 64.0:
        return "FIRE"
    if l5_pick_pct >= 54.0:
        return "AIR"
    if l5_pick_pct >= 45.0:
        return "WATER"
    return "EARTH"


def pool_idx_tennis(pool: list[dict[str, Any]]) -> tuple[int, int, int]:
    ch = [min(5, max(1, math.ceil(abs(x["mg"]) / 2))) for x in pool if x["mg"] > 0]
    ca = [min(5, max(1, math.ceil(abs(x["mg"]) / 2))) for x in pool if x["mg"] < 0]
    hw, aw = len(ch), len(ca)
    ih = 0 if not ch else (ch[0] if hw == 1 else max(ch) + min(ch))
    ia = 0 if not ca else (ca[0] if aw == 1 else max(ca) + min(ca))
    d = ih - ia
    s_delta = (2 * hw + ih) - (2 * aw + ia)
    if d > 0 and s_delta > 0:
        eff = d
    elif d < 0 and s_delta < 0:
        eff = d
    elif d == 0 and abs(s_delta) >= 2:
        eff = 1 if s_delta > 0 else -1
    else:
        eff = 0
    return hw, aw, eff


import numpy as np

_STR_ID_MAP: dict[str, int] = {}


def _sid(s: str) -> int:
    v = _STR_ID_MAP.get(s)
    if v is None:
        v = len(_STR_ID_MAP) + 1
        _STR_ID_MAP[s] = v
    return v


class FastDayPool:
    """Append-only day pool backed by contiguous numpy arrays for 40x faster exact twin filtering."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._h12_list: list[tuple[int, ...]] = []
        self._fin_list: list[int] = []
        self._dyn_list: list[int] = []
        self._tab_list: list[int] = []
        self._dirty = True
        self.h12_np = np.empty((0, 12), dtype=np.int16)
        self.fin_np = np.empty((0,), dtype=np.int16)
        self.dyn_np = np.empty((0,), dtype=np.int16)
        self.tab_np = np.empty((0,), dtype=np.int16)

    def __len__(self) -> int:
        return len(self.rows)

    def append(self, row: dict[str, Any]) -> None:
        self.rows.append(row)
        self._h12_list.append(tuple(_sid(x) for x in row["h12"]))
        self._fin_list.append(_sid(row["h_fin"]))
        self._dyn_list.append(_sid(row["h_dyn"]))
        self._tab_list.append(_sid(row["h_tab"]))
        self._dirty = True

    def sync(self) -> None:
        if self._dirty and self.rows:
            self.h12_np = np.asarray(self._h12_list, dtype=np.int16)
            self.fin_np = np.asarray(self._fin_list, dtype=np.int16)
            self.dyn_np = np.asarray(self._dyn_list, dtype=np.int16)
            self.tab_np = np.asarray(self._tab_list, dtype=np.int16)
            self._dirty = False


def auto_filter_fast(
    t12: tuple[str, ...],
    tgeo: str,
    dpool: FastDayPool,
    geo_first: bool,
    gk: str,
    min_gf: int,
) -> dict[str, Any]:
    dpool.sync()
    n_tot = len(dpool.rows)
    g_arr = dpool.fin_np if gk == "h_fin" else (dpool.tab_np if gk == "h_tab" else dpool.dyn_np)
    tgeo_id = _sid(tgeo) if tgeo else -1
    tv_np = np.asarray([_sid(x) for x in t12], dtype=np.int16)

    used_geo = False
    if geo_first and tgeo_id > 0:
        idx = np.flatnonzero(g_arr == tgeo_id)
        if len(idx) >= min_gf:
            used_geo = True
        else:
            idx = np.arange(n_tot, dtype=np.int32)
    else:
        idx = np.arange(n_tot, dtype=np.int32)

    used_mask = np.zeros(12, dtype=bool)
    while len(idx) > 7:
        eq = dpool.h12_np[idx] == tv_np
        cnts = eq.sum(axis=0)
        valid = (~used_mask) & (cnts >= 5) & (cnts < len(idx))
        if not valid.any():
            break
        masked_cnts = np.where(valid, cnts, -1)
        bc = int(np.argmax(masked_cnts))
        used_mask[bc] = True
        idx = idx[eq[:, bc]]
        if 5 <= len(idx) <= 7:
            break

    if (not geo_first) and (not used_geo) and tgeo_id > 0 and len(idx) > 7:
        sub_g = idx[g_arr[idx] == tgeo_id]
        if 5 <= len(sub_g) <= 7:
            idx = sub_g

    nat = 5 <= len(idx) <= 7
    if len(idx) > 7:
        idx = idx[-7:]
    pool = [dpool.rows[int(i)] for i in idx]
    hw, aw, eff = pool_idx_tennis(pool)
    tot = max(1, hw + aw)
    pct = round(max(hw, aw) * 100.0 / tot, 1)
    return {"pool": pool, "hw": hw, "aw": aw, "pct": pct, "mv": abs(hw - aw), "nat": nat, "ds": eff}


def eval_pillar_signal(
    h: str,
    a: str,
    h12: tuple[str, ...],
    h_fin: str,
    h_dyn: str,
    h_tab: str,
    f30: int,
    dpool: list[dict[str, Any]],
    mel: str,
) -> dict[str, Any]:
    if len(dpool) < 5:
        hfav = f30 >= 0
        pred = h if hfav else a
        return {
            "pick": pred, "twVotes": "0H-0A", "twPct": "50%", "f30": f30,
            "idx3": {"st": [0, 0, 0], "gf": [0, 0, 0], "gd": [0, 0, 0], "gt": [0, 0, 0], "tw": [0, 0, 0], "vh": 0, "va": 0, "nat": 0, "minD": 0},
            "f1": False, "f1_idx": False, "f1_guard": False, "f1_wtp": False, "vip_idx3": False, "nat": False,
            "twins": [],
        }

    sd = auto_filter_fast(h12, h_dyn, dpool, False, "h_dyn", 3)
    gd3 = auto_filter_fast(h12, h_dyn, dpool, True, "h_dyn", 3)
    sa = (sd["hw"] >= sd["aw"]) == (f30 >= 0)
    ga = (gd3["hw"] >= gd3["aw"]) == (f30 >= 0)
    pick_geo = (
        False if (sd["pct"] < 60 or (sa and not ga and sd["pct"] >= 55))
        else True if (not sa and ga and gd3["pct"] >= 55)
        else (gd3["pct"] > sd["pct"] or (gd3["pct"] == sd["pct"] and gd3["mv"] > sd["mv"]))
    )
    ch = gd3 if pick_geo else sd
    hw, aw_v, nat = ch["hw"], ch["aw"], ch["nat"]
    tot = hw + aw_v
    pct_int = round(max(hw, aw_v) * 100 / tot) if tot else 50
    hfav = True if hw > aw_v else (False if aw_v > hw else f30 >= 0)
    sgn = 1 if hfav else -1
    pred = h if hfav else a
    f30_o = f30 * sgn
    agree = (hfav and f30 > 0) or (not hfav and f30 < 0)
    both100 = sd["pct"] == 100.0 and gd3["pct"] == 100.0 and ((sd["hw"] > 0) == (gd3["hw"] > 0))
    v71 = 5 <= tot <= 7 and pct_int >= 71 and abs(hw - aw_v) >= 3
    bcombo = v71 and (agree or both100)

    c1 = auto_filter_fast(h12, h_fin, dpool, False, "h_fin", 5)
    c2 = auto_filter_fast(h12, h_fin, dpool, True, "h_fin", 5)
    c3 = auto_filter_fast(h12, h_dyn, dpool, True, "h_dyn", 5)
    c4 = auto_filter_fast(h12, h_tab, dpool, True, "h_tab", 5)
    ds4 = [c1["ds"], c2["ds"], c3["ds"], c4["ds"]]
    ds4_o = [v * sgn for v in ds4]
    vh4 = sum(1 for v in ds4 if v > 0)
    va4 = sum(1 for v in ds4 if v < 0)
    fav_v4 = vh4 if hfav else va4
    opp_v4 = va4 if hfav else vh4
    fav_v3 = sum(1 for v in ds4_o[:3] if v > 0)
    opp_v3 = sum(1 for v in ds4_o[:3] if v < 0)
    min_o4 = min(ds4_o)
    c4_vote_opp = ((c4["hw"] - c4["aw"]) * sgn < 0)

    t1 = (not hfav) and (f30_o < 10 or (fav_v3 < 2 and fav_v4 < 3))
    t2 = (opp_v3 >= 2 and f30_o < 8) or (opp_v4 >= 2 and f30_o < 10)
    t4 = (not nat) and fav_v3 < 3 and fav_v4 < 3 and f30_o < 12
    t5 = (fav_v4 == 0) or (c4_vote_opp and f30_o < 12)

    f1_idx = bool(bcombo and fav_v4 >= 2)
    f1_guard = bool(bcombo and not (t1 or t2 or t4 or t5))
    f1_wtp = bool(f1_guard and mel != "EARTH")
    vip = bool(f1_wtp and (mel == "FIRE" or (nat and fav_v4 == 4 and min_o4 >= 2)))
    twins_compact = [[tw["d"], tw["hc"], tw["ac"], tw["hp"], tw["ap"], tw["mg"]] for tw in ch["pool"]]
    return {
        "pick": pred,
        "twVotes": f"{hw}H-{aw_v}A",
        "twPct": f"{pct_int}%",
        "f30": f30,
        "idx3": {
            "st": [c1["hw"], c1["aw"], c1["ds"]],
            "gf": [c2["hw"], c2["aw"], c2["ds"]],
            "gd": [c3["hw"], c3["aw"], c3["ds"]],
            "gt": [c4["hw"], c4["aw"], c4["ds"]],
            "tw": [hw, aw_v, ch["ds"]],
            "vh": vh4,
            "va": va4,
            "nat": int(nat),
            "minD": min_o4,
        },
        "f1": bool(bcombo),
        "f1_idx": f1_idx,
        "f1_guard": f1_guard,
        "f1_wtp": f1_wtp,
        "vip_idx3": vip,
        "nat": nat,
        "twins": twins_compact,
    }


def dominant_elem_info(vec: list[int] | tuple[int, ...]) -> tuple[str, int, bool]:
    names = ("FIRE", "AIR", "WATER", "EARTH")
    mx = max(vec) if vec else 0
    if mx <= 0:
        return "—", 0, True
    winners = [names[i] for i in range(4) if vec[i] == mx]
    if len(winners) == 1:
        return winners[0], mx, False
    return f"TIE({'+'.join(w[0] for w in winners)})", mx, True


def compute_16_fusion_modes(
    h: str,
    a: str,
    wtp: dict[str, Any],
    res_t: dict[str, Any],
    res_p: dict[str, Any],
    hp_facets: list[dict[str, Any]],
    ap_facets: list[dict[str, Any]],
    tm_ent_h: dict[str, Any],
    tm_ent_a: dict[str, Any],
    ep_tm_h: tuple[int, int, int, int],
    ep_tm_a: tuple[int, int, int, int],
    date_sum_4: tuple[int, int, int, int],
    qtot_h: int,
    qtot_a: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str, str, bool]:
    """Computes all 16 Astro-Gematria Fusion Modes (Mode 1..16) with 100% UI parity."""
    tpk = res_t["pick"]
    ppk = res_p["pick"]
    sgn_t = 1 if tpk == h else -1
    sgn_p = 1 if ppk == h else -1
    f30_t = int(res_t["f30"])
    f30_p = int(res_p["f30"])
    t_sig = bool(res_t["f1_wtp"])
    p_sig = bool(res_p["f1_wtp"])
    t_vip = bool(res_t["vip_idx3"])
    p_vip = bool(res_p["vip_idx3"])

    p_supports_t = (ppk == tpk) or (f30_p * sgn_t > 0)
    t_supports_p = (tpk == ppk) or (f30_t * sgn_p > 0)
    p_astro_t = (f30_p * sgn_t > 0)
    t_astro_p = (f30_t * sgn_p > 0)

    # Modes 1..4
    is_diamond = bool(t_sig and p_sig and tpk == ppk)
    is_vip_cross = bool((t_vip and p_supports_t and (not p_vip or tpk == ppk)) or (p_vip and t_supports_p and (not t_vip or tpk == ppk)))
    is_astro_lock = bool((t_sig and p_astro_t and (not p_sig or tpk == ppk)) or (p_sig and t_astro_p and (not t_sig or tpk == ppk)))
    is_dual_pillar = bool((t_sig and p_supports_t and (not p_sig or tpk == ppk)) or (p_sig and t_supports_p and (not t_sig or tpk == ppk)))
    is_vetoed = bool((t_sig or p_sig) and not is_dual_pillar)

    l5h = float(wtp["l5h"])
    h_l5 = round(l5h, 1)
    a_l5 = round(100.0 - l5h, 1)
    fav_elo = h if h_l5 >= a_l5 else a

    if is_diamond:
        base_pick, driver, tier_code, tier_fa = tpk, "BOTH", "DIAMOND", "سطح ۱: الماس (توافق هم‌زمان دو زاویه T ∩ P)"
    elif is_vip_cross:
        base_pick = tpk if (t_vip and p_supports_t) else ppk
        driver = "TEAM" if base_pick == tpk else "PLAYER"
        tier_code, tier_fa = "GOLD_VIP", "سطح ۲: طلایی (VIP با تأیید متقابل)"
    elif is_dual_pillar:
        base_pick = tpk if (t_sig and p_supports_t) else ppk
        driver = "TEAM" if base_pick == tpk else "PLAYER"
        tier_code, tier_fa = "SILVER_CORE", "سطح ۳: نقره‌ای (تأیید دو-ستونی T+P)"
    elif is_vetoed:
        base_pick = tpk if t_sig else ppk
        driver = "TEAM" if t_sig else "PLAYER"
        tier_code, tier_fa = "VETOED", "وتوی متقابل دو زاویه"
    else:
        base_pick = tpk if abs(f30_t) > abs(f30_p) else (ppk if abs(f30_p) > abs(f30_t) else fav_elo)
        driver = "TEAM" if base_pick == tpk else "PLAYER"
        tier_code, tier_fa = "NONE", "بدون سیگنال پایه"

    pk_vip = tpk if (t_vip and p_supports_t) else (ppk if (p_vip and t_supports_p) else base_pick)
    pk_ast = tpk if (t_sig and p_astro_t) else (ppk if (p_sig and t_astro_p) else base_pick)
    pk_dp = tpk if (t_sig and p_supports_t) else (ppk if (p_sig and t_supports_p) else base_pick)
    pk_dia = tpk if is_diamond else base_pick

    # 1xxx / 0xxx / 0011 / All / GF-FIN metrics from 6-facet Astro-Gematria profile
    h_1xxx = [p["pwr"] for p in hp_facets if p["gf"].startswith("1")]
    a_1xxx = [p["pwr"] for p in ap_facets if p["gf"].startswith("1")]
    h_0xxx = [p["pwr"] for p in hp_facets if p["gf"].startswith("0")]
    a_0xxx = [p["pwr"] for p in ap_facets if p["gf"].startswith("0")]
    h_0011 = [p["pwr"] for p in hp_facets if p["gf"] == "0011"]
    a_0011 = [p["pwr"] for p in ap_facets if p["gf"] == "0011"]

    h_sum = round(sum(h_1xxx), 1)
    a_sum = round(sum(a_1xxx), 1)
    h_0sum = round(sum(h_0xxx), 1)
    a_0sum = round(sum(a_0xxx), 1)
    h_0011_sum = round(sum(h_0011), 1)
    a_0011_sum = round(sum(a_0011), 1)
    h_all = round(sum(p["pwr"] for p in hp_facets), 1)
    a_all = round(sum(p["pwr"] for p in ap_facets), 1)
    h_gf = round(sum(p["gf_fin"] for p in hp_facets), 1)
    a_gf = round(sum(p["gf_fin"] for p in ap_facets), 1)
    h_s3 = round(h_sum + h_all + h_gf, 1)
    a_s3 = round(a_sum + a_all + a_gf, 1)

    g1_win = h if h_sum < a_sum else (a if a_sum < h_sum else "")
    cold0_win = h if h_0sum < a_0sum else (a if a_0sum < h_0sum else "")
    c0011_win = h if h_0011_sum < a_0011_sum else (a if a_0011_sum < h_0011_sum else "")
    all_win = h if h_all < a_all else (a if a_all < h_all else "")
    gf_win = h if h_gf < a_gf else (a if a_gf < h_gf else "")
    s3_win = h if h_s3 < a_s3 else (a if a_s3 < h_s3 else "")

    # Majority of 3 numeric channels: 1xxx, All, GF-FIN
    votes_h3 = int(g1_win == h) + int(all_win == h) + int(gf_win == h)
    votes_a3 = int(g1_win == a) + int(all_win == a) + int(gf_win == a)
    maj23_win = h if votes_h3 >= 2 else (a if votes_a3 >= 2 else (gf_win or fav_elo))
    triple3_win = h if votes_h3 == 3 else (a if votes_a3 == 3 else "")

    # Mode 5 & Mode 6
    is_geo_1xxx_lock = bool(is_dual_pillar and g1_win == pk_dp)
    is_double_pwr_lock = bool(is_dual_pillar and g1_win == pk_dp and all_win == pk_dp)

    # Guards for Modes 7, 8, 9
    h_el, a_el = str(wtp["hel"]), str(wtp["ael"])
    pk_el = h_el if pk_dp == h else a_el
    op_el = a_el if pk_dp == h else h_el
    pk_l5 = h_l5 if pk_dp == h else a_l5
    earth_ok = not (pk_el == "EARTH" and op_el != "EARTH")
    pk_1sum = h_sum if pk_dp == h else a_sum
    pk_1cnt = len(h_1xxx) if pk_dp == h else len(a_1xxx)
    both_pos_1xxx = (len(h_1xxx) > 0 and len(a_1xxx) > 0 and h_sum > 0 and a_sum > 0)
    neg_anchor_ok = (pk_1cnt >= 1 and pk_1sum < 0)
    gf_delta = abs(h_gf - a_gf)
    dl_or_ref = (g1_win == pk_dp and all_win == pk_dp) or (pk_1cnt >= 1 and gf_delta >= 4.0 and maj23_win == pk_dp)

    # Mode 7: earth_neg_lock
    is_m7 = bool(is_dual_pillar and earth_ok and not both_pos_1xxx and neg_anchor_ok and dl_or_ref)

    # Mode 8: safe_dl_core
    safe_dl_win = pk_dp if (g1_win == pk_dp and all_win == pk_dp and earth_ok) else ""
    is_m8 = bool(
        is_m7
        or (is_vip_cross and safe_dl_win == pk_vip)
        or (dl_or_ref and pk_el != "EARTH" and neg_anchor_ok and pk_l5 >= 60.0 and tpk == ppk)
    )
    pk_m8 = pk_vip if (is_vip_cross and safe_dl_win == pk_vip and not is_m7) else pk_dp

    # Mode 9: pos_inv_lock (Polarity Inversion when both 1xxx > 0)
    pos_inv_trig = bool(both_pos_1xxx and abs(h_sum - a_sum) >= 2.0)
    pos_inv_win = (h if h_sum > a_sum else a) if pos_inv_trig else ""
    div_ref_ok = bool(g1_win != all_win and gf_delta >= 5.0 and maj23_win in (h, a))
    if is_m7:
        is_m9, pk_m9 = True, pk_dp
    elif is_vip_cross and safe_dl_win == pk_vip:
        is_m9, pk_m9 = True, pk_vip
    elif pos_inv_trig and ((pos_inv_win == h and h_l5 >= 55.0) or (pos_inv_win == a and a_l5 >= 55.0)):
        is_m9, pk_m9 = True, pos_inv_win
    elif is_dual_pillar and div_ref_ok and maj23_win == pk_dp and earth_ok:
        is_m9, pk_m9 = True, pk_dp
    else:
        is_m9, pk_m9 = False, pk_dp

    # Mode 10: gf_fin_pure (100% coverage pure GF-FIN argmin, tie-broken by Elo)
    pk_m10 = h if h_gf < a_gf else (a if a_gf < h_gf else fav_elo)

    # Mode 11: tri_gf_routed (3-Num + Cold 0xxx + Anti-Drop, zero twin dependency)
    s3_sign_split = (h_s3 < 0 < a_s3) or (a_s3 < 0 < h_s3)
    s3_split_win = h if (h_s3 < 0 < a_s3) else (a if (a_s3 < 0 < h_s3) else "")
    pk_m11 = s3_split_win or triple3_win or maj23_win or pk_m10
    m11_l5 = h_l5 if pk_m11 == h else a_l5
    m11_el = h_el if pk_m11 == h else a_el
    m11_0 = h_0sum if pk_m11 == h else a_0sum
    m11_1cnt = len(h_1xxx) if pk_m11 == h else len(a_1xxx)
    if m11_el == "EARTH" and (h_el != "EARTH" or a_el != "EARTH") and m11_l5 < 52.0:
        # EARTH flip to stronger non-EARTH side
        pk_m11 = a if pk_m11 == h else h
        m11_code, m11_reason, m11_flip = "M11_EARTH_FLIP", "چرخش ضد تله EARTH به سمت بازیکن قوی‌تر", True
        is_m11 = True
    elif m11_1cnt == 0 and ((pk_m11 == h and a_l5 >= 58.0) or (pk_m11 == a and h_l5 >= 58.0)):
        pk_m11 = a if pk_m11 == h else h
        m11_code, m11_reason, m11_flip = "M11_ZERO1XXX_OPP", "حبس 1xxx=0 و چرخش به بازیکن مقابل", True
        is_m11 = True
    elif s3_sign_split and m11_l5 >= 54.0:
        m11_code, m11_reason, m11_flip = "M11_S3_SPLIT", "موتور ۳ عددی: شکاف علامت Σ(3) منفی در برابر مثبت", False
        is_m11 = True
    elif triple3_win and m11_l5 >= 52.0:
        m11_code, m11_reason, m11_flip = "M11_TRIPLE3", "موتور ۳ عددی: اجماع کامل ۳/۳ کانال عددی", False
        is_m11 = True
    elif m11_0 <= -3.0 and cold0_win == pk_m11 and m11_l5 >= 55.0:
        m11_code, m11_reason, m11_flip = "M11_COLD_ANCHOR", "موتور ۳ عددی: لنگر قطب سرد Σ(0xxx)", False
        is_m11 = True
    else:
        m11_code, m11_reason, m11_flip = "M11_HOLD", "موتور ۳ عددی: خارج از آستانه قفل", False
        is_m11 = False

    # Mode 12: tri_gf_ultralock (Mode 9 Ultra ∪ ColdAnchor ∪ Bipolar 0011 ∪ S3 Split \ 2 Safety Locks)
    dual_earth_hold = (h_el == "EARTH" and a_el == "EARTH")
    cand_m12 = pk_m9 if is_m9 else (pk_m11 if is_m11 else pk_dp)
    clash_3of3_hold = bool(triple3_win and triple3_win != cand_m12)
    cand_l5 = h_l5 if cand_m12 == h else a_l5
    cand_0 = h_0sum if cand_m12 == h else a_0sum
    bipolar_ok = bool(c0011_win == cand_m12 and is_dual_pillar and cand_l5 >= 58.0)

    if dual_earth_hold:
        is_m12, m12_code, m12_reason = False, "ULTRA_DUAL_EARTH_HOLD", "توقف ایمنی: تقابل دو بازیکن EARTH"
    elif clash_3of3_hold:
        is_m12, m12_code, m12_reason = False, "ULTRA_3OF3_CLASH_HOLD", "توقف ایمنی: تضاد همزاد با اجماع ۳/۳ اعداد"
    elif is_m9 and cand_l5 >= 56.0:
        is_m12, m12_code, m12_reason = True, "ULTRA_M9_CORE", "ابرقفل حالت ۱۲: هسته قفل جامع + تایید GF-FIN"
    elif cand_0 <= -4.0 and cold0_win == cand_m12 and is_dual_pillar and cand_l5 >= 58.0:
        is_m12, m12_code, m12_reason = True, "ULTRA_COLD_ANCHOR", "ابرقفل حالت ۱۲: قطب سرد ۰xxx هم‌جهت با دو-ستونی"
    elif bipolar_ok:
        is_m12, m12_code, m12_reason = True, "ULTRA_BIPOLAR_0011", "ابرقفل حالت ۱۲: توازن دوقطبی 0011 هم‌جهت"
    elif s3_sign_split and s3_split_win == cand_m12 and is_dual_pillar and cand_l5 >= 60.0:
        is_m12, m12_code, m12_reason = True, "ULTRA_S3_SPLIT", "ابرقفل حالت ۱۲: شکاف علامت Σ(3) + تایید دو-ستونی"
    else:
        is_m12, m12_code, m12_reason = False, "M11_RAW", "موتور ۳ عددی پایه (در انتظار آزادسازی هوشمند)"
    pk_m12 = cand_m12

    # Mode 13: anti_nobet_smart (exact parity with evalSmartAntiNoBet in NbaDashboardTab.tsx!)
    p13 = pk_m12
    o13 = a if p13 == h else h
    p13_el = h_el if p13 == h else a_el
    o13_el = a_el if p13 == h else h_el
    p13_l5 = h_l5 if p13 == h else a_l5
    o13_l5 = a_l5 if p13 == h else h_l5
    is_3of3_p13 = (triple3_win == p13)
    dp_o13 = (is_dual_pillar and pk_dp == o13)
    raw_fb13 = m12_reason.startswith("موتور ۳ عددی")

    if is_m12:
        is_m13, vip_m13, pk_m13 = True, bool(is_diamond or p13_l5 >= 75.0), p13
    elif dual_earth_hold or m12_code == "ULTRA_3OF3_CLASH_HOLD":
        is_m13, vip_m13, pk_m13 = False, False, p13
    elif is_m11 and pk_m11 == p13 and p13_el != "EARTH" and p13_l5 >= 75.0:
        is_m13, vip_m13, pk_m13 = True, bool(p13_l5 >= 80.0), p13
    elif (not is_m11) and o13_el != "EARTH" and (not is_3of3_p13) and ((dp_o13 and o13_l5 >= 52.0) or (raw_fb13 and o13_l5 >= 60.0)):
        is_m13, vip_m13, pk_m13 = True, False, o13
    else:
        is_m13, vip_m13, pk_m13 = False, False, p13

    # Total-Elem-12 (6 player facets + 1 tournament/venue entity = 7 entities per player)
    h_ents = hp_facets + [tm_ent_h]
    a_ents = ap_facets + [tm_ent_a]
    h_ep_p = [sum(int(p["ep"].split("-")[j]) for p in hp_facets) for j in range(4)]
    a_ep_p = [sum(int(p["ep"].split("-")[j]) for p in ap_facets) for j in range(4)]
    h_ep_tot = [h_ep_p[j] + ep_tm_h[j] for j in range(4)]
    a_ep_tot = [a_ep_p[j] + ep_tm_a[j] for j in range(4)]
    h_ef_tot = [h_ep_tot[j] + date_sum_4[j] for j in range(4)]
    a_ef_tot = [a_ep_tot[j] + date_sum_4[j] for j in range(4)]

    h_gf_p12 = "".join("1" if abs(h_ep_p[j] + date_sum_4[j]) % 2 == 1 else "0" for j in range(4))
    a_gf_p12 = "".join("1" if abs(a_ep_p[j] + date_sum_4[j]) % 2 == 1 else "0" for j in range(4))
    h_gff_p12 = calc_gf_fin(tuple(h_ep_p[j] + date_sum_4[j] for j in range(4)), h_gf_p12)
    a_gff_p12 = calc_gf_fin(tuple(a_ep_p[j] + date_sum_4[j] for j in range(4)), a_gf_p12)
    h_gf_tot = "".join("1" if abs(x) % 2 == 1 else "0" for x in h_ef_tot)
    a_gf_tot = "".join("1" if abs(x) % 2 == 1 else "0" for x in a_ef_tot)
    h_gff_tot = calc_gf_fin(tuple(h_ef_tot), h_gf_tot)
    a_gff_tot = calc_gf_fin(tuple(a_ef_tot), a_gf_tot)

    h_w_ents = [e for e in h_ents if e["gf"].startswith("1")]
    a_w_ents = [e for e in a_ents if e["gf"].startswith("1")]
    h_c_ents = [e for e in h_ents if e["gf"].startswith("0")]
    a_c_ents = [e for e in a_ents if e["gf"].startswith("0")]
    h_0011_ents = [e for e in h_ents if e["gf"] == "0011"]
    a_0011_ents = [e for e in a_ents if e["gf"] == "0011"]

    h_w_gff = round(sum(e.get("gff", e.get("gf_fin", 0.0)) for e in h_w_ents), 1)
    a_w_gff = round(sum(e.get("gff", e.get("gf_fin", 0.0)) for e in a_w_ents), 1)
    h_c_gff = round(sum(e.get("gff", e.get("gf_fin", 0.0)) for e in h_c_ents), 1)
    a_c_gff = round(sum(e.get("gff", e.get("gf_fin", 0.0)) for e in a_c_ents), 1)
    h_c0011_gff = round(sum(e.get("gff", e.get("gf_fin", 0.0)) for e in h_0011_ents), 1)
    a_c0011_gff = round(sum(e.get("gff", e.get("gf_fin", 0.0)) for e in a_0011_ents), 1)
    h_s_gff = round(h_w_gff + h_c_gff, 1)
    a_s_gff = round(a_w_gff + a_c_gff, 1)
    h_d_gff = round(h_w_gff - h_c_gff, 1)
    a_d_gff = round(a_w_gff - a_c_gff, 1)
    h_s_pwr = round(sum(e["pwr"] for e in h_ents), 1)
    a_s_pwr = round(sum(e["pwr"] for e in a_ents), 1)

    h_dom, h_dom_cnt, h_dom_tie = dominant_elem_info(h_ef_tot)
    a_dom, a_dom_cnt, a_dom_tie = dominant_elem_info(a_ef_tot)
    h_lead_cnt = sum(1 for i in range(4) if h_ef_tot[i] > a_ef_tot[i])
    a_lead_cnt = sum(1 for i in range(4) if a_ef_tot[i] > h_ef_tot[i])
    dual_water = (h_dom == "WATER" and a_dom == "WATER")
    dom_split = (not h_dom_tie and not a_dom_tie and h_dom != a_dom)

    # Base Mode 14 signal before Smart14 wrapper
    base_m14_pick = h if h_gff_tot < a_gff_tot else (a if a_gff_tot < h_gff_tot else fav_elo)
    m14_l5 = h_l5 if base_m14_pick == h else a_l5
    if not dual_water and ((base_m14_pick == h and h_lead_cnt >= 3) or (base_m14_pick == a and a_lead_cnt >= 3)) and m14_l5 >= 55.0:
        base_m14_sig, t12_code = True, "TOT12_LEAD_3OF4"
    elif not dual_water and is_dual_pillar and pk_dp == base_m14_pick and m14_l5 >= 58.0:
        base_m14_sig, t12_code = True, "TOT12_DUAL_HARMONY"
    elif not dual_water and ((base_m14_pick == h and h_w_gff < a_w_gff and h_c_gff < a_c_gff) or (base_m14_pick == a and a_w_gff < h_w_gff and a_c_gff < h_c_gff)):
        base_m14_sig, t12_code = True, "TOT12_BIPOLAR_HARMONY"
    else:
        base_m14_sig, t12_code = False, "TOT12_NEUTRAL"

    # Exact Mode 14 (Smart14), Mode 15 (Fusion4), and Mode 16 (Referee6) mirroring NbaDashboardTab.tsx!
    p14 = base_m14_pick
    o14 = a if p14 == h else h
    pl5_14 = h_l5 if p14 == h else a_l5
    ol5_14 = a_l5 if p14 == h else h_l5
    p_warm_14 = h_w_gff if p14 == h else a_w_gff
    p12_fav_opp = (h_gff_p12 < a_gff_p12) if o14 == h else (a_gff_p12 < h_gff_p12)
    p12_fav_base = (h_gff_p12 < a_gff_p12) if p14 == h else (a_gff_p12 < h_gff_p12)
    spwr_fav_opp = (h_s_pwr < a_s_pwr) if o14 == h else (a_s_pwr < h_s_pwr)
    m11_dir_opp = (pk_m11 == o14)
    m11_fav_opp = (is_m11 and pk_m11 == o14)
    p_lead_14 = h_lead_cnt if p14 == h else a_lead_cnt
    o_lead_14 = a_lead_cnt if p14 == h else h_lead_cnt

    trap_bipolar = bool(base_m14_sig and t12_code == "TOT12_BIPOLAR_HARMONY" and pl5_14 < 75.0)
    trap_away_warm = bool(base_m14_sig and p14 == a and p_warm_14 < 0)
    trap_water = bool(base_m14_sig and dual_water)
    has_trap_14 = trap_bipolar or trap_away_warm or trap_water

    sm14_kind = "M14_HOLD_NEUTRAL"
    if base_m14_sig:
        if has_trap_14:
            pk_sm14 = o14
            if m11_dir_opp and not dual_water:
                is_sm14, vip_sm14, sm14_kind = True, False, "M14_TRAP_FLIP"
            else:
                is_sm14, vip_sm14, sm14_kind = False, False, "M14_VETO_TRAP"
        else:
            is_sm14, vip_sm14, pk_sm14, sm14_kind = True, bool(p_lead_14 == 3 or dom_split), p14, "M14_CORE_CLEAN"
    elif not dual_water and pl5_14 >= 75.0:
        is_sm14, vip_sm14, pk_sm14, sm14_kind = True, bool(pl5_14 >= 80.0 or p_lead_14 == 3), p14, "M14_DIRECT_RELEASE"
    elif not dual_water and ((m11_fav_opp and spwr_fav_opp and ol5_14 >= 55.0) or (ol5_14 >= 62.0 and (m11_fav_opp or p12_fav_opp))):
        is_sm14, vip_sm14, pk_sm14, sm14_kind = True, bool((m11_fav_opp and spwr_fav_opp) or o_lead_14 == 3), o14, "M14_OPPOSITE_FLIP"
    else:
        is_sm14, vip_sm14, pk_sm14 = False, False, p14

    # Dominant Element Follow-Up (Mode 15 & 16 helper)
    h_cat = "TIE" if h_dom_tie else h_dom
    a_cat = "TIE" if a_dom_tie else a_dom
    dom_delta = abs(h_dom_cnt - a_dom_cnt)
    air_delta = abs(h_ef_tot[1] - a_ef_tot[1])
    h_ef_sum, a_ef_sum = sum(h_ef_tot), sum(a_ef_tot)
    ef_pick, ef_tier, ef_rule = "", "NEUTRAL", "NEUTRAL"
    if h_cat == "EARTH" and a_cat == "EARTH" and dom_delta >= 10:
        ef_pick, ef_tier, ef_rule = (h if h_dom_cnt < a_dom_cnt else a), "STRONG", "EARTH_SAT10_SMALL"
    elif air_delta >= 8:
        ef_pick, ef_tier, ef_rule = (h if h_ef_tot[1] < a_ef_tot[1] else a), "STRONG", "AIR_SAT8_SMALL"
    elif h_cat == "WATER" and a_cat == "WATER" and 1 <= dom_delta <= 3:
        ef_pick, ef_tier, ef_rule = (h if h_dom_cnt < a_dom_cnt else a), "STRONG", "WATER_1_3_SMALL"
    elif h_cat == "WATER" and a_cat == "WATER" and dom_delta >= 4:
        ef_pick, ef_tier, ef_rule = (h if h_dom_cnt > a_dom_cnt else a), "STRONG", "WATER_4_PLUS_LARGE"
    elif h_dom_tie != a_dom_tie:
        ef_pick, ef_tier, ef_rule = (h if h_dom_tie else a), "STRONG", "TIE_VS_UNIQ"
    elif h_cat == "EARTH" and a_cat == "EARTH" and 4 <= dom_delta <= 9:
        ef_pick, ef_tier, ef_rule = (h if h_dom_cnt > a_dom_cnt else a), "STRONG", "EARTH_4_9_LARGE"
    elif h_lead_cnt == 3 or a_lead_cnt == 3:
        ef_pick, ef_tier, ef_rule = (h if h_lead_cnt == 3 else a), "MEDIUM", "LEAD_3OF4"
    elif h_cat == "EARTH" and a_cat == "EARTH" and 1 <= dom_delta <= 3:
        ef_pick, ef_tier, ef_rule = (h if h_dom_cnt > a_dom_cnt else a), "MEDIUM", "EARTH_1_3_LARGE"
    elif h_ef_sum != a_ef_sum:
        ef_pick, ef_tier, ef_rule = (h if h_ef_sum > a_ef_sum else a), "MEDIUM", "SPLIT_SUM_LARGE"

    # Mode 15: fusion4_elem (4-Pattern Element × Smart14 Fusion)
    sug_pick = pk_sm14
    sug_l5 = h_l5 if sug_pick == h else a_l5
    ep_is_h = bool(ef_pick and ef_pick == h)
    ep_l5 = 0.0 if not ef_pick else (h_l5 if ep_is_h else a_l5)
    ep_p12_ok = False if not ef_pick else (h_gff_p12 < a_gff_p12 if ep_is_h else a_gff_p12 < h_gff_p12)
    ep_sum_ok = False if not ef_pick else (h_ef_sum > a_ef_sum if ep_is_h else a_ef_sum > h_ef_sum)
    ep_m11_dir = bool(ef_pick and pk_m11 == ef_pick)
    ep_m11_sig = bool(ef_pick and is_m11 and pk_m11 == ef_pick)
    sug_team_sig = bool(t_sig and tpk == sug_pick)
    agree_boxes = bool(ef_pick and sug_pick == ef_pick)
    clash_boxes = bool(ef_pick and sug_pick != ef_pick)
    sat_trap = ef_rule in ("AIR_SAT8_SMALL", "EARTH_SAT10_SMALL")

    p1_hit = bool(not dual_water and agree_boxes and ep_is_h and ep_m11_dir and (ep_l5 >= 58.0 or (ef_tier == "STRONG" and ep_l5 >= 52.0)))
    p2_hit = bool(not dual_water and agree_boxes and (is_sm14 or (ef_tier == "STRONG" and (ep_m11_sig or sug_team_sig or (ep_p12_ok and ep_sum_ok and ep_l5 >= 60.0)))))
    p3_hit = bool(not dual_water and ef_pick and ef_tier == "STRONG" and ep_p12_ok and ep_l5 >= 62.0 and (agree_boxes or not is_sm14))
    p4_air_trap = bool(clash_boxes and (sug_team_sig or (is_sm14 and sug_l5 >= 75.0)) and sat_trap)
    p4_hit = bool(not dual_water and clash_boxes and not sat_trap and (sug_team_sig or (is_sm14 and sug_l5 >= 75.0)))
    is_m15 = bool(p1_hit or p2_hit or p3_hit or p4_hit)
    pk_m15 = ef_pick if (p1_hit or p2_hit or p3_hit) else (sug_pick if p4_hit else sug_pick)
    vip_m15 = bool((int(p1_hit) + int(p2_hit) + int(p3_hit) + int(p4_hit)) >= 2)

    # Mode 16: referee6_ranked (6-Box Weighted Ranked Referee)
    b1_h = int(h_w_gff < a_w_gff) + int(h_c_gff < a_c_gff) + int(h_d_gff < a_d_gff) + int(h_gff_tot < a_gff_tot) + int(not dual_water and (h_lead_cnt == 3 or (dom_split and h_dom in ("WATER", "AIR"))))
    b1_a = int(a_w_gff < h_w_gff) + int(a_c_gff < h_c_gff) + int(a_d_gff < h_d_gff) + int(a_gff_tot < h_gff_tot) + int(not dual_water and (a_lead_cnt == 3 or (dom_split and a_dom in ("WATER", "AIR"))))
    h_is_b, a_is_b = (p14 == h), (p14 == a)
    h_pure_l5 = (h_is_b and base_m14_sig and not has_trap_14) or (h_is_b and h_l5 >= 75.0) or ((not h_is_b) and (h_l5 >= 62.0 or (m11_fav_opp and spwr_fav_opp and h_l5 >= 55.0)))
    a_pure_l5 = (a_is_b and base_m14_sig and not has_trap_14) or (a_is_b and a_l5 >= 75.0) or ((not a_is_b) and (a_l5 >= 62.0 or (m11_fav_opp and spwr_fav_opp and a_l5 >= 55.0)))
    sm_h = (
        int(base_m14_sig and h_is_b and not has_trap_14)
        + int(not dual_water and (h_lead_cnt == 3 or (dom_split and (pk_sm14 == h if is_sm14 else h_dom != "EARTH"))))
        + int(h_pure_l5)
        + int(((is_m11 and pk_m11 == h) or p12_fav_opp or (has_trap_14 and pk_m11 == h)) if not h_is_b else (sm14_kind in ("M14_CORE_CLEAN", "M14_DIRECT_RELEASE") and p12_fav_base))
        + int(is_sm14 and pk_sm14 == h)
    )
    sm_a = (
        int(base_m14_sig and a_is_b and not has_trap_14)
        + int(not dual_water and (a_lead_cnt == 3 or (dom_split and (pk_sm14 == a if is_sm14 else a_dom != "EARTH"))))
        + int(a_pure_l5)
        + int(((is_m11 and pk_m11 == a) or p12_fav_opp or (has_trap_14 and pk_m11 == a)) if not a_is_b else (sm14_kind in ("M14_CORE_CLEAN", "M14_DIRECT_RELEASE") and p12_fav_base))
        + int(is_sm14 and pk_sm14 == a)
    )
    f4_h = int(p1_hit and ef_pick == h) + int(p2_hit and ef_pick == h) + int(p3_hit and ef_pick == h) + int(p4_hit and sug_pick == h)
    f4_a = int(p1_hit and ef_pick == a) + int(p2_hit and ef_pick == a) + int(p3_hit and ef_pick == a) + int(p4_hit and sug_pick == a)
    tot_h_ticks = b1_h + sm_h + int(ef_pick == h) + f4_h
    tot_a_ticks = b1_a + sm_a + int(ef_pick == a) + f4_a

    r82_sat_trap = clash_boxes and sat_trap and not p4_hit
    r82_weak_clash = bool(is_sm14 and clash_boxes and not p4_hit and not vip_sm14)
    f4_cnt = int(p1_hit) + int(p2_hit) + int(p3_hit) + int(p4_hit)
    f4_tick_lead = (tot_h_ticks > tot_a_ticks if pk_m15 == h else tot_a_ticks > tot_h_ticks) if is_m15 else False
    nobet_f4_trap = bool(not is_sm14 and is_m15 and not f4_tick_lead)
    opp_sug = a if sug_pick == h else h
    opp_sug_l5 = h_l5 if opp_sug == h else a_l5
    b1_pick = h if b1_h > b1_a else (a if b1_a > b1_h else "")
    rev_m12 = bool(not dual_water and is_m12 and pk_m12 == opp_sug and (opp_sug_l5 < 50.0 or opp_sug_l5 >= 55.0))
    rev_h_m11 = bool(not dual_water and opp_sug == h and is_m11 and pk_m11 == opp_sug and ef_pick == opp_sug)
    dir_m12 = bool(not dual_water and not is_sm14 and not p4_air_trap and is_m12 and pk_m12 == sug_pick and sug_l5 >= 60.0)
    dir_m11_b1 = bool(not dual_water and not is_sm14 and not p4_air_trap and is_m11 and pk_m11 == sug_pick and b1_pick == sug_pick and sug_l5 >= 65.0)

    pts_h, pts_a, top_hit = 0.0, 0.0, False

    def add_pts(tm: str, pts: float) -> None:
        nonlocal pts_h, pts_a
        if pts > 0 and tm == h:
            pts_h += pts
        elif pts > 0 and tm == a:
            pts_a += pts

    if is_m15:
        solo_p3 = p3_hit and not (p1_hit or p2_hit or p4_hit)
        if f4_cnt >= 2 and (is_sm14 or f4_tick_lead):
            add_pts(pk_m15, 10.0); top_hit = True
        elif (is_sm14 and p4_hit) or ((not is_sm14) and (p1_hit or p2_hit) and f4_tick_lead):
            add_pts(pk_m15, 8.0); top_hit = True
        elif (not is_sm14) and p4_hit and f4_tick_lead:
            add_pts(pk_m15, 7.0); top_hit = True
        elif solo_p3:
            add_pts(pk_m15, 1.0)
        else:
            add_pts(pk_m15, 1.5)
    elif p4_air_trap and ef_pick:
        add_pts(ef_pick, 3.5)

    if is_sm14 and vip_sm14 and not r82_sat_trap:
        add_pts(pk_sm14, 9.0); top_hit = True
    elif is_sm14 and not r82_weak_clash and not r82_sat_trap:
        add_pts(pk_sm14, 7.0); top_hit = True
    elif rev_m12 or rev_h_m11:
        add_pts(opp_sug, 7.0); top_hit = True
    elif not (r82_weak_clash or r82_sat_trap):
        if dir_m12 or dir_m11_b1:
            add_pts(sug_pick, 7.0); top_hit = True
        elif nobet_f4_trap and pk_m15 == sug_pick:
            add_pts(sug_pick, 1.5)
        else:
            add_pts(sug_pick, 5.0 if sug_l5 >= 58.0 else (4.0 if sug_l5 >= 50.0 else 2.5))

    if is_sm14 and not r82_weak_clash and not r82_sat_trap:
        add_pts(pk_sm14, 6.0); top_hit = True
    elif rev_m12 or rev_h_m11:
        add_pts(opp_sug, 5.0)
    elif not (r82_weak_clash or r82_sat_trap):
        if dir_m12 or dir_m11_b1:
            add_pts(sug_pick, 4.5)
        elif sm_h != sm_a:
            add_pts(h if sm_h > sm_a else a, 2.0)

    if ef_pick:
        add_pts(ef_pick, 3.5 if ef_tier == "STRONG" else 2.0)
    if not dual_water and (h_lead_cnt == 3 or a_lead_cnt == 3):
        add_pts(h if h_lead_cnt == 3 else a, 1.5)
    elif dom_split and h_dom_cnt != a_dom_cnt:
        add_pts(h if h_dom_cnt > a_dom_cnt else a, 1.0)
    if b1_pick:
        add_pts(b1_pick, 1.5 if abs(b1_h - b1_a) >= 2 else 1.0)

    delta_pts = round(abs(pts_h - pts_a), 1)
    pk_m16 = h if pts_h > pts_a else (a if pts_a > pts_h else sug_pick)
    ef_strong_m16 = bool(ef_pick and ef_tier == "STRONG" and ef_pick == pk_m16)
    is_m16 = bool((top_hit and delta_pts >= 8.0) or delta_pts >= 5.5 or (delta_pts >= 4.0 and ef_strong_m16))
    vip_m16 = bool(top_hit and delta_pts >= 18.0)

    modes_dict = {
        "dual_pillar":     {"sig": is_dual_pillar,     "vip": is_vip_cross,   "pick": pk_dp},
        "vip_cross":       {"sig": is_vip_cross,       "vip": is_diamond,     "pick": pk_vip},
        "astro_lock":      {"sig": is_astro_lock,      "vip": bool(is_astro_lock and is_vip_cross), "pick": pk_ast},
        "diamond":         {"sig": is_diamond,         "vip": is_diamond,     "pick": pk_dia},
        "geo_1xxx_lock":   {"sig": is_geo_1xxx_lock,   "vip": bool(is_vip_cross and g1_win == pk_vip), "pick": pk_dp},
        "double_pwr_lock": {"sig": is_double_pwr_lock, "vip": bool(is_vip_cross and g1_win == pk_vip and all_win == pk_vip), "pick": pk_dp},
        "earth_neg_lock":  {"sig": is_m7,              "vip": bool(is_m7 and is_vip_cross), "pick": pk_dp},
        "safe_dl_core":    {"sig": is_m8,              "vip": is_m7,          "pick": pk_m8},
        "pos_inv_lock":    {"sig": is_m9,              "vip": is_m7,          "pick": pk_m9},
        "gf_fin_pure":     {"sig": True,               "vip": bool(abs(h_gf - a_gf) >= 10.0), "pick": pk_m10},
        "tri_gf_routed":   {"sig": is_m11,             "vip": bool(is_m11 and triple3_win == pk_m11), "pick": pk_m11},
        "tri_gf_ultralock":{"sig": is_m12,             "vip": bool(is_m12 and is_m9), "pick": pk_m12},
        "anti_nobet_smart":{"sig": is_m13,             "vip": vip_m13,        "pick": pk_m13},
        "total_elem_12":   {"sig": base_m14_sig,       "vip": bool(base_m14_sig and (h_lead_cnt == 3 or a_lead_cnt == 3)), "pick": base_m14_pick},
        "smart_elem_14":   {"sig": is_sm14,            "vip": vip_sm14,       "pick": pk_sm14},
        "fusion4_elem":    {"sig": is_m15,             "vip": vip_m15,        "pick": pk_m15},
        "referee6_ranked": {"sig": is_m16,             "vip": vip_m16,        "pick": pk_m16},
    }

    geo1xxx_obj = {
        "h_sum": h_sum, "a_sum": a_sum,
        "h_cnt": len(h_1xxx), "a_cnt": len(a_1xxx),
        "h_0xxx": h_0sum, "a_0xxx": a_0sum,
        "h_0cnt": len(h_0xxx), "a_0cnt": len(a_0xxx),
        "cold0_diff": round(h_0sum - a_0sum, 1),
        "cold0_win": cold0_win,
        "h_0011": h_0011_sum, "a_0011": a_0011_sum,
        "h_0011_cnt": len(h_0011), "a_0011_cnt": len(a_0011),
        "c0011_win": c0011_win,
        "h_all": h_all, "a_all": a_all,
        "h_gf": h_gf, "a_gf": a_gf,
        "gf_diff": round(h_gf - a_gf, 1),
        "gf_win": gf_win,
        "h_s3": h_s3, "a_s3": a_s3,
        "s3_diff": round(h_s3 - a_s3, 1),
        "s3_win": s3_win,
        "s3_sign_split": s3_sign_split,
        "s3_split_win": s3_split_win,
        "maj23_win": maj23_win,
        "triple3_win": triple3_win,
        "m11_route": {"code": m11_code, "reason_fa": m11_reason, "flipped": m11_flip},
        "m12_route": {"code": m12_code, "reason_fa": m12_reason, "flipped": False},
        "diff": round(h_sum - a_sum, 1),
        "win": g1_win,
        "all_win": all_win,
        "safe_dl_win": safe_dl_win,
        "pos_inv": {
            "both_pos": both_pos_1xxx,
            "triggered": pos_inv_trig,
            "win": pos_inv_win,
            "case_code": "POS_INV" if pos_inv_trig else "NONE",
            "dc": round(h_0sum - a_0sum, 1),
            "d1": round(h_sum - a_sum, 1),
            "l5_big": max(h_l5, a_l5),
            "reason_fa": "چرخش قطبیت دو-مثبت 1xxx" if pos_inv_trig else "عادی",
        },
        "guards": {
            "eval_team": pk_dp,
            "el_wk": pk_el, "el_dy": pk_el,
            "opp_el_wk": op_el, "opp_el_dy": op_el,
            "l5_wk": pk_l5, "l5_dy": pk_l5,
            "earth_ok": earth_ok,
            "has_neg": neg_anchor_ok,
            "margin_ok": abs(h_sum - a_sum) >= 1.5,
            "neg_anchor_ok": neg_anchor_ok,
            "pos_inv_trap": both_pos_1xxx,
            "d1": round(h_sum - a_sum, 1),
            "d8": round(h_all - a_all, 1),
            "safe_ok": bool(safe_dl_win),
            "reason_fa": "PASS" if (earth_ok and neg_anchor_ok) else "GUARD",
        },
    }

    tot12_obj = {
        "h_cnt12": len(hp_facets), "a_cnt12": len(ap_facets),
        "h_cnt1": len(h_w_ents), "a_cnt1": len(a_w_ents),
        "h_cnt0": len(h_c_ents), "a_cnt0": len(a_c_ents),
        "h_cnt0011": len(h_0011_ents), "a_cnt0011": len(a_0011_ents),
        "h_w_gff": h_w_gff, "a_w_gff": a_w_gff,
        "h_c_gff": h_c_gff, "a_c_gff": a_c_gff,
        "h_c0011_gff": h_c0011_gff, "a_c0011_gff": a_c0011_gff,
        "h_s_gff": h_s_gff, "a_s_gff": a_s_gff,
        "h_d_gff": h_d_gff, "a_d_gff": a_d_gff,
        "h_s_pwr": h_s_pwr, "a_s_pwr": a_s_pwr,
        "h_ep_p12": h_ep_p, "a_ep_p12": a_ep_p,
        "h_ep_tm": list(ep_tm_h), "a_ep_tm": list(ep_tm_a),
        "h_ep_tot": h_ep_tot, "a_ep_tot": a_ep_tot,
        "h_ef_tot": h_ef_tot, "a_ef_tot": a_ef_tot,
        "h_gf_p12": h_gf_p12, "a_gf_p12": a_gf_p12,
        "h_gff_p12": h_gff_p12, "a_gff_p12": a_gff_p12,
        "h_gf_tot": h_gf_tot, "a_gf_tot": a_gf_tot,
        "h_gff_tot": h_gff_tot, "a_gff_tot": a_gff_tot,
        "h_qtot": qtot_h, "a_qtot": qtot_a,
        "code": t12_code,
        "reason_fa": "تحلیل بردار کل المنت‌های بازیکن + تورنمنت/کورت",
        "flipped": False,
        "h_tm_ent": tm_ent_h,
        "a_tm_ent": tm_ent_a,
        "h_p12": [{"fn": p["fn"], "no": p["no"], "pos": p["pos"], "st": p["st"], "mpg": p["mpg"], "ep": p["ep"], "ef": p["ef"], "gf": p["gf"], "gff": p["gf_fin"], "pwr": p["pwr"]} for p in hp_facets],
        "a_p12": [{"fn": p["fn"], "no": p["no"], "pos": p["pos"], "st": p["st"], "mpg": p["mpg"], "ep": p["ep"], "ef": p["ef"], "gf": p["gf"], "gff": p["gf_fin"], "pwr": p["pwr"]} for p in ap_facets],
    }

    return modes_dict, geo1xxx_obj, tot12_obj, tier_code, tier_fa, driver, is_vetoed


def run_pipeline() -> None:
    t0 = time.time()
    all_by_tour = load_all_matches("/tmp/tennis_raw")
    print(f"[1/4] Loaded raw main-tour matches in {time.time()-t0:.1f}s -> ATP={len(all_by_tour['ATP'])}, WTA={len(all_by_tour['WTA'])}")

    dash_base = "/home/antigravity/moghimarash-create/TENNIS-SIGNAL-DASHBORD/artifacts/calc-dashboard/public"
    fus_base = "/home/antigravity/moghimarash-create/TENNIS-FUSION-SIGNAL/artifacts/calc-dashboard/public"
    os.makedirs(dash_base, exist_ok=True)
    os.makedirs(fus_base, exist_ok=True)

    DEG3_OPTS = ("opt1", "opt2", "opt3")
    MODE_16_LIST = [
        ("m01", "dual_pillar", "Mode 1: Dual Pillar (T + P)"),
        ("m02", "vip_cross", "Mode 2: VIP Cross (T × P)"),
        ("m03", "astro_lock", "Mode 3: Astro F30 Lock"),
        ("m04", "diamond", "Mode 4: Diamond Lock (T ∩ P)"),
        ("m05", "geo_1xxx_lock", "Mode 5: Geomantic 1xxx Lock"),
        ("m06", "double_pwr_lock", "Mode 6: Double Power Lock (1xxx + ΣAll)"),
        ("m07", "earth_neg_lock", "Mode 7: Earth + Neg-Anchor + GF-FIN"),
        ("m08", "safe_dl_core", "Mode 8: Safe Double-Lock Core"),
        ("m09", "pos_inv_lock", "Mode 9: Polarity Inversion v5 + GF-FIN"),
        ("m10", "gf_fin_pure", "Mode 10: Pure GF-FIN (100% Slate)"),
        ("m11", "tri_gf_routed", "Mode 11: 3-Number + Cold 0xxx Standalone"),
        ("m12", "tri_gf_ultralock", "Mode 12: 3-Number Ultra-Lock + 2 Safety Guards"),
        ("m13", "anti_nobet_smart", "Mode 13: Smart Anti-NO-BET (Direct + Flip)"),
        ("m14", "smart_elem_14", "Mode 14: Total Element Polarity [F-A-W-E]"),
        ("m15", "fusion4_elem", "Mode 15: 4-Pattern Element × Box-2 Fusion"),
        ("m16", "referee6_ranked", "Mode 16: 6-Box Weighted Ranked Referee"),
    ]

    # Store output structures
    dash_games: dict[tuple[str, str], list[dict[str, Any]]] = {(t, o): [] for t in ("ATP", "WTA") for o in DEG3_OPTS}
    fus_games: dict[tuple[str, str], list[dict[str, Any]]] = {(t, o): [] for t in ("ATP", "WTA") for o in DEG3_OPTS}
    hist_export: dict[tuple[str, str], list[list[Any]]] = {(t, o): [] for t in ("ATP", "WTA") for o in (*DEG3_OPTS, "p")}

    for tour in ("ATP", "WTA"):
        t_tour = time.time()
        deg1 = ATP_DEG1 if tour == "ATP" else WTA_DEG1
        matches = all_by_tour[tour]

        # Zero-Lookahead Overall + Surface Elo state (strictly updated AFTER each calendar date!)
        elo_all: dict[str, float] = defaultdict(lambda: 1500.0)
        elo_surf: dict[tuple[str, str], float] = defaultdict(lambda: 1500.0)
        cnt_all: dict[str, int] = defaultdict(int)
        cnt_surf: dict[tuple[str, str], int] = defaultdict(int)
        season_wl: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])

        # Historical Twin Pools grouped by weekday, strictly appended AFTER each calendar date!
        pools_t: dict[tuple[str, str], FastDayPool] = {(o, wd): FastDayPool() for o in DEG3_OPTS for wd in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")}
        pools_p: dict[str, FastDayPool] = {wd: FastDayPool() for wd in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")}

        # Group matches by date for strict r.date < match.date batching
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for m in matches:
            by_date[m["d"]].append(m)

        game_seq = 0
        for d_iso in sorted(by_date.keys()):
            day_matches = by_date[d_iso]
            d_ctx = fpe.get_date_ctx(d_iso)
            _, wd_up, _, _, _, _, _, ele_date_sum, _ = d_ctx
            y, mo, dy = map(int, d_iso.split("-"))
            ym_greg = d_iso[:7]
            sh_m_str, sh_d_str = shamsi_ym(d_iso)

            # Precompute current dynamic Elo ranks strictly before d_iso
            ranked_players = sorted(elo_all.keys(), key=lambda p: elo_all[p], reverse=True)
            dyn_rank = {p: idx + 1 for idx, p in enumerate(ranked_players)}
            n_ranked = max(30, len(ranked_players))
            q1_cut, q2_cut = max(10, n_ranked // 6), max(20, n_ranked // 3)

            pending_elo_updates: list[tuple[str, str, str, float, float]] = []
            pending_pool_t: list[tuple[str, str, dict[str, Any], list[Any]]] = []
            pending_pool_p: list[tuple[str, dict[str, Any], list[Any]]] = []

            for m in day_matches:
                surf = m["surface"]
                w_nm, l_nm = m["w_name"], m["l_name"]

                def blended_elo(pl: str) -> float:
                    ea = elo_all[pl]
                    es = elo_surf[(pl, surf)]
                    ns = cnt_surf[(pl, surf)]
                    ws = min(0.45, 0.09 * ns)
                    return (1.0 - ws) * ea + ws * es

                eb_w = blended_elo(w_nm)
                eb_l = blended_elo(l_nm)

                # STRICT PRE-MATCH ORDERING: higher pre-match blended Elo -> h (Player 1), tie-broken by rank then ASCII name!
                key_w = (round(eb_w, 4), -m["w_rk"], w_nm)
                key_l = (round(eb_l, 4), -m["l_rk"], l_nm)
                if key_w >= key_l:
                    h, a = w_nm, l_nm
                    h_ioc, a_ioc = m["w_ioc"], m["l_ioc"]
                    eb_h, eb_a = eb_w, eb_l
                    hp, ap = m["w_g"], m["l_g"]
                    mg = max(1, hp - ap)
                    aw = h
                    sc_disp = m["score_raw"]
                else:
                    h, a = l_nm, w_nm
                    h_ioc, a_ioc = m["l_ioc"], m["w_ioc"]
                    eb_h, eb_a = eb_l, eb_w
                    hp, ap = m["l_g"], m["w_g"]
                    mg = min(-1, hp - ap)
                    aw = a
                    sc_disp = m["score_raw"]

                # Pre-match probabilities & WTP object
                p_win_h = 1.0 / (1.0 + (10.0 ** (-(eb_h - eb_a) / 400.0)))
                ph_str = 1.0 / (1.0 + (10.0 ** (-(eb_h - 1500.0) / 400.0)))
                pa_str = 1.0 / (1.0 + (10.0 ** (-(eb_a - 1500.0) / 400.0)))
                l5h = round(p_win_h * 100.0, 1)
                htp = round(50.0 + (eb_h - 1500.0) / 12.0, 1)
                atp = round(50.0 + (eb_a - 1500.0) / 12.0, 1)
                hrk = dyn_rank.get(h, min(999, m["w_rk"] if h == w_nm else m["l_rk"]))
                ark = dyn_rank.get(a, min(999, m["l_rk"] if h == w_nm else m["w_rk"]))
                hw_s, hl_s = season_wl[(m["season"], h)]
                aw_s, al_s = season_wl[(m["season"], a)]
                h_tab = f"{int(hrk <= q1_cut)}{int(hrk <= q2_cut)}{int(ark <= q1_cut)}{int(ark <= q2_cut)}"
                a_tab = f"{int(ark <= q1_cut)}{int(ark <= q2_cut)}{int(hrk <= q1_cut)}{int(hrk <= q2_cut)}"

                wtp_base = {
                    "mon": d_iso,
                    "htp": htp, "atp": atp, "dtp": round(htp - atp, 1),
                    "hrk": hrk, "ark": ark,
                    "hwl": f"{hw_s}-{hl_s}", "awl": f"{aw_s}-{al_s}",
                    "hpct": round(ph_str * 100.0, 1), "apct": round(pa_str * 100.0, 1),
                    "hel": player_elem(ph_str), "ael": player_elem(pa_str),
                    "l5h": l5h,
                    "hodds": round(1.0 / max(0.04, p_win_h), 2),
                    "aodds": round(1.0 / max(0.04, 1.0 - p_win_h), 2),
                    "mel": matchup_elem(max(l5h, round(100.0 - l5h, 1))),
                }

                # Queue Elo update for AFTER all matches on d_iso are evaluated!
                p_exp_w = 1.0 / (1.0 + (10.0 ** (-(elo_all[w_nm] - elo_all[l_nm]) / 400.0)))
                p_exp_ws = 1.0 / (1.0 + (10.0 ** (-(elo_surf[(w_nm, surf)] - elo_surf[(l_nm, surf)]) / 400.0)))
                pending_elo_updates.append((w_nm, l_nm, surf, p_exp_w, p_exp_ws))
                season_wl[(m["season"], w_nm)][0] += 1
                season_wl[(m["season"], l_nm)][1] += 1

                # Match-sky Ephemeris table at Tournament City local timezone (14:00 local session)
                tbl = LazyTbl(fpe.get_jd_local(y, mo, dy, m["tz"], 14, 0))

                # Gematria degrees (100% Birthdate-Free!)
                city_str, tourney_str = m["city"], m["tourney"]
                deg_city = egem(city_str) % 360
                deg_tour = egem(tourney_str) % 360
                deg_surf = egem(surf) % 360

                deg3_map = {
                    "opt1": deg_city + deg_tour,   # Option 1: MOD(City,360) + MOD(Tournament,360)
                    "opt2": deg_tour,              # Option 2: MOD(Tournament,360)
                    "opt3": deg_city,              # Option 3: MOD(City,360)
                }

                h_first, h_last = split_first_last(h)
                a_first, a_last = split_first_last(a)
                h_d2_full = egem(h) % 360
                a_d2_full = egem(a) % 360
                h_d2_last = egem(h_last) % 360
                a_d2_last = egem(a_last) % 360
                h_d3_p = deg_surf + (egem(h_ioc) % 360)
                a_d3_p = deg_surf + (egem(a_ioc) % 360)
                h_fawe = cached_fawe(h)
                a_fawe = cached_fawe(a)
                hc_code, ac_code = player_3code(h), player_3code(a)

                # Evaluate Angle P (Last Name x [Surface + IOC])
                ep_hp, ef_hp, ed_hp, mhp = fpe.fast_eval_entity(d_ctx, deg1, h_d2_last, h_d3_p, cached_fawe(h_last), tbl)
                ep_ap, ef_ap, ed_ap, map_ = fpe.fast_eval_entity(d_ctx, deg1, a_d2_last, a_d3_p, cached_fawe(a_last), tbl)
                h12_p = tuple(
                    [f"{ed_hp[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                    + [f"{ef_hp[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                    + [f"{ep_hp[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                )
                a12_p = tuple(
                    [f"{ed_ap[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                    + [f"{ef_ap[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                    + [f"{ep_ap[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                )
                h_fin_p = geo_code_from_ef(ef_hp)
                h_dyn_p = geo_code_from_ef(ed_hp)
                a_dyn_p = geo_code_from_ef(ed_ap)
                sc_p = 0
                for km in ("qdeg", "qfin", "qdec", "qdecf", "gd", "rul"):
                    vh_m = mhp[km][0] + mhp[km][1]
                    va_m = map_[km][0] + map_[km][1]
                    if vh_m > va_m:
                        sc_p += 1
                    elif va_m > vh_m:
                        sc_p -= 1
                f30_p = sc_p * 5

                is_eval_season = m["season"] in ("2024", "2025", "2026")
                res_p = None
                if is_eval_season:
                    mel_p = matchup_elem(l5h if f30_p >= 0 else round(100.0 - l5h, 1))
                    res_p = eval_pillar_signal(h, a, h12_p, h_fin_p, h_dyn_p, h_tab, f30_p, pools_p[wd_up], mel_p)

                p_twin_row = {
                    "d": d_iso, "hc": hc_code, "ac": ac_code, "hp": hp, "ap": ap, "mg": mg,
                    "h12": h12_p, "h_fin": h_fin_p, "h_dyn": h_dyn_p, "h_tab": h_tab,
                }
                p_hist_export_row = [d_iso, wd_up, m["season"], h, a, hp, ap, mg, list(h12_p), h_dyn_p, list(a12_p), a_dyn_p, f30_p, 0, h_tab, a_tab]
                pending_pool_p.append((wd_up, p_twin_row, p_hist_export_row))

                # Precompute the 5 shared player facets (Facets 2..6) once per match if in 2024-2026
                shared_h_facets: list[dict[str, Any]] = []
                shared_a_facets: list[dict[str, Any]] = []
                if is_eval_season:
                    game_seq += 1
                    facet_specs_h = [
                        ("P", f"{h_last} [{surf}+{h_ioc}]", "SURF", h_d2_last, h_d3_p, cached_fawe(h_last)),
                        ("N", f"{h_first} [{surf}+{city_str}]", "FIRST", egem(h_first) % 360, deg_surf + deg_city, cached_fawe(h_first)),
                        ("V", f"{h} [{tourney_str}+{surf}]", "COURT", h_d2_full, deg_tour + deg_surf, h_fawe),
                        ("C", f"{h_last} [{tourney_str}]", "EVENT", h_d2_last, deg_tour, cached_fawe(h_last)),
                        ("I", f"{h_last}+{h_ioc} [{city_str}]", "CITY", (egem(h_last) + egem(h_ioc)) % 360, deg_city, h_fawe),
                    ]
                    facet_specs_a = [
                        ("P", f"{a_last} [{surf}+{a_ioc}]", "SURF", a_d2_last, a_d3_p, cached_fawe(a_last)),
                        ("N", f"{a_first} [{surf}+{city_str}]", "FIRST", egem(a_first) % 360, deg_surf + deg_city, cached_fawe(a_first)),
                        ("V", f"{a} [{tourney_str}+{surf}]", "COURT", a_d2_full, deg_tour + deg_surf, a_fawe),
                        ("C", f"{a_last} [{tourney_str}]", "EVENT", a_d2_last, deg_tour, cached_fawe(a_last)),
                        ("I", f"{a_last}+{a_ioc} [{city_str}]", "CITY", (egem(a_last) + egem(a_ioc)) % 360, deg_city, a_fawe),
                    ]
                    for idx_f, (no_s, fn_s, pos_s, d2_v, d3_v, fw_v) in enumerate(facet_specs_h, start=2):
                        ep_v, ef_v, _, md_v = fpe.fast_eval_entity(d_ctx, deg1, d2_v, d3_v, fw_v, tbl)
                        ef_str = f"{ef_v[0]}-{ef_v[1]}-{ef_v[2]}-{ef_v[3]}"
                        gf_s = geo_code_from_ef(ef_v)
                        gff_v = calc_gf_fin(ef_v, gf_s)
                        pwr_v = calc_pwr(md_v)
                        hc_v, m_v = md_v["qfin"]
                        shared_h_facets.append({
                            "pid": f"{hc_code}_{no_s}", "fn": fn_s, "jn": h_last, "no": str(idx_f), "pos": pos_s,
                            "st": True, "mpg": 30.0, "d2": d2_v, "d3": d3_v % 360,
                            "ep": f"{ep_v[0]}-{ep_v[1]}-{ep_v[2]}-{ep_v[3]}", "ef": ef_str, "gf": gf_s, "gf_fin": gff_v,
                            "qf": f"{abs(hc_v)}{'HOT' if hc_v >= 0 else 'COLD'}/{abs(m_v)}{'MOIST' if m_v >= 0 else 'DRY'}",
                            "dec": dec_label(d2_v), "pwr": pwr_v,
                        })
                    for idx_f, (no_s, fn_s, pos_s, d2_v, d3_v, fw_v) in enumerate(facet_specs_a, start=2):
                        ep_v, ef_v, _, md_v = fpe.fast_eval_entity(d_ctx, deg1, d2_v, d3_v, fw_v, tbl)
                        ef_str = f"{ef_v[0]}-{ef_v[1]}-{ef_v[2]}-{ef_v[3]}"
                        gf_s = geo_code_from_ef(ef_v)
                        gff_v = calc_gf_fin(ef_v, gf_s)
                        pwr_v = calc_pwr(md_v)
                        hc_v, m_v = md_v["qfin"]
                        shared_a_facets.append({
                            "pid": f"{ac_code}_{no_s}", "fn": fn_s, "jn": a_last, "no": str(idx_f), "pos": pos_s,
                            "st": True, "mpg": 30.0, "d2": d2_v, "d3": d3_v % 360,
                            "ep": f"{ep_v[0]}-{ep_v[1]}-{ep_v[2]}-{ep_v[3]}", "ef": ef_str, "gf": gf_s, "gf_fin": gff_v,
                            "qf": f"{abs(hc_v)}{'HOT' if hc_v >= 0 else 'COLD'}/{abs(m_v)}{'MOIST' if m_v >= 0 else 'DRY'}",
                            "dec": dec_label(d2_v), "pwr": pwr_v,
                        })

                # Evaluate Angle T across all 3 DEG3 Options (opt1, opt2, opt3)
                for opt_k in DEG3_OPTS:
                    d3_t = deg3_map[opt_k]
                    ep_ht, ef_ht, ed_ht, mht = fpe.fast_eval_entity(d_ctx, deg1, h_d2_full, d3_t, h_fawe, tbl)
                    ep_at, ef_at, ed_at, mat = fpe.fast_eval_entity(d_ctx, deg1, a_d2_full, d3_t, a_fawe, tbl)

                    h12_t = tuple(
                        [f"{ed_ht[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                        + [f"{ef_ht[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                        + [f"{ep_ht[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                    )
                    a12_t = tuple(
                        [f"{ed_at[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                        + [f"{ef_at[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                        + [f"{ep_at[j]} {('FIRE','AIR','WATER','EARTH')[j]}" for j in range(4)]
                    )
                    h_fin_t = geo_code_from_ef(ef_ht)
                    a_fin_t = geo_code_from_ef(ef_at)
                    h_dyn_t = geo_code_from_ef(ed_ht)
                    a_dyn_t = geo_code_from_ef(ed_at)

                    votes6 = []
                    for km in ("qdeg", "qfin", "qdec", "qdecf", "gd", "rul"):
                        vh_m = mht[km][0] + mht[km][1]
                        va_m = mat[km][0] + mat[km][1]
                        votes6.append(1 if vh_m > va_m else (-1 if va_m > vh_m else 0))
                    f30_t = sum(votes6) * 5

                    t_twin_row = {
                        "d": d_iso, "hc": hc_code, "ac": ac_code, "hp": hp, "ap": ap, "mg": mg,
                        "h12": h12_t, "h_fin": h_fin_t, "h_dyn": h_dyn_t, "h_tab": h_tab,
                    }
                    t_hist_export_row = [d_iso, wd_up, m["season"], h, a, hp, ap, mg, list(h12_t), h_dyn_t, list(a12_t), a_dyn_t, f30_t, 0, h_tab, a_tab]
                    pending_pool_t.append((opt_k, wd_up, t_twin_row, t_hist_export_row))

                    if not is_eval_season:
                        continue

                    assert res_p is not None
                    # Dynamic mel wrt T's pick direction
                    res_t_raw = eval_pillar_signal(h, a, h12_t, h_fin_t, h_dyn_t, h_tab, f30_t, pools_t[(opt_k, wd_up)], "AIR")
                    t_pick = res_t_raw["pick"]
                    l5_for_t = l5h if t_pick == h else round(100.0 - l5h, 1)
                    wtp_t = dict(wtp_base)
                    wtp_t["dtp"] = round((htp - atp) if t_pick == h else (atp - htp), 1)
                    wtp_t["mel"] = matchup_elem(l5_for_t)
                    res_t_raw["f1_wtp"] = bool(res_t_raw["f1_guard"] and wtp_t["mel"] != "EARTH")
                    res_t_raw["vip_idx3"] = bool(res_t_raw["f1_wtp"] and (wtp_t["mel"] == "FIRE" or (res_t_raw["nat"] and res_t_raw["idx3"]["minD"] >= 2)))

                    # Facet 1 (T_Active) + Facets 2..6
                    ef_ht_s = f"{ef_ht[0]}-{ef_ht[1]}-{ef_ht[2]}-{ef_ht[3]}"
                    ef_at_s = f"{ef_at[0]}-{ef_at[1]}-{ef_at[2]}-{ef_at[3]}"
                    gff_ht = calc_gf_fin(ef_ht, h_fin_t)
                    gff_at = calc_gf_fin(ef_at, a_fin_t)
                    pwr_ht = calc_pwr(mht)
                    pwr_at = calc_pwr(mat)
                    hc_ht, md_ht = mht["qfin"]
                    hc_at, md_at = mat["qfin"]

                    f1_h = {
                        "pid": f"{hc_code}_T", "fn": f"{h} [{city_str} • {tourney_str}]", "jn": h_last, "no": "1", "pos": "MAIN",
                        "st": True, "mpg": 36.0, "d2": h_d2_full, "d3": d3_t % 360,
                        "ep": f"{ep_ht[0]}-{ep_ht[1]}-{ep_ht[2]}-{ep_ht[3]}", "ef": ef_ht_s, "gf": h_fin_t, "gf_fin": gff_ht,
                        "qf": f"{abs(hc_ht)}{'HOT' if hc_ht >= 0 else 'COLD'}/{abs(md_ht)}{'MOIST' if md_ht >= 0 else 'DRY'}",
                        "dec": dec_label(h_d2_full), "pwr": pwr_ht,
                    }
                    f1_a = {
                        "pid": f"{ac_code}_T", "fn": f"{a} [{city_str} • {tourney_str}]", "jn": a_last, "no": "1", "pos": "MAIN",
                        "st": True, "mpg": 36.0, "d2": a_d2_full, "d3": d3_t % 360,
                        "ep": f"{ep_at[0]}-{ep_at[1]}-{ep_at[2]}-{ef_at[3]}", "ef": ef_at_s, "gf": a_fin_t, "gf_fin": gff_at,
                        "qf": f"{abs(hc_at)}{'HOT' if hc_at >= 0 else 'COLD'}/{abs(md_at)}{'MOIST' if md_at >= 0 else 'DRY'}",
                        "dec": dec_label(a_d2_full), "pwr": pwr_at,
                    }
                    f1_a["ep"] = f"{ep_at[0]}-{ep_at[1]}-{ep_at[2]}-{ep_at[3]}"

                    hp_facets = [f1_h] + shared_h_facets
                    ap_facets = [f1_a] + shared_a_facets

                    # Venue+Surface Anchor entity for Total-Elem
                    ep_vh, ef_vh, _, m_vh = fpe.fast_eval_entity(d_ctx, deg1, deg_tour, deg_city + deg_surf, cached_fawe(tourney_str), tbl)
                    ep_va, ef_va, _, m_va = fpe.fast_eval_entity(d_ctx, deg1, deg_city, deg_tour + deg_surf, cached_fawe(city_str), tbl)
                    gf_vh, gf_va = geo_code_from_ef(ef_vh), geo_code_from_ef(ef_va)
                    tm_ent_h = {
                        "ep": f"{ep_vh[0]}-{ep_vh[1]}-{ep_vh[2]}-{ep_vh[3]}",
                        "ef": f"{ef_vh[0]}-{ef_vh[1]}-{ef_vh[2]}-{ef_vh[3]}",
                        "gf": gf_vh, "gff": calc_gf_fin(ef_vh, gf_vh), "pwr": calc_pwr(m_vh),
                    }
                    tm_ent_a = {
                        "ep": f"{ep_va[0]}-{ep_va[1]}-{ep_va[2]}-{ep_va[3]}",
                        "ef": f"{ef_va[0]}-{ef_va[1]}-{ef_va[2]}-{ef_va[3]}",
                        "gf": gf_va, "gff": calc_gf_fin(ef_va, gf_va), "pwr": calc_pwr(m_va),
                    }

                    base_card = {
                        "n": game_seq + (0 if tour == "ATP" else 100000),
                        "tour": tour,
                        "deg1": deg1,
                        "deg3_opt": opt_k,
                        "surface": surf,
                        "city": city_str,
                        "tourney": tourney_str,
                        "rnd": m["rnd"],
                        "day": wd_up,
                        "d": d_iso,
                        "ym": ym_greg,
                        "sh_m": sh_m_str,
                        "sh_d": sh_d_str,
                        "s": m["season"],
                        "h": h,
                        "a": a,
                        "hc": hc_code,
                        "ac": ac_code,
                        "h_ioc": h_ioc,
                        "a_ioc": a_ioc,
                        "hp": hp,
                        "ap": ap,
                        "sc": f"{sc_disp} ({hp}-{ap})",
                        "aw": aw,
                        "done": True,
                        "hw": bool(aw == h),
                        "venue": f"{tourney_str} • {city_str} ({surf})",
                        "deg": [deg1, h_d2_full, d3_t, a_d2_full, d3_t, h_d2_last, a_d2_last, h_d3_p],
                        "pw": t_pick,
                        "fpw": t_pick if res_t_raw["f1_wtp"] else "",
                        "sys_win": t_pick,
                        "twWin": t_pick,
                        "st": "WIN" if t_pick == aw else "LOSS",
                        "fst": ("WIN" if t_pick == aw else "LOSS") if res_t_raw["f1_wtp"] else "",
                        "ph": bool(t_pick == h),
                        "vm6": f30_t,
                        "f30": f30_t,
                        "v": votes6,
                        "nd": abs(sum(votes6)),
                        "b137": abs(f30_t) >= 15,
                        "n80": res_t_raw["f1_wtp"],
                        "e80": res_t_raw["vip_idx3"],
                        "q80": res_t_raw["f1_guard"],
                        "g83": res_t_raw["vip_idx3"],
                        "tier": "VIP" if res_t_raw["vip_idx3"] else ("F1" if res_t_raw["f1_wtp"] else "RAW"),
                        "qdeg": [fmt_qual_pair(mht["qdeg"]), fmt_qual_pair(mat["qdeg"])],
                        "qfin": [fmt_qual_pair(mht["qfin"]), fmt_qual_pair(mat["qfin"])],
                        "qdec": [fmt_qual_pair(mht["qdec"]), fmt_qual_pair(mat["qdec"])],
                        "qdecf": [fmt_qual_pair(mht["qdecf"]), fmt_qual_pair(mat["qdecf"])],
                        "qtot": [fmt_qual_pair(mht["qtot"]), fmt_qual_pair(mat["qtot"])],
                        "qp2": [fmt_qual_pair(mht["qp2"]), fmt_qual_pair(mat["qp2"])],
                        "gd": [fmt_qual_pair(mht["gd"]), fmt_qual_pair(mat["gd"])],
                        "rul": [fmt_qual_pair(mht["rul"]), fmt_qual_pair(mat["rul"])],
                        "qnam": [fmt_qual_pair(mht["qnam"]), fmt_qual_pair(mat["qnam"])],
                        "cf": [deg1, h_d2_full, d3_t],
                        "twVotes": res_t_raw["twVotes"],
                        "twPct": res_t_raw["twPct"],
                        "h_12": list(h12_t),
                        "a_12": list(a12_t),
                        "h_geo": h_fin_t,
                        "a_geo": a_fin_t,
                        "h_geo_dyn": h_dyn_t,
                        "a_geo_dyn": a_dyn_t,
                        "h_geo_tab": h_tab,
                        "a_geo_tab": a_tab,
                        "idx3": res_t_raw["idx3"],
                        "f1": res_t_raw["f1"],
                        "f1_idx": res_t_raw["f1_idx"],
                        "f1_guard": res_t_raw["f1_guard"],
                        "f1_wtp": res_t_raw["f1_wtp"],
                        "vip_idx3": res_t_raw["vip_idx3"],
                        "f1_union": res_t_raw["f1_wtp"],
                        "f1_wtp_day": res_t_raw["f1_wtp"],
                        "vip_idx3_day": res_t_raw["vip_idx3"],
                        "f1_union_day": res_t_raw["f1_wtp"],
                        "is_nat": res_t_raw["nat"],
                        "twins": res_t_raw["twins"],
                        "wtp": wtp_t,
                        "wtp_day": wtp_t,
                    }
                    dash_games[(tour, opt_k)].append(base_card)

                    # Build 16-Mode Fusion Card for TENNIS-FUSION-SIGNAL
                    modes_16, geo1xxx_obj, tot12_obj, tier_code, tier_fa, driver, is_vetoed = compute_16_fusion_modes(
                        h=h, a=a, wtp=wtp_t, res_t=res_t_raw, res_p=res_p,
                        hp_facets=hp_facets, ap_facets=ap_facets,
                        tm_ent_h=tm_ent_h, tm_ent_a=tm_ent_a,
                        ep_tm_h=ep_vh, ep_tm_a=ep_va,
                        date_sum_4=ele_date_sum,
                        qtot_h=mht["qtot"][0] + mht["qtot"][1],
                        qtot_a=mat["qtot"][0] + mat["qtot"][1],
                    )
                    m12_def = modes_16["tri_gf_ultralock"]
                    f_card = dict(base_card)
                    f_card["h_players"] = hp_facets
                    f_card["a_players"] = ap_facets
                    f_card["sys_win"] = m12_def["pick"]
                    f_card["pw"] = m12_def["pick"]
                    f_card["fpw"] = m12_def["pick"] if m12_def["sig"] else ""
                    f_card["f30"] = f30_t + f30_p
                    f_card["vm6"] = f30_t + f30_p
                    f_card["f1"] = bool(m12_def["sig"])
                    f_card["f1_idx"] = bool(m12_def["sig"])
                    f_card["f1_guard"] = bool(m12_def["sig"])
                    f_card["f1_wtp"] = bool(m12_def["sig"])
                    f_card["vip_idx3"] = bool(m12_def["vip"])
                    f_card["st"] = "WIN" if m12_def["pick"] == aw else "LOSS"
                    f_card["fst"] = f_card["st"] if m12_def["sig"] else ""
                    f_card["fusion_meta"] = {
                        "mode": "tri_gf_ultralock",
                        "tier": tier_code,
                        "tier_fa": tier_fa,
                        "driver": driver,
                        "in_auth_overlap": True,
                        "vetoed": is_vetoed,
                        "geo1xxx": geo1xxx_obj,
                        "total_elem_12": tot12_obj,
                        "modes": modes_16,
                        "team": {
                            "pick": t_pick,
                            "votes": res_t_raw["twVotes"],
                            "pct": res_t_raw["twPct"],
                            "f30": f30_t,
                            "ch": f"{res_t_raw['idx3']['vh']}H-{res_t_raw['idx3']['va']}A",
                            "sig": res_t_raw["f1_wtp"],
                            "vip": res_t_raw["vip_idx3"],
                            "deg2": h_d2_full,
                            "deg3": d3_t,
                        },
                        "player": {
                            "pick": res_p["pick"],
                            "votes": res_p["twVotes"],
                            "pct": res_p["twPct"],
                            "f30": f30_p,
                            "ch": f"{res_p['idx3']['vh']}H-{res_p['idx3']['va']}A",
                            "sig": res_p["f1_wtp"],
                            "vip": res_p["vip_idx3"],
                        },
                    }
                    fus_games[(tour, opt_k)].append(f_card)

            # STRICT ZERO-LOOKAHEAD COMMIT AT END OF CALENDAR DAY d_iso
            for w_nm, l_nm, surf, p_exp_w, p_exp_ws in pending_elo_updates:
                k_all_w = 32.0 / ((cnt_all[w_nm] + 5) ** 0.20)
                k_all_l = 32.0 / ((cnt_all[l_nm] + 5) ** 0.20)
                elo_all[w_nm] += k_all_w * (1.0 - p_exp_w)
                elo_all[l_nm] -= k_all_l * p_exp_w
                cnt_all[w_nm] += 1
                cnt_all[l_nm] += 1

                k_sf_w = 36.0 / ((cnt_surf[(w_nm, surf)] + 5) ** 0.20)
                k_sf_l = 36.0 / ((cnt_surf[(l_nm, surf)] + 5) ** 0.20)
                elo_surf[(w_nm, surf)] += k_sf_w * (1.0 - p_exp_ws)
                elo_surf[(l_nm, surf)] -= k_sf_l * p_exp_ws
                cnt_surf[(w_nm, surf)] += 1
                cnt_surf[(l_nm, surf)] += 1

            for opt_k, wd_k, t_row, hist_row in pending_pool_t:
                pools_t[(opt_k, wd_k)].append(t_row)
                hist_export[(tour, opt_k)].append(hist_row)
            for wd_k, p_row, hist_row in pending_pool_p:
                pools_p[wd_k].append(p_row)
                hist_export[(tour, "p")].append(hist_row)

        print(f"[2/4] Completed {tour} (DEG1={deg1}) in {time.time()-t_tour:.1f}s -> 2024-2026 matches={len(fus_games[(tour, 'opt1')])}")

    # Compute comprehensive benchmarks across DEG3 opt1/opt2/opt3 and Modes 1..16
    deg3_bench: dict[str, Any] = {"options": {}, "angle_p": {}}
    OPT_META = {
        "opt1": {"code": "CITY_PLUS_TOURNAMENT", "formula": "MOD(EnglishGem(City), 360) + MOD(EnglishGem(Tournament), 360)"},
        "opt2": {"code": "TOURNAMENT_ONLY", "formula": "MOD(EnglishGem(Tournament), 360)"},
        "opt3": {"code": "CITY_ONLY", "formula": "MOD(EnglishGem(City), 360)"},
    }

    def calc_stat(rows: list[tuple[bool, bool]]) -> dict[str, Any]:
        # rows of (is_sig, is_win)
        sigs = [w for s, w in rows if s]
        n = len(sigs)
        w = sum(1 for x in sigs if x)
        pct = round(100.0 * w / n, 2) if n > 0 else 0.0
        return {"w": w, "n": n, "pct": pct, "rec": f"{w}/{n}"}

    for opt_k in DEG3_OPTS:
        deg3_bench["options"][opt_k] = {"meta": OPT_META[opt_k], "tours": {}}
        for tour_scope in ("ATP", "WTA", "ALL"):
            g_list = (
                dash_games[("ATP", opt_k)] + dash_games[("WTA", opt_k)]
                if tour_scope == "ALL"
                else dash_games[(tour_scope, opt_k)]
            )
            by_yr = {}
            for yr in ("2024", "2025", "2026"):
                sub = [g for g in g_list if g["s"] == yr]
                by_yr[yr] = {
                    "f1_wtp": calc_stat([(bool(g["f1_wtp"]), g["sys_win"] == g["aw"]) for g in sub]),
                    "vip": calc_stat([(bool(g["vip_idx3"]), g["sys_win"] == g["aw"]) for g in sub]),
                    "raw_all": calc_stat([(True, g["sys_win"] == g["aw"]) for g in sub]),
                }
            by_yr["total"] = {
                "f1_wtp": calc_stat([(bool(g["f1_wtp"]), g["sys_win"] == g["aw"]) for g in g_list]),
                "vip": calc_stat([(bool(g["vip_idx3"]), g["sys_win"] == g["aw"]) for g in g_list]),
                "raw_all": calc_stat([(True, g["sys_win"] == g["aw"]) for g in g_list]),
            }
            deg3_bench["options"][opt_k]["tours"][tour_scope] = by_yr

    # Pick winning default DEG3 option by highest ALL 2024-2026 f1_wtp accuracy
    best_opt = max(
        DEG3_OPTS,
        key=lambda o: deg3_bench["options"][o]["tours"]["ALL"]["total"]["f1_wtp"]["pct"],
    )
    deg3_bench["bestDefaultOption"] = best_opt

    # Angle P benchmark
    for tour_scope in ("ATP", "WTA", "ALL"):
        g_list = (
            fus_games[("ATP", best_opt)] + fus_games[("WTA", best_opt)]
            if tour_scope == "ALL"
            else fus_games[(tour_scope, best_opt)]
        )
        deg3_bench["angle_p"][tour_scope] = {
            yr: calc_stat([(bool(g["fusion_meta"]["player"]["sig"]), g["fusion_meta"]["player"]["pick"] == g["aw"]) for g in g_list if g["s"] == yr])
            for yr in ("2024", "2025", "2026")
        }
        deg3_bench["angle_p"][tour_scope]["total"] = calc_stat(
            [(bool(g["fusion_meta"]["player"]["sig"]), g["fusion_meta"]["player"]["pick"] == g["aw"]) for g in g_list]
        )

    # 16-Mode Benchmark Matrix across opt1/opt2/opt3 x ATP/WTA/ALL x 2024/2025/2026/Total/Last50
    fusion_bench: dict[str, Any] = {
        "bestDefaultDeg3": best_opt,
        "deg3Bench": deg3_bench,
        "modesMeta": [{"num": idx + 1, "id": m_id, "key": m_key, "title": m_title} for idx, (m_id, m_key, m_title) in enumerate(MODE_16_LIST)],
        "byOption": {},
    }

    for opt_k in DEG3_OPTS:
        fusion_bench["byOption"][opt_k] = {}
        for tour_scope in ("ATP", "WTA", "ALL"):
            g_list = (
                sorted(fus_games[("ATP", opt_k)] + fus_games[("WTA", opt_k)], key=lambda x: (x["d"], x["n"]))
                if tour_scope == "ALL"
                else fus_games[(tour_scope, opt_k)]
            )
            m_stats: dict[str, Any] = {}
            for idx, (m_id, m_key, m_title) in enumerate(MODE_16_LIST, start=1):
                yr_map = {}
                for yr in ("2024", "2025", "2026"):
                    sub = [g for g in g_list if g["s"] == yr]
                    yr_map[yr] = calc_stat([
                        (bool(g["fusion_meta"]["modes"][m_key]["sig"]), g["fusion_meta"]["modes"][m_key]["pick"] == g["aw"])
                        for g in sub
                    ])
                all_pairs = [
                    (bool(g["fusion_meta"]["modes"][m_key]["sig"]), g["fusion_meta"]["modes"][m_key]["pick"] == g["aw"])
                    for g in g_list
                ]
                tot_st = calc_stat(all_pairs)
                sig_wins = [w for s, w in all_pairs if s]
                l50 = sig_wins[-50:]
                l50_w = sum(1 for x in l50 if x)
                l50_pct = round(100.0 * l50_w / len(l50), 1) if l50 else 0.0
                m_stats[m_key] = {
                    "modeNum": idx,
                    "title": m_title,
                    "2024": yr_map["2024"],
                    "2025": yr_map["2025"],
                    "2026": yr_map["2026"],
                    "total": tot_st,
                    "last50": {"w": l50_w, "n": len(l50), "pct": l50_pct, "rec": f"{l50_w}/{len(l50)}"},
                }
            fusion_bench["byOption"][opt_k][tour_scope] = m_stats

    print(f"[3/4] Writing compact JSON packs (best DEG3 default = {best_opt})...")

    # Write TENNIS-SIGNAL-DASHBORD public packs (split by tour & option so every file is ~18-21 MB!)
    with open(f"{dash_base}/tennis_deg3_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(deg3_bench, f, ensure_ascii=False, indent=2)

    for tour in ("ATP", "WTA"):
        tlc = tour.lower()
        for opt_k in DEG3_OPTS:
            p_dash = f"{dash_base}/tennis_dashbord_{tlc}_{opt_k}.json"
            with open(p_dash, "w", encoding="utf-8") as f:
                json.dump({"tour": tour, "deg3Option": opt_k, "birthdateUsed": False, "games": dash_games[(tour, opt_k)]}, f, ensure_ascii=False, separators=(",", ":"))
            # Keep last 4,500 historical rows per tour in browser twin explorer pack so file stays ~1.5 MB
            p_hist_d = f"{dash_base}/tennis_hist_{tlc}_{opt_k}.json"
            with open(p_hist_d, "w", encoding="utf-8") as f:
                json.dump(hist_export[(tour, opt_k)][-4500:], f, ensure_ascii=False, separators=(",", ":"))
            shutil.copyfile(p_hist_d, f"{fus_base}/tennis_hist_{tlc}_{opt_k}.json")

            # Strip duplicate wtp_day and total_elem_12.{h_p12, a_p12} and shard by season year (2024/2025/2026) so every file is <28 MB!
            by_yr = {"2024": [], "2025": [], "2026": []}
            for g in fus_games[(tour, opt_k)]:
                g.pop("wtp_day", None)
                fm = g.get("fusion_meta")
                if isinstance(fm, dict):
                    t12 = fm.get("total_elem_12")
                    if isinstance(t12, dict):
                        t12.pop("h_p12", None)
                        t12.pop("a_p12", None)
                yr_k = str(g.get("s", g.get("d", "")[:4]))
                if yr_k in by_yr:
                    by_yr[yr_k].append(g)
            for yr_k, yr_list in by_yr.items():
                p_fus_yr = f"{fus_base}/fusion_{tlc}_{opt_k}_{yr_k}.json"
                with open(p_fus_yr, "w", encoding="utf-8") as f:
                    json.dump({"tour": tour, "deg3Option": opt_k, "season": yr_k, "birthdateUsed": False, "games": yr_list}, f, ensure_ascii=False, separators=(",", ":"))

        p_hist_p = f"{fus_base}/tennis_hist_{tlc}_p.json"
        with open(p_hist_p, "w", encoding="utf-8") as f:
            json.dump(hist_export[(tour, "p")][-4500:], f, ensure_ascii=False, separators=(",", ":"))

    # Default lightweight legacy fallback pointers (latest 300 matches of best_opt ATP, ~2.5 MB)
    with open(f"{dash_base}/nba_predictions_2580.json", "w", encoding="utf-8") as f:
        json.dump({"tour": "ATP", "deg3Option": best_opt, "birthdateUsed": False, "games": dash_games[("ATP", best_opt)][-300:]}, f, ensure_ascii=False, separators=(",", ":"))
    shutil.copyfile(f"{dash_base}/tennis_hist_atp_{best_opt}.json", f"{dash_base}/nba_history_pack_2010_2026.json")
    with open(f"{fus_base}/fusion_nba_master.json", "w", encoding="utf-8") as f:
        json.dump({"tour": "ATP", "deg3Option": best_opt, "birthdateUsed": False, "games": fus_games[("ATP", best_opt)][-300:]}, f, ensure_ascii=False, separators=(",", ":"))
    shutil.copyfile(f"{fus_base}/tennis_hist_atp_{best_opt}.json", f"{fus_base}/nba_history_pack_2010_2026.json")
    shutil.copyfile(f"{fus_base}/tennis_hist_atp_p.json", f"{fus_base}/player_nba_hist_mode_c.json")

    with open(f"{fus_base}/fusion_modes_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(fusion_bench, f, ensure_ascii=False, indent=2)

    print(f"[4/4] ALL DONE in {time.time()-t0:.1f}s! Best Default DEG3 Option = {best_opt}")


if __name__ == "__main__":
    run_pipeline()
