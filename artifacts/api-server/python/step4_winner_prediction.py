#!/usr/bin/env python3
"""
Step 4: NBA Calculation Builder (Sheet1 + Sheet3 + Game_Predictions)
Reads NBA-Result-Degree :: Node_Output (TENNIS_ISOLATED_RESULT_DEGREE),
executes the complete deterministic calculation pipeline of Nba-Calculation-1.xlsm:
  1) Sheet1 (116 columns A:DL — SPLIT_NUMBER, SPE_DIGIT, GEOMANCYFULL, ELE-P,
     Get_Day_Element, DigitalSum, ELE-DIGSUM, ELE-P-DIGSUM, DATE_SPLIT,
     MOD_ARCANUM, Get_Zodiac_Card, ElemMain, ElemSub, QUALITY-DAY, ELE-DATE,
     ELE-DATE+P+DIGSUM, DAY_GEO_CODE, ELE-DAYWEEK, ELE-FINAL, ELEM_Q1/Q2,
     SUM_ALL_ELEMENTS, QULITY-FIN, QULITY-DECAN, DD:DL)
  2) Sheet3 (85 columns A:CG — ELE-P, ELE-FINAL, ELE-DYN, QULITY-FIN,
     QULITY-DECAN, QULITY-P, QULITY-DYN, Nam-ele, QULITY-NAME, ELE-TOTAL,
     QULITY-TOTAL, Ele-Prime2, QULITY-PRIME2, ELE-DECAN-FIN, QULITY-DECAN-FIN,
     QULITY-GD-CARD, QULITY-RULER, 6-Rule Votes & Winner Determination)
  3) Game_Predictions (30 columns A:AD — Paired Home vs Away summary, VM6 score,
     and 80%–85.7% Fixed Pattern Tiers)
Writes outputs to NBA-Calculation (TENNIS_ISOLATED_CALC)
and NBA-Result-Degree :: Game_Predictions.
"""
import os, sys, json, re, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib.sheets import open_sheet

SS_RD   = os.environ.get("TENNIS_RESULT_DEGREE_SHEET_ID", "")
SS_CALC = os.environ.get("TENNIS_CALC_SHEET_ID", "")

GEO_NAMES = {
    0: "Populus (0000)", 1: "Tristitia (0001)", 2: "Albus (0010)", 3: "Fortuna Major (0011)",
    4: "Rubeus (0100)", 5: "Acquisitio (0101)", 6: "Conjunctio (0110)", 7: "Caput Draconis (0111)",
    8: "Laetitia (1000)", 9: "Carcer (1001)", 10: "Amissio (1010)", 11: "Puella (1011)",
    12: "Fortuna Minor (1100)", 13: "Puer (1101)", 14: "Cauda Draconis (1110)", 15: "Via (1111)"
}
GEO_BITS = {
    0:(0,0,0,0), 1:(0,0,0,1), 2:(0,0,1,0), 3:(0,0,1,1),
    4:(0,1,0,0), 5:(0,1,0,1), 6:(0,1,1,0), 7:(0,1,1,1),
    8:(1,0,0,0), 9:(1,0,0,1), 10:(1,0,1,0), 11:(1,0,1,1),
    12:(1,1,0,0), 13:(1,1,0,1), 14:(1,1,1,0), 15:(1,1,1,1)
}
DAY_EL_MAP = {
    "SUNDAY": "Sunday | Sun | [Fire]",
    "MONDAY": "Monday | Moon | [Water]",
    "TUESDAY": "Tuesday | Mars | [Fire]",
    "WEDNESDAY": "Wednesday | Mercury | [Air]",
    "THURSDAY": "Thursday | Jupiter | [Air]",
    "FRIDAY": "Friday | Venus | [Water]",
    "SATURDAY": "Saturday | Saturn | [Earth]",
}
DAY_CODE_MAP = {
    "SUNDAY": "0011",
    "MONDAY": "1111",
    "TUESDAY": "1101",
    "WEDNESDAY": "0110",
    "THURSDAY": "0101",
    "FRIDAY": "1011",
    "SATURDAY": "0001",
}
ZOD_MAP = {
    1: ('Scorpio - [Water]', 'COLD', 'MOIST'),
    2: ('Leo - [Fire]', 'HOT', 'DRY'),
    3: ('Gemini - [Air]', 'HOT', 'MOIST'),
    4: ('Aries - [Fire]', 'HOT', 'DRY'),
    5: ('Gemini - [Air]', 'HOT', 'MOIST'),
    6: ('Gemini - [Air]', 'HOT', 'MOIST'),
    7: ('Capricorn - [Earth]', 'COLD', 'DRY'),
    8: ('Libra - [Air]', 'HOT', 'MOIST'),
    9: ('Capricorn - [Earth]', 'COLD', 'DRY'),
    10: ('Gemini - [Air]', 'HOT', 'MOIST'),
    11: ('Taurus - [Earth]', 'COLD', 'DRY'),
    12: ('Cancer - [Water]', 'COLD', 'MOIST'),
    13: ('Gemini - [Air]', 'HOT', 'MOIST'),
    14: ('Leo - [Fire]', 'HOT', 'DRY'),
    15: ('Aries - [Fire]', 'HOT', 'DRY'),
    16: ('Gemini - [Air]', 'HOT', 'MOIST'),
    17: ('Taurus - [Earth]', 'COLD', 'DRY'),
    18: ('Scorpio - [Water]', 'COLD', 'MOIST'),
    19: ('Capricorn - [Earth]', 'COLD', 'DRY'),
    20: ('Leo - [Fire]', 'HOT', 'DRY'),
    21: ('Aquarius - [Air]', 'HOT', 'MOIST'),
    22: ('Virgo - [Earth]', 'COLD', 'DRY'),
}
LETTER_EL = {}
for ch in "EIJYOSUVW": LETTER_EL[ch] = 0 # Fire
for ch in "BHRT":      LETTER_EL[ch] = 3 # Earth
for ch in "DGLQZ":     LETTER_EL[ch] = 1 # Air
for ch in "ACKFPMNX":  LETTER_EL[ch] = 2 # Water

