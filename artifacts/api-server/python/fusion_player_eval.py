#!/usr/bin/env python3
"""
Portable, zero-hardcoded-path NBA Player Astrological & Elemental Evaluator (`DEG1=53`, Mode C: `DEG2=egem(Full_Name)%360`, `DEG3=JerseyNoEff%360`).
100% bit-for-bit parity with `parity_check.py` and `rebuild_fusion_v5_pos_inv.py`.
"""
import sys, os, types, datetime, unicodedata
import pytz
import swisseph as swe

PY_SRC = os.path.dirname(os.path.abspath(__file__))
if PY_SRC not in sys.path:
    sys.path.insert(0, PY_SRC)

for mod_name in ["_lib", "_lib.runner", "_lib.sheets", "gspread", "gspread.exceptions"]:
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
if not hasattr(sys.modules["_lib.runner"], "emit_result"):
    sys.modules["_lib.runner"].emit_result = lambda **kw: None
if not hasattr(sys.modules["_lib.runner"], "log"):
    sys.modules["_lib.runner"].log = lambda msg: None
if not hasattr(sys.modules["_lib.sheets"], "open_sheet"):
    sys.modules["_lib.sheets"].open_sheet = lambda *a, **kw: None
if not hasattr(sys.modules["gspread"], "Spreadsheet"):
    sys.modules["gspread"].Spreadsheet = object
    sys.modules["gspread"].Worksheet = object
    sys.modules["gspread.exceptions"].APIError = Exception
    sys.modules["gspread.exceptions"].WorksheetNotFound = Exception

import step1_geomantic as s1
import step2_astro_aspects as s2
import step3_result_degree as s3
import step4_winner_prediction as s4

s2._init_ephe()
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
PLANETS_10 = s2.PLANETS[:10]

EGEM_MAP = {
    'A':1,'B':2,'C':20,'D':4,'E':5,'F':80,'G':3,'H':8,'I':10,'J':10,
    'K':20,'L':30,'M':40,'N':50,'O':70,'P':80,'Q':100,'R':200,'S':60,
    'T':400,'U':6,'V':6,'W':6,'X':70,'Y':10,'Z':7
}

def clean_ascii(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).strip()

def egem(s):
    return sum(EGEM_MAP.get(ch, 0) for ch in clean_ascii(s).upper())

def jersey_eff_num(j_str, zero_rule=True):
    s = str(j_str or "").strip()
    if s == "00":
        return 20 if zero_rule else 100
    if s == "0":
        return 10 if zero_rule else 0
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return 10 if zero_rule else 0
    v = int(digits)
    if v == 0 and zero_rule:
        return 10
    return v

_SIGNS_36 = [("Aries","Fire","Cardinal","Wands"),("Taurus","Earth","Fixed","Pentacles"),("Gemini","Air","Mutable","Swords"),("Cancer","Water","Cardinal","Cups"),("Leo","Fire","Fixed","Wands"),("Virgo","Earth","Mutable","Pentacles"),("Libra","Air","Cardinal","Swords"),("Scorpio","Water","Fixed","Cups"),("Sagittarius","Fire","Mutable","Wands"),("Capricorn","Earth","Cardinal","Pentacles"),("Aquarius","Air","Fixed","Swords"),("Pisces","Water","Mutable","Cups")]
_RULERS_7 = ["Mars","Sun","Venus","Mercury","Moon","Saturn","Jupiter"]
_RULER_EL = {"Mars":"Fire","Sun":"Fire","Venus":"Water","Mercury":"Earth","Moon":"Water","Saturn":"Earth","Jupiter":"Air"}
_EL_QUAL = {"Fire":(1,-1,"Hot","Dry"),"Earth":(-1,-1,"Cold","Dry"),"Air":(1,1,"Hot","Moist"),"Water":(-1,1,"Cold","Moist")}
_GEO_BITS = {i: tuple((i >> (3 - b)) & 1 for b in range(4)) for i in range(16)}

_DM = {}
for _d in range(1, 37):
    si, face = (_d - 1) // 3, ((_d - 1) % 3) + 1
    sign, se, mod, suit = _SIGNS_36[si]
    cn = (1 if mod == "Cardinal" else (4 if mod == "Fixed" else 7)) + face
    rul = _RULERS_7[(_d - 1) % 7]
    _DM[_d] = (
        _d,
        _d * _EL_QUAL[se][0], _d * _EL_QUAL[se][1],
        cn * _EL_QUAL[se][0], cn * _EL_QUAL[se][1],
        cn * _EL_QUAL[_RULER_EL[rul]][0], cn * _EL_QUAL[_RULER_EL[rul]][1],
        f"{sign} D{face}"
    )

_ARC_HC = [0] * 23
_ARC_MD = [0] * 23
for a_i in range(1, 23):
    _, hc_l, md_l = s4.ZOD_MAP[a_i]
    _ARC_HC[a_i] = a_i if hc_l == "HOT" else -a_i
    _ARC_MD[a_i] = a_i if md_l == "MOIST" else -a_i