TRAP_TEAMS = {"Charlotte Hornets", "Toronto Raptors", "Brooklyn Nets", "Washington Wizards"}

def cell_s(row, idx):
    return str(row[idx]).strip() if idx < len(row) and row[idx] is not None else ""

def split_number(val):
    if val is None: return 0
    m = re.search(r"(\d+)", str(val))
    return int(m.group(1)) if m else 0

def parse_qual(val):
    if val is None: return (0, "NEUTRAL", 0)
    s = str(val).strip().upper()
    if not s or "NEUTRAL" in s: return (0, "NEUTRAL", 0)
    m = re.match(r"([+-]?\d+)\s*(HOT|COLD|MOIST|DRY)", s)
    if not m: return (0, "NEUTRAL", 0)
    mag = abs(int(m.group(1)))
    pol = m.group(2)
    signed = mag if pol in ("HOT", "MOIST") else -mag
    return (signed, pol, mag)

def norm_qual_str(val, is_hc=True):
    signed, _, _ = parse_qual(val)
    return fmt_hc(signed) if is_hc else fmt_md(signed)

def fmt_hc(v, space=True):
    sp = " " if space else ""
    if v > 0: return f"{abs(v)}{sp}HOT"
    elif v < 0: return f"{abs(v)}{sp}COLD"
    else: return f"0{sp}NEUTRAL"

def fmt_md(v, space=True):
    sp = " " if space else ""
    if v > 0: return f"{abs(v)}{sp}MOIST"
    elif v < 0: return f"{abs(v)}{sp}DRY"
    else: return f"0{sp}NEUTRAL"

def mod_arcanum(n):
    return ((int(n) - 1) % 22) + 1

def parse_mdy(dt_str):
    s = str(dt_str).strip()
    m1 = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m1:
        return int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
    m2 = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m2:
        return int(m2.group(2)), int(m2.group(3)), int(m2.group(1))
    return 1, 1, 2025

def clean_team_name(label):
    s = re.sub(r"\s*\[.*$", "", str(label or "")).strip()
    return s

def word_element_fawe(text):
    fawe = [0, 0, 0, 0]
    for ch in str(text).upper():
        if ch in LETTER_EL:
            fawe[LETTER_EL[ch]] += 1
    return fawe

def qual_from_fawe(fawe):
    f, a, w, e = fawe
    return (f + a) - (w + e), (a + w) - (f + e)

def elem_to_code(fawe):
    return "".join("1" if x % 2 == 1 else "0" for x in fawe)

def get_season(iso_dt):
    if iso_dt < "2025-08-01": return "2024-25"
    elif iso_dt < "2026-08-01": return "2025-26"
    else: return "2026-27"

SHEET1_HEADERS = [""] * 116
for idx, h in [
    (0, "DAY"), (1, "DATE"), (2, "HOME_TEAM"), (3, "PRIC_CH (AD)"), (4, "quli-deg"),
    (18, "ELE-P"), (28, "ELE-DIGSUM"), (33, "ELE-P-DIGSUM"), (53, "QUALITY-DAY"),
    (66, "ELE-DATE"), (71, "ELE-DATE+P+DIGSUM"), (77, "ELE-DAYWEEK"), (82, "ELE-FINAL"),
    (101, "QULITY-FIN"), (104, "QULITY-DECAN"), (107, "DEC_MODALITY_SUMMARY (AZ)"),
    (108, "GD_CARD_HC (BA)"), (109, "GD_CARD_MD (BB)"), (110, "GD_NUMBER_AG (BC)"),
    (111, "DEC_ELE_P (BD)"), (112, "DEC_GEO_FIG (BE)"), (113, "RULER_HC (BF)"),
    (114, "RULER_MD (BG)"), (115, "RULER_GEO_FIG (BH)")
]:
    SHEET1_HEADERS[idx] = h

SHEET3_HEADERS = [""] * 85
for idx, h in [
    (0, "DAY"), (1, "DATE"), (2, "HOME_TEAM"), (3, "PRIC_CH (AD)"),
    (5, "ELE-P"), (10, "ELE-FINAL"), (15, "ELE-DYN (P+FIN)"), (19, "CODE-DYN"),
    (24, "SUM-DYN"), (26, "QULITY-FIN"), (29, "QULITY-DECAN"), (32, "QULITY-P"),
    (35, "QULITY-DYN"), (38, "Nam-ele"), (43, "QULITY-NAME"), (46, "ELE-TOTAL"),
    (50, "CODE-TOTAL"), (51, "SUM-TOTAL"), (53, "QULITY-TOTAL"), (56, "Ele-Prime2"),
    (60, "CODE-PRIME2"), (62, "QULITY-PRIME2"), (65, "ELE-DECAN-FIN"),
    (70, "QULITY-DECAN-FIN"), (73, "QULITY-GD-CARD"), (76, "QULITY-RULER"),
    (79, "TEAM_VOTES"), (80, "OPP_VOTES"), (81, "VOTE_MARGIN"),
    (82, "PREDICTED_WINNER"), (83, "ACTUAL_WINNER"), (84, "RESULT_STATUS")
]:
    SHEET3_HEADERS[idx] = h

PRED_HEADERS = [
    "GAME_NO", "DAY", "DATE", "SEASON", "HOME_TEAM", "AWAY_TEAM", "SCORE_RESULT",
    "quli-deg (H)", "quli-deg (A)", "QFIN (H)", "QFIN (A)", "QDEC (H)", "QDEC (A)",
    "QTOT (H)", "QTOT (A)", "QPRIME2 (H)", "QPRIME2 (A)", "QDECF (H)", "QDECF (A)",
    "GD_CARD (H)", "GD_CARD (A)", "RULER (H)", "RULER (A)", "QNAME (H)", "QNAME (A)",
    "VM6_SCORE", "PATTERN_TIER", "PREDICTED_WINNER", "ACTUAL_WINNER", "STATUS"
]