_jd_tbl_cache = {}
def get_deg_table(jd):
    key = round(jd, 5)
    t = _jd_tbl_cache.get(key)
    if t is not None:
        return t
    p_degs = [(pn, swe.calc_ut(jd, pid, FLAGS)[0][0] % 360.0) for pn, pid in PLANETS_10]
    t = [0] * 360
    for deg in range(360):
        tot = 0
        fdeg = float(deg)
        for pn, pd in p_degs:
            sym = s2._best_aspect(fdeg, pd, pn)
            if sym is not None:
                v = s3.zod_aspect_deg(sym)
                if isinstance(v, (int, float)):
                    tot += int(v)
        t[deg] = tot
    _jd_tbl_cache[key] = t
    return t

_tz_cache = {}
def get_jd_local(y, m, d, tz_str, hh=19, mm=30):
    tz = _tz_cache.get(tz_str)
    if tz is None:
        tz = pytz.timezone(tz_str)
        _tz_cache[tz_str] = tz
    u = tz.localize(datetime.datetime(y, m, d, hh, mm, 0)).astimezone(pytz.utc)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60.0)

_date_ctx_cache = {}
def get_date_ctx(d_iso):
    ctx = _date_ctx_cache.get(d_iso)
    if ctx is not None:
        return ctx
    y, m, d = map(int, d_iso.split("-"))
    dt = datetime.date(y, m, d)
    wd_title = dt.strftime("%A")
    wd_up = wd_title.upper()
    f_helper = s1.WEEKDAY_NUM[wd_title] + sum(int(c) for c in f"{y:04d}{m:02d}{d:02d}")
    x2 = sum(int(c) for c in f"{m}{d}{y}")
    b_dig1, b_dig2 = _GEO_BITS[min(15, x2 // 10)], _GEO_BITS[min(15, x2 % 10)]
    ele_dig = tuple(b_dig1[j] + b_dig2[j] for j in range(4))

    ap2, aq2, ar2 = ((m - 1) % 22) + 1, ((d - 1) % 22) + 1, ((y - 1) % 22) + 1
    hc_day = _ARC_HC[ap2] + _ARC_HC[aq2] + _ARC_HC[ar2]
    md_day = _ARC_MD[ap2] + _ARC_MD[aq2] + _ARC_MD[ar2]
    bd2, be2 = abs(hc_day), abs(md_day)
    b_dt = [_GEO_BITS[min(15, x)] for x in (bd2 // 10, bd2 % 10, be2 // 10, be2 % 10)]
    ele_dt = tuple(sum(b[j] for b in b_dt) for j in range(4))

    by2 = s4.DAY_CODE_MAP.get(wd_up, "0101")
    ele_dw = tuple(int(ch) for ch in by2)
    ele_date_sum = tuple(ele_dig[j] + ele_dt[j] + ele_dw[j] for j in range(4))

    jd_u = swe.julday(y, m, d, 0.0)
    tbl_u = get_deg_table(jd_u)

    ctx = (dt, wd_up, f"{m}/{d}/{y}", f_helper, ele_dig, ele_dt, ele_dw, ele_date_sum, tbl_u)
    _date_ctx_cache[d_iso] = ctx
    return ctx

def fast_eval_entity(d_ctx, deg1, deg2, deg3, nam_fawe, tbl):
    _, _, _, f_helper, _, _, _, ele_date_sum, _ = d_ctx
    p1 = deg1 + f_helper
    p2 = deg2 + f_helper
    p3 = deg3 + f_helper

    a1, a2, a3 = ((p1 - 1) % 22) + 1, ((p2 - 1) % 22) + 1, ((p3 - 1) % 22) + 1
    el1_v = _ARC_HC[a1] + _ARC_HC[a2] + _ARC_HC[a3]
    el2_v = _ARC_MD[a1] + _ARC_MD[a2] + _ARC_MD[a3]

    cv, dv, ev = tbl[p1 % 360], tbl[p2 % 360], tbl[p3 % 360]
    mG, mH, mI = ((cv - 1) % 22) + 1, ((dv - 1) % 22) + 1, ((ev - 1) % 22) + 1
    hcAA_v = _ARC_HC[mG] + _ARC_HC[mH] + _ARC_HC[mI]
    mdAB_v = _ARC_MD[mG] + _ARC_MD[mH] + _ARC_MD[mI]

    qdeg_hc = hcAA_v + el1_v
    qdeg_md = mdAB_v + el2_v

    h2, i2 = abs(qdeg_hc), abs(qdeg_md)
    bp1, bp2, bp3, bp4 = _GEO_BITS[min(15, h2 // 10)], _GEO_BITS[min(15, h2 % 10)], _GEO_BITS[min(15, i2 // 10)], _GEO_BITS[min(15, i2 % 10)]
    ele_p = (bp1[0]+bp2[0]+bp3[0]+bp4[0], bp1[1]+bp2[1]+bp3[1]+bp4[1], bp1[2]+bp2[2]+bp3[2]+bp4[2], bp1[3]+bp2[3]+bp3[3]+bp4[3])
    ele_fin = (ele_p[0]+ele_date_sum[0], ele_p[1]+ele_date_sum[1], ele_p[2]+ele_date_sum[2], ele_p[3]+ele_date_sum[3])
    ele_dyn = (ele_p[0]+ele_fin[0], ele_p[1]+ele_fin[1], ele_p[2]+ele_fin[2], ele_p[3]+ele_fin[3])

    qfin_hc = (ele_fin[0] + ele_fin[1]) - (ele_fin[2] + ele_fin[3])
    qfin_md = (ele_fin[1] + ele_fin[2]) - (ele_fin[0] + ele_fin[3])

    mg = _DM[((cv - 1) % 36) + 1]
    mh = _DM[((dv - 1) % 36) + 1]
    mi = _DM[((ev - 1) % 36) + 1]
    f1 = _DM[((p1 - 1) % 36) + 1]
    f2 = _DM[((p2 - 1) % 36) + 1]
    f3 = _DM[((p3 - 1) % 36) + 1]

    qdec_hc = mg[1] + mh[1] + mi[1] + f1[1] + f2[1] + f3[1]
    qdec_md = mg[2] + mh[2] + mi[2] + f1[2] + f2[2] + f3[2]
    gd_hc   = mg[3] + mh[3] + mi[3] + f1[3] + f2[3] + f3[3]
    gd_md   = mg[4] + mh[4] + mi[4] + f1[4] + f2[4] + f3[4]
    rul_hc  = mg[5] + mh[5] + mi[5] + f1[5] + f2[5] + f3[5]
    rul_md  = mg[6] + mh[6] + mi[6] + f1[6] + f2[6] + f3[6]

    dh, dm_v = abs(qdec_hc), abs(qdec_md)
    bd1, bd2_b, bd3, bd4 = _GEO_BITS[min(15, dh // 10)], _GEO_BITS[min(15, dh % 10)], _GEO_BITS[min(15, dm_v // 10)], _GEO_BITS[min(15, dm_v % 10)]
    ele_decf = (
        bd1[0]+bd2_b[0]+bd3[0]+bd4[0]+ele_date_sum[0],
        bd1[1]+bd2_b[1]+bd3[1]+bd4[1]+ele_date_sum[1],
        bd1[2]+bd2_b[2]+bd3[2]+bd4[2]+ele_date_sum[2],
        bd1[3]+bd2_b[3]+bd3[3]+bd4[3]+ele_date_sum[3],
    )
    qdecf_hc = (ele_decf[0] + ele_decf[1]) - (ele_decf[2] + ele_decf[3])
    qdecf_md = (ele_decf[1] + ele_decf[2]) - (ele_decf[0] + ele_decf[3])

    ele_tot = (ele_dyn[0]+nam_fawe[0], ele_dyn[1]+nam_fawe[1], ele_dyn[2]+nam_fawe[2], ele_dyn[3]+nam_fawe[3])
    qtot_hc = (ele_tot[0] + ele_tot[1]) - (ele_tot[2] + ele_tot[3])
    qtot_md = (ele_tot[1] + ele_tot[2]) - (ele_tot[0] + ele_tot[3])
    qnam_hc = (nam_fawe[0] + nam_fawe[1]) - (nam_fawe[2] + nam_fawe[3])
    qnam_md = (nam_fawe[1] + nam_fawe[2]) - (nam_fawe[0] + nam_fawe[3])

    p2_b = []
    for v in ele_tot:
        p2_b.append(_GEO_BITS[min(15, v // 10)])
        p2_b.append(_GEO_BITS[min(15, v % 10)])
    ele_p2 = (
        sum(x[0] for x in p2_b), sum(x[1] for x in p2_b),
        sum(x[2] for x in p2_b), sum(x[3] for x in p2_b)
    )
    qp2_hc = (ele_p2[0] + ele_p2[1]) - (ele_p2[2] + ele_p2[3])
    qp2_md = (ele_p2[1] + ele_p2[2]) - (ele_p2[0] + ele_p2[3])

    m_dict = {
        "qdeg": (qdeg_hc, qdeg_md),
        "qfin": (qfin_hc, qfin_md),
        "qdec": (qdec_hc, qdec_md),
        "qdecf": (qdecf_hc, qdecf_md),
        "qtot": (qtot_hc, qtot_md),
        "qp2": (qp2_hc, qp2_md),
        "gd": (gd_hc, gd_md),
        "rul": (rul_hc, rul_md),
        "qnam": (qnam_hc, qnam_md),
        "decan_lbl": f"{f2[7]} / {f3[7]}",
    }
    return ele_p, ele_fin, ele_dyn, m_dict