def build_team_calc(node_row):
    day_s = cell_s(node_row, 0).upper()
    dt_raw = cell_s(node_row, 1)
    m_v, d_v, y_v = parse_mdy(dt_raw)
    iso_dt = f"{y_v:04d}-{m_v:02d}-{d_v:02d}"
    team_af = cell_s(node_row, 31) or cell_s(node_row, 5)
    pric_ad = cell_s(node_row, 29)

    qdeg_hc_s = norm_qual_str(cell_s(node_row, 26), True)
    qdeg_md_s = norm_qual_str(cell_s(node_row, 27), False)
    qdec_hc_s = norm_qual_str(cell_s(node_row, 48), True)
    qdec_md_s = norm_qual_str(cell_s(node_row, 49), False)

    dec_mod_az = cell_s(node_row, 51)
    gd_hc_ba   = norm_qual_str(cell_s(node_row, 52), True)
    gd_md_bb   = norm_qual_str(cell_s(node_row, 53), False)
    gd_ag_bc   = cell_s(node_row, 54)
    dec_elp_bd = cell_s(node_row, 55)
    dec_fig_be = cell_s(node_row, 56)
    rul_hc_bf  = norm_qual_str(cell_s(node_row, 57), True)
    rul_md_bg  = norm_qual_str(cell_s(node_row, 58), False)
    rul_fig_bh = cell_s(node_row, 59)

    # Sheet1 chain
    h2 = split_number(qdeg_hc_s)
    i2 = split_number(qdeg_md_s)
    k2, l2 = h2 // 10, h2 % 10
    m2, n2 = i2 // 10, i2 % 10
    o2, p2, q2, r2 = [GEO_NAMES.get(min(15, d), "Populus (0000)") for d in (k2, l2, m2, n2)]
    bits_p = [GEO_BITS.get(min(15, d), (0,0,0,0)) for d in (k2, l2, m2, n2)]
    ele_p = [sum(b[j] for b in bits_p) for j in range(4)]

    w2 = DAY_EL_MAP.get(day_s, "Thursday | Jupiter | [Air]")
    x2 = sum(int(c) for c in f"{m_v}{d_v}{y_v}")
    y2, z2 = x2 // 10, x2 % 10
    aa2, ab2 = [GEO_NAMES.get(min(15, d), "Populus (0000)") for d in (y2, z2)]
    bits_dig = [GEO_BITS.get(min(15, d), (0,0,0,0)) for d in (y2, z2)]
    ele_dig = [sum(b[j] for b in bits_dig) for j in range(4)]
    ele_p_dig = [ele_p[j] + ele_dig[j] for j in range(4)]

    ap2, aq2, ar2 = mod_arcanum(m_v), mod_arcanum(d_v), mod_arcanum(y_v)
    as2, p_hc_m, p_md_m = ZOD_MAP[ap2]
    at2, p_hc_d, p_md_d = ZOD_MAP[aq2]
    au2, p_hc_y, p_md_y = ZOD_MAP[ar2]

    av2 = f"{ap2}{p_hc_m}"
    aw2 = f"{aq2}{p_hc_d}"
    ax2 = f"{ar2}{p_hc_y}"
    ay2 = f"{ap2}{p_md_m}"
    az2 = f"{aq2}{p_md_d}"
    ba2 = f"{ar2}{p_md_y}"

    hc_day = (ap2 if p_hc_m=="HOT" else -ap2) + (aq2 if p_hc_d=="HOT" else -aq2) + (ar2 if p_hc_y=="HOT" else -ar2)
    md_day = (ap2 if p_md_m=="MOIST" else -ap2) + (aq2 if p_md_d=="MOIST" else -aq2) + (ar2 if p_md_y=="MOIST" else -ar2)
    bb2 = fmt_hc(hc_day)
    bc2 = fmt_md(md_day)

    bd2, be2 = abs(hc_day), abs(md_day)
    bf2, bg2 = bd2 // 10, bd2 % 10
    bh2, bi2 = be2 // 10, be2 % 10
    bj2, bk2, bl2, bm2 = [GEO_NAMES.get(min(15, d), "Populus (0000)") for d in (bf2, bg2, bh2, bi2)]
    bits_dt = [GEO_BITS.get(min(15, d), (0,0,0,0)) for d in (bf2, bg2, bh2, bi2)]
    ele_dt = [sum(b[j] for b in bits_dt) for j in range(4)]
    ele_dpd = [ele_p_dig[j] + ele_dt[j] for j in range(4)]

    by2 = DAY_CODE_MAP.get(day_s, "0101")
    ele_dw = [int(ch) for ch in by2]
    ele_fin = [ele_dpd[j] + ele_dw[j] for j in range(4)]

    f_v, a_v, w_v, e_v = ele_fin
    cj2, ck2 = f"{f_v} HOT", f"{f_v} DRY"
    cl2, cm2 = f"{a_v} HOT", f"{a_v} MOIST"
    cn2, co2 = f"{w_v} COLD", f"{w_v} MOIST"
    cp2, cq2 = f"{e_v} COLD", f"{e_v} DRY"
    cs2, ct2, cu2, cv2 = f"{f_v+a_v} HOT", f"{a_v+w_v} MOIST", f"{f_v+e_v} DRY", f"{w_v+e_v} COLD"

    qfin_hc, qfin_md = qual_from_fawe(ele_fin)
    cx2, cy2 = fmt_hc(qfin_hc), fmt_md(qfin_md)

    s1_row = [""] * 116
    s1_row[0] = day_s
    s1_row[1] = iso_dt
    s1_row[2] = team_af
    s1_row[3] = pric_ad
    s1_row[4] = qdeg_hc_s
    s1_row[5] = qdeg_md_s
    s1_row[7] = h2; s1_row[8] = i2
    s1_row[10] = k2; s1_row[11] = l2; s1_row[12] = m2; s1_row[13] = n2
    s1_row[14] = o2; s1_row[15] = p2; s1_row[16] = q2; s1_row[17] = r2
    s1_row[18] = f"{ele_p[0]} FIRE"; s1_row[19] = f"{ele_p[1]} AIR"; s1_row[20] = f"{ele_p[2]} WATER"; s1_row[21] = f"{ele_p[3]} EARTH"
    s1_row[22] = w2; s1_row[23] = x2; s1_row[24] = y2; s1_row[25] = z2; s1_row[26] = aa2; s1_row[27] = ab2
    s1_row[28] = f"{ele_dig[0]} FIRE"; s1_row[29] = f"{ele_dig[1]} AIR"; s1_row[30] = f"{ele_dig[2]} WATER"; s1_row[31] = f"{ele_dig[3]} EARTH"
    s1_row[33] = f"{ele_p_dig[0]} FIRE"; s1_row[34] = f"{ele_p_dig[1]} AIR"; s1_row[35] = f"{ele_p_dig[2]} WATER"; s1_row[36] = f"{ele_p_dig[3]} EARTH"
    s1_row[38] = m_v; s1_row[39] = d_v; s1_row[40] = y_v
    s1_row[41] = ap2; s1_row[42] = aq2; s1_row[43] = ar2
    s1_row[44] = as2; s1_row[45] = at2; s1_row[46] = au2
    s1_row[47] = av2; s1_row[48] = aw2; s1_row[49] = ax2
    s1_row[50] = ay2; s1_row[51] = az2; s1_row[52] = ba2
    s1_row[53] = bb2; s1_row[54] = bc2
    s1_row[55] = bd2; s1_row[56] = be2
    s1_row[57] = bf2; s1_row[58] = bg2; s1_row[59] = bh2; s1_row[60] = bi2
    s1_row[61] = bj2; s1_row[62] = bk2; s1_row[63] = bl2; s1_row[64] = bm2
    s1_row[66] = f"{ele_dt[0]} FIRE"; s1_row[67] = f"{ele_dt[1]} AIR"; s1_row[68] = f"{ele_dt[2]} WATER"; s1_row[69] = f"{ele_dt[3]} EARTH"
    s1_row[71] = f"{ele_dpd[0]} FIRE"; s1_row[72] = f"{ele_dpd[1]} AIR"; s1_row[73] = f"{ele_dpd[2]} WATER"; s1_row[74] = f"{ele_dpd[3]} EARTH"
    s1_row[76] = by2
    s1_row[77] = f"{ele_dw[0]} FIRE"; s1_row[78] = f"{ele_dw[1]} AIR"; s1_row[79] = f"{ele_dw[2]} WATER"; s1_row[80] = f"{ele_dw[3]} EARTH"
    s1_row[82] = f"{ele_fin[0]} FIRE"; s1_row[83] = f"{ele_fin[1]} AIR"; s1_row[84] = f"{ele_fin[2]} WATER"; s1_row[85] = f"{ele_fin[3]} EARTH"
    s1_row[87] = cj2; s1_row[88] = ck2; s1_row[89] = cl2; s1_row[90] = cm2
    s1_row[91] = cn2; s1_row[92] = co2; s1_row[93] = cp2; s1_row[94] = cq2
    s1_row[96] = cs2; s1_row[97] = ct2; s1_row[98] = cu2; s1_row[99] = cv2
    s1_row[101] = cx2; s1_row[102] = cy2
    s1_row[104] = qdec_hc_s; s1_row[105] = qdec_md_s
    s1_row[107] = dec_mod_az; s1_row[108] = gd_hc_ba; s1_row[109] = gd_md_bb; s1_row[110] = gd_ag_bc
    s1_row[111] = dec_elp_bd; s1_row[112] = dec_fig_be; s1_row[113] = rul_hc_bf; s1_row[114] = rul_md_bg; s1_row[115] = rul_fig_bh

    # Sheet3 chain
    ele_dyn = [ele_p[j] + ele_fin[j] for j in range(4)]
    code_dyn = elem_to_code(ele_dyn)
    sum_dyn = sum(ele_dyn)
    qp_hc, qp_md = qual_from_fawe(ele_p)
    qdyn_hc, qdyn_md = qual_from_fawe(ele_dyn)

    t_clean = clean_team_name(team_af)
    nam_fawe = word_element_fawe(t_clean)
    qnam_hc, qnam_md = qual_from_fawe(nam_fawe)

    ele_tot = [ele_dyn[j] + nam_fawe[j] for j in range(4)]
    code_tot = elem_to_code(ele_tot)
    sum_tot = sum(ele_tot)
    qtot_hc, qtot_md = qual_from_fawe(ele_tot)

    p2_digits = []
    for v in ele_tot:
        p2_digits.extend([v // 10, v % 10])
    bits_p2 = [GEO_BITS.get(min(15, d), (0,0,0,0)) for d in p2_digits]
    ele_p2 = [sum(b[j] for b in bits_p2) for j in range(4)]
    code_p2 = elem_to_code(ele_p2)
    qp2_hc, qp2_md = qual_from_fawe(ele_p2)

    qdec_hc_v = parse_qual(qdec_hc_s)[0]
    qdec_md_v = parse_qual(qdec_md_s)[0]
    dec_d = [abs(qdec_hc_v)//10, abs(qdec_hc_v)%10, abs(qdec_md_v)//10, abs(qdec_md_v)%10]
    bits_dec = [GEO_BITS.get(min(15, d), (0,0,0,0)) for d in dec_d]
    ele_dec_p = [sum(b[j] for b in bits_dec) for j in range(4)]
    ele_decf = [ele_dec_p[j] + ele_dig[j] + ele_dt[j] + ele_dw[j] for j in range(4)]
    qdecf_hc, qdecf_md = qual_from_fawe(ele_decf)

    gd_hc_v, gd_md_v = parse_qual(gd_hc_ba)[0], parse_qual(gd_md_bb)[0]
    rul_hc_v, rul_md_v = parse_qual(rul_hc_bf)[0], parse_qual(rul_md_bg)[0]
    qdeg_hc_v, qdeg_md_v = parse_qual(qdeg_hc_s)[0], parse_qual(qdeg_md_s)[0]

    s3_row = [""] * 85
    s3_row[0] = day_s; s3_row[1] = iso_dt; s3_row[2] = team_af; s3_row[3] = pric_ad
    s3_row[5] = f"{ele_p[0]} FIRE"; s3_row[6] = f"{ele_p[1]} AIR"; s3_row[7] = f"{ele_p[2]} WATER"; s3_row[8] = f"{ele_p[3]} EARTH"
    s3_row[10] = f"{ele_fin[0]} FIRE"; s3_row[11] = f"{ele_fin[1]} AIR"; s3_row[12] = f"{ele_fin[2]} WATER"; s3_row[13] = f"{ele_fin[3]} EARTH"
    s3_row[15] = f"{ele_dyn[0]} FIRE"; s3_row[16] = f"{ele_dyn[1]} AIR"; s3_row[17] = f"{ele_dyn[2]} WATER"; s3_row[18] = f"{ele_dyn[3]} EARTH"
    s3_row[19] = code_dyn
    s3_row[20] = ele_dyn[0]; s3_row[21] = ele_dyn[1]; s3_row[22] = ele_dyn[2]; s3_row[23] = ele_dyn[3]; s3_row[24] = sum_dyn
    s3_row[26] = cx2; s3_row[27] = cy2
    s3_row[29] = qdec_hc_s; s3_row[30] = qdec_md_s
    s3_row[32] = fmt_hc(qp_hc); s3_row[33] = fmt_md(qp_md)
    s3_row[35] = fmt_hc(qdyn_hc); s3_row[36] = fmt_md(qdyn_md)
    s3_row[38] = f"{nam_fawe[0]} FIRE"; s3_row[39] = f"{nam_fawe[1]} AIR"; s3_row[40] = f"{nam_fawe[2]} WATER"; s3_row[41] = f"{nam_fawe[3]} EARTH"
    s3_row[43] = fmt_hc(qnam_hc); s3_row[44] = fmt_md(qnam_md)
    s3_row[46] = f"{ele_tot[0]} FIRE"; s3_row[47] = f"{ele_tot[1]} AIR"; s3_row[48] = f"{ele_tot[2]} WATER"; s3_row[49] = f"{ele_tot[3]} EARTH"
    s3_row[50] = code_tot; s3_row[51] = sum_tot
    s3_row[53] = fmt_hc(qtot_hc); s3_row[54] = fmt_md(qtot_md)
    s3_row[56] = f"{ele_p2[0]} FIRE"; s3_row[57] = f"{ele_p2[1]} AIR"; s3_row[58] = f"{ele_p2[2]} WATER"; s3_row[59] = f"{ele_p2[3]} EARTH"
    s3_row[60] = code_p2
    s3_row[62] = fmt_hc(qp2_hc); s3_row[63] = fmt_md(qp2_md)
    s3_row[65] = f"{ele_decf[0]} FIRE"; s3_row[66] = f"{ele_decf[1]} AIR"; s3_row[67] = f"{ele_decf[2]} WATER"; s3_row[68] = f"{ele_decf[3]} EARTH"
    s3_row[70] = fmt_hc(qdecf_hc); s3_row[71] = fmt_md(qdecf_md)
    s3_row[73] = gd_hc_ba; s3_row[74] = gd_md_bb
    s3_row[76] = rul_hc_bf; s3_row[77] = rul_md_bg

    meta = {
        "day": day_s, "iso_dt": iso_dt, "ym": iso_dt[:7], "season": get_season(iso_dt),
        "team_clean": t_clean, "team_af": team_af, "pric_ad": pric_ad,
        "qdeg": (qdeg_hc_v, qdeg_md_v),
        "qfin": (qfin_hc, qfin_md),
        "qdec": (qdec_hc_v, qdec_md_v),
        "qdecf": (qdecf_hc, qdecf_md),
        "qtot": (qtot_hc, qtot_md),
        "qp2": (qp2_hc, qp2_md),
        "gd": (gd_hc_v, gd_md_v),
        "rul": (rul_hc_v, rul_md_v),
        "qnam": (qnam_hc, qnam_md),
    }
    return s1_row, s3_row, meta

def write_chunked(ws, rows, chunk_size=2600):
    ws.clear()
    total = len(rows)
    for i in range(0, total, chunk_size):
        chunk = rows[i:i+chunk_size]
        ws.update(range_name=f"A{i+1}", values=chunk, value_input_option="RAW")

def main():
    t0 = time.time()
    print("[Step 4] Reading NBA-Result-Degree :: Node_Output from Google Sheets...")
    ss_rd = open_sheet(SS_RD)
    ws_node = ss_rd.worksheet("Node_Output")
    node_rows = ws_node.get_all_values()
    if len(node_rows) <= 1:
        print("[Step 4] Node_Output is empty!")
        return

    data_rows = [r for r in node_rows[1:] if r and str(r[0]).strip() != ""]
    print(f"[Step 4] Read {len(data_rows)} team rows ({len(data_rows)//2} paired games) from Node_Output.")

    sheet1_rows = [SHEET1_HEADERS]
    sheet3_rows = [SHEET3_HEADERS]
    pred_rows   = [PRED_HEADERS]

    for i in range(0, len(data_rows) - 1, 2):
        s1_h, s3_h, mh = build_team_calc(data_rows[i])
        s1_a, s3_a, ma = build_team_calc(data_rows[i+1])
        game_no = (i // 2) + 1

        # 6 Core Rules
        r1 = 1 if abs(mh["qdec"][1]) < abs(ma["qdec"][1]) else (-1 if abs(mh["qdec"][1]) > abs(ma["qdec"][1]) else 0)
        r2 = 1 if mh["gd"][1] < ma["gd"][1] else (-1 if mh["gd"][1] > ma["gd"][1] else 0)
        r3 = 1 if abs(mh["qdecf"][0]) < abs(ma["qdecf"][0]) else (-1 if abs(mh["qdecf"][0]) > abs(ma["qdecf"][0]) else 0)
        r4 = 1 if (abs(mh["qfin"][0])+abs(mh["qfin"][1])) < (abs(ma["qfin"][0])+abs(ma["qfin"][1])) else (-1 if (abs(mh["qfin"][0])+abs(mh["qfin"][1])) > (abs(ma["qfin"][0])+abs(ma["qfin"][1])) else 0)
        r5 = 1 if mh["qtot"][1] < ma["qtot"][1] else (-1 if mh["qtot"][1] > ma["qtot"][1] else 0)
        r6 = 1 if (abs(mh["qnam"][0])+abs(mh["qnam"][1])) > (abs(ma["qnam"][0])+abs(ma["qnam"][1])) else (-1 if (abs(mh["qnam"][0])+abs(mh["qnam"][1])) < (abs(ma["qnam"][0])+abs(ma["qnam"][1])) else 0)

        votes = [r1, r2, r3, r4, r5, r6]
        h_votes = sum(1 for v in votes if v > 0)
        a_votes = sum(1 for v in votes if v < 0)
        vm6 = h_votes - a_votes
        pred_home = (vm6 >= 0)
        pred_winner = mh["team_clean"] if pred_home else ma["team_clean"]

        # Parse actual winner from PRIC_CH (AD)
        pch = mh["pric_ad"]
        m_win = re.search(r"\(([+-]?\d+)\s*\|\s*WIN:\s*([^)]+)\)", pch)
        if m_win and int(m_win.group(1)) != 0:
            actual_winner = m_win.group(2).strip()
            home_won = int(m_win.group(1)) > 0
            status = "WIN" if (pred_home == home_won) else "LOSS"
        else:
            actual_winner = "PENDING"
            status = "PENDING"

        name_diff = (abs(mh["qnam"][0])+abs(mh["qnam"][1])) - (abs(ma["qnam"][0])+abs(ma["qnam"][1]))
        c_qdeg_md = abs(mh["qdeg"][1]) <= abs(ma["qdeg"][1])
        c_qdeg_hc = abs(mh["qdeg"][0]) <= abs(ma["qdeg"][0])
        c_qtot_hc = mh["qtot"][0] <= ma["qtot"][0]
        c_rul_hc  = mh["rul"][0] <= ma["rul"][0]
        c_rul_md  = mh["rul"][1] <= ma["rul"][1]

        is_base_137  = (vm6 >= 4) and (mh["team_clean"] not in TRAP_TEAMS)
        is_name_80   = is_base_137 and (name_diff >= 4)
        is_elem_80   = is_base_137 and ((int(c_qdeg_md) + int(c_qtot_hc) + int(c_rul_hc)) >= 2)
        is_qdeg_80   = is_base_137 and c_qdeg_md and c_qdeg_hc
        is_golden_83 = is_base_137 and (name_diff >= 4) and (c_qdeg_md or c_rul_md)

        if is_golden_83:
            tier = "TIER 1: GOLDEN (82.8%)"
        elif is_elem_80 or is_qdeg_80:
            tier = "TIER 2: BALANCE (80.0%)"
        elif is_name_80:
            tier = "TIER 2B: NAME>=4 (79.8%)"
        elif is_base_137:
            tier = "TIER 3: HIGH VM>=4 (71.5%)"
        elif abs(vm6) >= 2:
            tier = "TIER 4: MODERATE (|VM|>=2)"
        else:
            tier = "TIER 5: STANDARD"

        s3_h[79] = h_votes; s3_h[80] = a_votes; s3_h[81] = abs(vm6); s3_h[82] = pred_winner; s3_h[83] = actual_winner; s3_h[84] = status
        s3_a[79] = a_votes; s3_a[80] = h_votes; s3_a[81] = abs(vm6); s3_a[82] = pred_winner; s3_a[83] = actual_winner; s3_a[84] = status

        sheet1_rows.append(s1_h)
        sheet1_rows.append(s1_a)
        sheet3_rows.append(s3_h)
        sheet3_rows.append(s3_a)

        pred_rows.append([
            game_no, mh["day"], mh["iso_dt"], mh["season"], mh["team_clean"], ma["team_clean"], pch,
            f"{s1_h[4]} | {s1_h[5]}", f"{s1_a[4]} | {s1_a[5]}",
            f"{s3_h[26]} | {s3_h[27]}", f"{s3_a[26]} | {s3_a[27]}",
            f"{s3_h[29]} | {s3_h[30]}", f"{s3_a[29]} | {s3_a[30]}",
            f"{s3_h[53]} | {s3_h[54]}", f"{s3_a[53]} | {s3_a[54]}",
            f"{s3_h[62]} | {s3_h[63]}", f"{s3_a[62]} | {s3_a[63]}",
            f"{s3_h[70]} | {s3_h[71]}", f"{s3_a[70]} | {s3_a[71]}",
            f"{s3_h[73]} | {s3_h[74]}", f"{s3_a[73]} | {s3_a[74]}",
            f"{s3_h[76]} | {s3_h[77]}", f"{s3_a[76]} | {s3_a[77]}",
            f"{s3_h[43]} | {s3_h[44]}", f"{s3_a[43]} | {s3_a[44]}",
            vm6, tier, pred_winner, actual_winner, status
        ])

    print(f"[Step 4] Computed {len(sheet1_rows)-1} rows for Sheet1 & Sheet3, and {len(pred_rows)-1} games for Game_Predictions.")
    ss_calc = open_sheet(SS_CALC)
    print("[Step 4] Writing NBA-Calculation :: Sheet1 (116 cols)...")
    write_chunked(ss_calc.worksheet("Sheet1"), sheet1_rows, chunk_size=2600)
    print("[Step 4] Writing NBA-Calculation :: Sheet3 (85 cols)...")
    write_chunked(ss_calc.worksheet("Sheet3"), sheet3_rows, chunk_size=2600)
    print("[Step 4] Writing NBA-Calculation :: Game_Predictions (30 cols)...")
    write_chunked(ss_calc.worksheet("Game_Predictions"), pred_rows, chunk_size=2600)
    print("[Step 4] Writing NBA-Result-Degree :: Game_Predictions (30 cols)...")
    write_chunked(ss_rd.worksheet("Game_Predictions"), pred_rows, chunk_size=2600)

    print(f"__ROWS_WRITTEN__ {len(sheet1_rows)-1}")
    print(f"[Step 4] Successfully built NBA-Calculation (Sheet1, Sheet3, Game_Predictions) in {time.time()-t0:.2f}s.")

if __name__ == "__main__":
    main()
