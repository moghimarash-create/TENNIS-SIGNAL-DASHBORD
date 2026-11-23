import { useState, useEffect, useCallback, useMemo, Fragment } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Loader2, RefreshCw } from "lucide-react";

// ---------------------------------------------------------------------------
// NHL 2010-2027 ELEMENTAL TWINS (DEG1 = 88 FIXED), DUAL-GEO + DECAN & KALSHI
// Exact 1-to-1 Visual & Interactive Layout Match of NbaWinnerPredictorPanel
// ---------------------------------------------------------------------------

const NBA_TEAM_KALSHI_MAP: Record<string, string> = {
  "atlanta hawks": "ATL",
  "boston celtics": "BOS",
  "brooklyn nets": "BKN",
  "charlotte hornets": "CHA",
  "chicago bulls": "CHI",
  "cleveland cavaliers": "CLE",
  "dallas mavericks": "DAL",
  "denver nuggets": "DEN",
  "detroit pistons": "DET",
  "golden state warriors": "GSW",
  "houston rockets": "HOU",
  "indiana pacers": "IND",
  "los angeles clippers": "LAC",
  "la clippers": "LAC",
  "los angeles lakers": "LAL",
  "memphis grizzlies": "MEM",
  "miami heat": "MIA",
  "milwaukee bucks": "MIL",
  "minnesota timberwolves": "MIN",
  "new orleans pelicans": "NOP",
  "new york knicks": "NYK",
  "oklahoma city thunder": "OKC",
  "orlando magic": "ORL",
  "philadelphia 76ers": "PHI",
  "phoenix suns": "PHX",
  "portland trail blazers": "POR",
  "sacramento kings": "SAC",
  "san antonio spurs": "SAS",
  "toronto raptors": "TOR",
  "utah jazz": "UTA",
  "washington wizards": "WAS",
};

function elemCodeFromFinal4(el12: string[]): string {
  if (!el12 || el12.length < 8) return "";
  return el12
    .slice(4, 8)
    .map((s) => {
      const n = parseInt(String(s ?? "").trim().split(/\s+/)[0] ?? "0", 10);
      return Number.isFinite(n) && Math.abs(n) % 2 === 1 ? "1" : "0";
    })
    .join("");
}

type NbaGamePred = {
  n: number;
  day: string;
  d: string;
  ym: string;
  s: string;
  h: string;
  a: string;
  sc: string;
  pw: string;
  aw: string;
  st: "WIN" | "LOSS" | "PENDING";
  ph: boolean;
  vm6: number;
  v: number[];
  nd: number;
  b137: boolean;
  n80: boolean;
  e80: boolean;
  q80: boolean;
  g83: boolean;
  tier: string;
  qdeg: [string, string];
  qfin: [string, string];
  qdec: [string, string];
  qdecf: [string, string];
  qtot: [string, string];
  qp2: [string, string];
  gd: [string, string];
  rul: [string, string];
  qnam: [string, string];
  cf: number[];
  // 5-Method Fusion fields:
  mv?: [number, number, number, number, number];
  f30?: number;
  a25?: number;
  ag5?: number;
  fpw?: string;
  fst?: "WIN" | "LOSS" | "PENDING";
  ftier?: string;
  f16?: boolean;
  f14?: boolean;
  f12?: boolean;
  fa14?: boolean;
  astro9?: boolean;
  fa8?: boolean;
  // 2010-2026 Elemental Twins fields (GOLD-FORMULA-PRIORITY engine):
  twMode?: string;
  twVotes?: string;
  twPct?: string;
  twWin?: string;
  f5Full?: string;
  f5Loo?: string;
  tp?: [number, number, number];
  twAgree?: boolean;
  twPath?: string;
  twPeers?: string[];
  twDiamond?: boolean;
  twGolden?: boolean;
  twVip?: boolean;
  twActive?: boolean;
  twF5_5?: boolean;
  twF5_4?: boolean;
  h_12?: string[];
  h_geo?: string;
  h_geo_dyn?: string;
  h_geo_tab?: string;
  a_12?: string[];
  a_geo?: string;
  a_geo_dyn?: string;
  a_geo_tab?: string;
  hc?: string;
  ac?: string;
  hp?: number;
  ap?: number;
  done?: boolean;
  hw?: boolean | null;
  venue?: string;
  sh_d?: string;
  sh_m?: string;
  deg?: number[];
  f1?: boolean;
  s_new?: boolean;
  vip?: boolean;
  s_a1?: boolean;
  a1_veto?: boolean;
  new_veto?: boolean;
  chan?: string;
  twins?: [string, string, string, number, number, number][];
  idx3?: {
    st: number[];
    gf: number[];
    gd: number[];
    gt?: number[];
    tw: number[];
    vh: number;
    va: number;
    nat: number;
    minD: number;
  };
  f1_idx?: boolean;
  f1_guard?: boolean;
  f1_wtp?: boolean;
  vip_idx3?: boolean;
  idx_rescue?: boolean;
  f1_union?: boolean;
  f1_wtp_day?: boolean;
  vip_idx3_day?: boolean;
  f1_union_day?: boolean;
  sys_win?: string;
  b2b_tag?: string;
  is_nat?: boolean;
  trap_tag?: string;
  tier_pct?: number;
  max_buy_c?: number;
  wtp?: {
    mon: string;
    htp: number;
    atp: number;
    dtp: number;
    hrk: number;
    ark: number;
    hwl: string;
    awl: string;
    hpct?: number;
    apct?: number;
    hel?: string;
    ael?: string;
    l5h?: number;
    hodds?: number;
    aodds?: number;
    mel?: string;
  };
  wtp_day?: {
    mon: string;
    htp: number;
    atp: number;
    dtp: number;
    hrk: number;
    ark: number;
    hwl: string;
    awl: string;
    hpct?: number;
    apct?: number;
    hel?: string;
    ael?: string;
    l5h?: number;
    hodds?: number;
    aodds?: number;
    mel?: string;
  };
};

type HistGameRow = {
  d: string;
  day: string;
  s: string;
  h: string;
  a: string;
  hp: number;
  ap: number;
  mg: number;
  h12: string[];
  hGeo: string;
  a12: string[];
  aGeo: string;
  f30: number;
  hGeoDyn?: string;
  aGeoDyn?: string;
  hGeoTab?: string;
  aGeoTab?: string;
};

type ManualFilterState = {
  cols: Record<number, string>; // 0..11 -> selected value or "ALL"
  geo: string;                  // "ALL" or 4-bit code (GEO-FIN / GEO-DYN)
  geoTab?: string;              // "ALL" or 4-bit Daily Standings Geomantic Figure (GEO-TAB)
  geoKind?: "fin" | "dyn";      // per-game GEO-FIN vs GEO-DYN channel
  modeLabel?: string;
  pathLog?: string[];
  stepSummary?: string;
  geoSummary?: string;
};

type PoolNumIndex = {
  hw: number;
  aw: number;
  idxH: number;
  idxA: number;
  delta: number;
  effDelta: number;
  scoreH: number;
  scoreA: number;
  scoreDelta: number;
  formulaH: string;
  formulaA: string;
  cappedH: boolean;
  cappedA: boolean;
  winner: "HOME" | "AWAY" | "TIE";
};

function computePoolNumIndex(rows: HistGameRow[]): PoolNumIndex {
  const rawH = rows.filter((r) => r.mg > 0).map((r) => Math.abs(r.mg));
  const rawA = rows.filter((r) => r.mg < 0).map((r) => Math.abs(r.mg));
  const capH = rawH.map((m) => Math.min(5, Math.max(1, Math.ceil(m / 4))));
  const capA = rawA.map((m) => Math.min(5, Math.max(1, Math.ceil(m / 4))));
  const hw = capH.length;
  const aw = capA.length;
  const cappedH = rawH.some((m) => m > 20);
  const cappedA = rawA.some((m) => m > 20);

  let idxH = 0;
  let formulaH = "0";
  if (hw === 1) {
    idxH = capH[0];
    formulaH = `1×(+${capH[0]})${cappedH ? "[≤5]" : ""}`;
  } else if (hw >= 2) {
    const mn = Math.min(...capH);
    const mx = Math.max(...capH);
    idxH = mx + mn;
    formulaH = `${mn}+${mx}${cappedH ? "[≤5]" : ""}`;
  }

  let idxA = 0;
  let formulaA = "0";
  if (aw === 1) {
    idxA = capA[0];
    formulaA = `1×(-${capA[0]})${cappedA ? "[≤5]" : ""}`;
  } else if (aw >= 2) {
    const mn = Math.min(...capA);
    const mx = Math.max(...capA);
    idxA = mx + mn;
    formulaA = `(-${mx})+(-${mn})${cappedA ? "[≤5]" : ""}`;
  }

  const delta = idxH - idxA;
  const scoreH = 2 * hw + idxH;
  const scoreA = 2 * aw + idxA;
  const scoreDelta = scoreH - scoreA;
  const effDelta =
    delta > 0 && scoreDelta > 0
      ? delta
      : delta < 0 && scoreDelta < 0
        ? delta
        : delta === 0 && Math.abs(scoreDelta) >= 2
          ? scoreDelta > 0
            ? 1
            : -1
          : 0;
  const winner: "HOME" | "AWAY" | "TIE" = effDelta > 0 ? "HOME" : effDelta < 0 ? "AWAY" : "TIE";

  return {
    hw,
    aw,
    idxH,
    idxA,
    delta,
    effDelta,
    scoreH,
    scoreA,
    scoreDelta,
    formulaH,
    formulaA,
    cappedH,
    cappedA,
    winner,
  };
}

const MANUAL_COL_META: { idx: number; key: string; group: string; sub: string }[] = [
  { idx: 0,  key: "PRIM-1",  group: "ELE-DYN (P+FIN)", sub: "FIRE" },
  { idx: 1,  key: "PRIM-2",  group: "ELE-DYN (P+FIN)", sub: "AIR" },
  { idx: 2,  key: "PRIM-3",  group: "ELE-DYN (P+FIN)", sub: "WATER" },
  { idx: 3,  key: "PRIM-4",  group: "ELE-DYN (P+FIN)", sub: "EARTH" },
  { idx: 4,  key: "FINAL-1", group: "ELE-FINAL",       sub: "FIRE" },
  { idx: 5,  key: "FINAL-2", group: "ELE-FINAL",       sub: "AIR" },
  { idx: 6,  key: "FINAL-3", group: "ELE-FINAL",       sub: "WATER" },
  { idx: 7,  key: "FINAL-4", group: "ELE-FINAL",       sub: "EARTH" },
  { idx: 8,  key: "ELE-P-1", group: "ELE-P",           sub: "FIRE" },
  { idx: 9,  key: "ELE-P-2", group: "ELE-P",           sub: "AIR" },
  { idx: 10, key: "ELE-P-3", group: "ELE-P",           sub: "WATER" },
  { idx: 11, key: "ELE-P-4", group: "ELE-P",           sub: "EARTH" },
];

function decodeGeoTabFa(code: string): string {
  if (!code || code.length < 4) return "شکل رمل جدول روزانه";
  const tierFa = (b1: string, b2: string) =>
    b1 === "1" ? "۱۰ تیم اول (#1-10)" : b2 === "1" ? "میانه جدول (#11-20)" : "۱۰ تیم آخر (#21-30)";
  return `میزبان: ${tierFa(code[0], code[1])} | میهمان: ${tierFa(code[2], code[3])}`;
}

function computeAutoFilterState(
  targetEl12: string[],
  targetGeo: string,
  dayPool: HistGameRow[],
  persp: "home" | "away",
  geoFirst: boolean,
  geoKind: "fin" | "dyn" | "tab" = "fin"
): {
  state: ManualFilterState;
  pool: HistGameRow[];
  unslicedPool: HistGameRow[];
  isNatural57: boolean;
  hw: number;
  aw: number;
  pct: number;
  mv: number;
  sumStr: string;
} {
  let pool = [...dayPool];
  const cols: Record<number, string> = {};
  let geo = "ALL";
  let geoTab = "ALL";
  const pathLog: string[] = [];

  const getEl12 = (r: HistGameRow) => (persp === "home" ? r.h12 : r.a12);
  const getGeo = (r: HistGameRow) =>
    geoKind === "tab"
      ? persp === "home"
        ? r.hGeoTab ?? ""
        : r.aGeoTab ?? ""
      : persp === "home"
        ? geoKind === "dyn"
          ? r.hGeoDyn ?? r.hGeo
          : r.hGeo
        : geoKind === "dyn"
          ? r.aGeoDyn ?? r.aGeo
          : r.aGeo;

  const geoLabel = geoKind === "tab" ? "GEO-TAB" : geoKind === "dyn" ? "GEO-DYN" : "GEO-FIN";

  if (geoFirst && targetGeo) {
    const nxtGeo = pool.filter((r) => getGeo(r) === targetGeo);
    if (nxtGeo.length >= 5) {
      pool = nxtGeo;
      if (geoKind === "tab") geoTab = targetGeo;
      else geo = targetGeo;
      pathLog.push(`${geoLabel}=${targetGeo} (${pool.length})`);
    }
  }

  // STRICT 5-TO-7 ROWS RULE:
  // Stop immediately when pool has 5 to 7 rows (5 <= pool.length <= 7), and never narrow below 5 rows (cnt >= 5).
  while (pool.length > 7) {
    let bestC: number | null = null;
    let bestCnt = -1;
    let bestNxt: HistGameRow[] = [];

    for (let c = 0; c < 12; c++) {
      if (cols[c] && cols[c] !== "ALL") continue;
      const tVal = targetEl12[c];
      if (!tVal) continue;
      const nxt = pool.filter((r) => getEl12(r)[c] === tVal);
      const cnt = nxt.length;
      if (cnt >= 5 && cnt < pool.length && cnt > bestCnt) {
        bestCnt = cnt;
        bestC = c;
        bestNxt = nxt;
      }
    }

    if (bestC === null) break;
    cols[bestC] = targetEl12[bestC];
    pool = bestNxt;
    pathLog.push(`${MANUAL_COL_META[bestC].key}=${targetEl12[bestC]} (${pool.length})`);
    if (pool.length >= 5 && pool.length <= 7) break;
  }

  if (!geoFirst && geo === "ALL" && geoTab === "ALL" && targetGeo && pool.length > 7) {
    const nxtGeo = pool.filter((r) => getGeo(r) === targetGeo);
    if (nxtGeo.length >= 5 && nxtGeo.length <= 7) {
      pool = nxtGeo;
      if (geoKind === "tab") geoTab = targetGeo;
      else geo = targetGeo;
      pathLog.push(`${geoLabel}=${targetGeo} (${pool.length})`);
    }
  }

  const unslicedPool = [...pool];
  const isNatural57 = unslicedPool.length >= 5 && unslicedPool.length <= 7;

  if (pool.length > 7) {
    pool = pool.slice(-7);
    pathLog.push(`RANK_CAP(7/${unslicedPool.length})`);
  }

  const hw = pool.filter((r) => r.mg > 0).length;
  const aw = pool.filter((r) => r.mg < 0).length;
  const tot = Math.max(1, hw + aw);
  const pct = Math.round((Math.max(hw, aw) / tot) * 1000) / 10;
  const mv = Math.abs(hw - aw);
  const sumStr = `${hw}H-${aw}A (${pct}%)`;

  return {
    state: {
      cols,
      geo,
      geoTab,
      geoKind: geoKind === "tab" ? "fin" : geoKind,
      modeLabel: geoFirst
        ? geoKind === "tab"
          ? "اول شکل رمل جدول روزانه (GEO-TAB)"
          : geoKind === "dyn"
            ? "اول شکل رمل پویا (GEO-DYN)"
            : "اول شکل رمل اصلاحی (GEO-FIN)"
        : "گام‌به‌گام بیشترین تکرار (STEP)",
      pathLog,
    },
    pool,
    unslicedPool,
    isNatural57,
    hw,
    aw,
    pct,
    mv,
    sumStr,
  };
}

function computeThreeChannelIndex(
  t12: string[],
  tGeoFin: string,
  tGeoDyn: string,
  dayPool: HistGameRow[],
  persp: "home" | "away",
  tGeoTab: string = ""
) {
  const step = computeAutoFilterState(t12, tGeoFin, dayPool, persp, false, "fin");
  const geoFin = computeAutoFilterState(t12, tGeoFin, dayPool, persp, true, "fin");
  const geoDyn = computeAutoFilterState(t12, tGeoDyn, dayPool, persp, true, "dyn");
  const geoTab = computeAutoFilterState(t12, tGeoTab, dayPool, persp, true, "tab");

  const idxSt = computePoolNumIndex(step.pool);
  const idxGf = computePoolNumIndex(geoFin.pool);
  const idxGd = computePoolNumIndex(geoDyn.pool);
  const idxGt = computePoolNumIndex(geoTab.pool);

  const chList = [idxSt, idxGf, idxGd, idxGt];
  const votesHome = chList.filter((c) => c.effDelta > 0).length;
  const votesAway = chList.filter((c) => c.effDelta < 0).length;
  const natCount = [step, geoFin, geoDyn, geoTab].filter((c) => c.isNatural57).length;
  const minDelta = Math.min(idxSt.effDelta, idxGf.effDelta, idxGd.effDelta, idxGt.effDelta);
  const maxDelta = Math.max(idxSt.effDelta, idxGf.effDelta, idxGd.effDelta, idxGt.effDelta);
  const totalScoreDelta = idxSt.scoreDelta + idxGf.scoreDelta + idxGd.scoreDelta + idxGt.scoreDelta;
  const consensusWinner: "HOME" | "AWAY" | "TIE" =
    votesHome > votesAway ? "HOME" : votesAway > votesHome ? "AWAY" : "TIE";

  const avgDelta = Math.round(((idxSt.effDelta + idxGf.effDelta + idxGd.effDelta + idxGt.effDelta) / 4) * 10) / 10;
  const unanimous = votesHome === 4 || votesAway === 4;

  return {
    step,
    geoFin,
    geoDyn,
    geoTab,
    idxSt,
    idxGf,
    idxGd,
    idxGt,
    votesHome,
    votesAway,
    homeVotes: votesHome,
    awayVotes: votesAway,
    natCount,
    minDelta,
    maxDelta,
    avgDelta,
    unanimous,
    totalScoreDelta,
    consensusWinner,
    favSide: consensusWinner,
  };
}

type EngineMode = "manual" | "twins" | "fusion" | "single";
type TwinPatternKey =
  | "twVipIdx3"
  | "twF1Wtp"
  | "twF1Guard"
  | "twF1Idx"
  | "twF1Union"
  | "twVipDual"
  | "twF1"
  | "twSNew"
  | "twF1Agree"
  | "twSA1"
  | "tall";
type FusionPatternKey = "f12" | "f8" | "f6" | "fa10" | "fall";
type SinglePatternKey = "s1_vip" | "s1_f1" | "s1_guard" | "all";

const TWIN_PATTERN_DEFS: {
  key: TwinPatternKey;
  titleFa: string;
  titleEn: string;
  formulaFa: string;
}[] = [
  {
    key: "twVipIdx3",
    titleFa: "سطح ویژه عنصر آتش FIRE ضریب Log5 یا اجماع ۴ از ۴ شاخص تقویت‌شده Δ+S",
    titleEn: "VIP FIRE Odds-Element (Log5 ≥ 58%) or 4/4 Δ+S Index Consensus",
    formulaFa: "سیگنال‌های تمیز سیستم نهایی NBA (ATP: 121 • WTA: 47) که در لایه ضریب جدول به عنصر آتش FIRE (≥۵۸٪) می‌رسند یا اجماع ۴ از ۴ شاخص تقویت‌شده Δ+S در هر ۴ کانال مستقل (STEP، GEO-FIN، GEO-DYN، GEO-TAB) با Δmin≥2 دارند (سقف خرید تا ۷۶¢)",
  },
  {
    key: "twF1Wtp",
    titleFa: "سیستم نهایی NBA + ۴ کانال تقویت‌شده Δ+S + شکل رملی روزانه جدول GEO-TAB + ضریب Log5",
    titleEn: "NBA Final System + 4-Channel Δ+S + GEO-TAB Standings Figure + Log5 Element",
    formulaFa: "همزاد ۵ تا ۷ ردیف (≥۷۱٪ هم‌جهت با Fusion 30) + شاخص ۴ کاناله تقویت‌شده Δ+S (شامل کانال ۴ شکل رملی ۴ خطی روزانه جدول GEO-TAB و سپر پلی‌آف) + حفظ عناصر FIRE/AIR/WATER و اخراج فقط EARTH (<۴۴٪)",
  },
  {
    key: "twF1Guard",
    titleFa: "نگهبان ۴ تله درونی و خستگی B2B بدون فیلتر جدول هفتگی (۷۷٫۴٪ فصل جاری)",
    titleEn: "NBA Internal Trap Guard & B2B Fatigue Only",
    formulaFa: "حذف ۴ تله ثابت درونی و برنامه‌ای NBA (میهمان ضعیف، مخالفت شاخص ۳ کاناله، خستگی Back-to-Back تیم منتخب، و برش CAP7 بدون پشتوانه ۳/۳ شاخص) بدون اعمال فیلتر جدول هفتگی",
  },
  {
    key: "twF1Idx",
    titleFa: "تلفیق پایه همزاد + شاخص عددی پایه بدون نگهبان تله (Idx هم‌جهت)",
    titleEn: "NBA Base Combo + Numerical Index Filter",
    formulaFa: "واجد شرایط همزاد ۵ تا ۷ ردیف (DEG1=53 • ≥۷۱٪) هم‌جهت با Fusion 30 به شرط هم‌جهت بودن شاخص عددی استخر (واحد ۴ امتیازی بسکتبال با سقف ۵ واحد برای حذف بردهای پرت)",
  },
  {
    key: "twF1Union",
    titleFa: "اتحاد سیستم نهایی NBA + نجات شاخص ۳ کاناله (اجماع ۳/۳ + جدول هفتگی)",
    titleEn: "NBA Final System UNION 3-Channel Index Rescue",
    formulaFa: "اتحاد سیستم نهایی NBA با بازی‌های دارای اجماع ۳ از ۳ شاخص عددی مستقل (STEP + GEO-FIN + GEO-DYN با Δmin≥1) بدون تله درونی و با تایید جدول هفتگی (ΔTP > -8)",
  },
  {
    key: "tall",
    titleFa: "۶. کل ۲٬۶۴۲ بازی NBA (۲۰۲۴ تا ۲۰۲۷) + همزادهای ۲۰۱۰–۲۰۲۶",
    titleEn: "All 2,642 NBA Games (2024–2027)",
    formulaFa: "نمایش تمام بازی‌های NBA در سه فصل ۲۰۲۴–۲۰۲۵، ۲۰۲۵–۲۰۲۶ و ۲۰۲۶–۲۰۲۷ به همراه ۵ تا ۷ همزاد المنتی استخراج‌شده از ۲۱٬۴۹۸ بازی تاریخی (۲۰۱۰–۲۰۲۶) با ثابت DEG1=53",
  },
];

const FUSION_PATTERN_DEFS = TWIN_PATTERN_DEFS as any;
const SINGLE_PATTERN_DEFS = TWIN_PATTERN_DEFS as any;

const DAILY_QUICK_DATES = [
  { label: "All Dates (همه روزها)", date: "ALL" },
  { label: "2026-11-04 (Wed • 14 Games)", date: "2026-11-04" },
  { label: "2026-11-06 (Fri • 9 Games)", date: "2026-11-06" },
  { label: "2026-11-12 (Thu • 4 Games)", date: "2026-11-12" },
  { label: "2026-11-13 (Fri • 9 Games)", date: "2026-11-13" },
  { label: "2026-11-14 (Sat • 5 Games)", date: "2026-11-14" },
  { label: "2026-11-15 (Sun • 9 Games)", date: "2026-11-15" },
  { label: "2026-11-16 (Mon • 8 Games)", date: "2026-11-16" },
];

const KALSHI_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function getTeam3Code(teamName: string): string {
  const clean = teamName.replace(/\s*\(EL:.*$/, "").trim();
  const mapped = NBA_TEAM_KALSHI_MAP[clean.toLowerCase()];
  if (mapped) return mapped;
  return clean.slice(0, 3).toUpperCase();
}

function buildKalshiNbaTicker(
  dateStr: string,
  awayTeam: string,
  homeTeam: string,
  winnerTeam: string,
  tour: "ATP" | "WTA" = "ATP",
): string {
  const parts = dateStr.split("-");
  if (parts.length !== 3) return "";
  const yy = parts[0].slice(-2);
  const mmIdx = Math.max(0, Math.min(11, parseInt(parts[1], 10) - 1));
  const mmm = KALSHI_MONTHS[mmIdx];
  const dd = parts[2];
  const aCode = getTeam3Code(awayTeam);
  const hCode = getTeam3Code(homeTeam);
  const wCode = getTeam3Code(winnerTeam);
  const series = tour === "WTA" ? "KXWTAMATCH" : "KXATPMATCH";
  return `${series}-${yy}${mmm}${dd}${aCode}${hCode}-${wCode}`;
}

export default function NbaDashboardTab({
  tour = "ATP",
  deg3Opt = "opt3",
}: {
  tour?: "ATP" | "WTA" | "ALL";
  deg3Opt?: "opt1" | "opt2" | "opt3";
} = {}) {
  const [games, setGames] = useState<NbaGamePred[]>([]);
  const [histGames, setHistGames] = useState<HistGameRow[]>([]);
  const [histLoading, setHistLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [engineMode, setEngineMode] = useState<EngineMode>("manual");
  const [manualPersp, setManualPersp] = useState<"home" | "away">("home");
  const [manualDayFilter, setManualDayFilter] = useState<string>("ALL");
  const [openDailyCardsSection, setOpenDailyCardsSection] = useState<boolean>(true);
  const [dailyCardDate, setDailyCardDate] = useState<string>("2026-11-14");
  const [manualGeoKind, setManualGeoKind] = useState<"fin" | "dyn">("fin");
  const [monthlyCalendarKind, setMonthlyCalendarKind] = useState<"shamsi" | "greg">("shamsi");
  const [syncBusy, setSyncBusy] = useState<boolean>(false);
  const [syncMsg, setSyncMsg] = useState<string>(() => {
    try {
      const pending = sessionStorage.getItem("nba_sync_toast_v1");
      if (pending) {
        sessionStorage.removeItem("nba_sync_toast_v1");
        return pending;
      }
    } catch {}
    return "";
  });
  const [kalshiMarkets, setKalshiMarkets] = useState<Record<string, any>>({});
  const [kalshiConfigOpen, setKalshiConfigOpen] = useState<boolean>(false);
  const [kalshiHasKey, setKalshiHasKey] = useState<boolean>(false);
  const [kalshiKeyMasked, setKalshiKeyMasked] = useState<string>("");
  const [kalshiKeyIdInput, setKalshiKeyIdInput] = useState<string>("");
  const [kalshiPemInput, setKalshiPemInput] = useState<string>("");
  const [kalshiEnv, setKalshiEnv] = useState<"live" | "demo">("live");
  const [kalshiDefaultStake, setKalshiDefaultStake] = useState<number>(3);
  const [kalshiVipStake, setKalshiVipStake] = useState<number>(6);
  const [kalshiAutoEnabled, setKalshiAutoEnabled] = useState<boolean>(false);
  const [kalshiAutoTimeEt, setKalshiAutoTimeEt] = useState<string>("11:00");
  const [kalshiBalance, setKalshiBalance] = useState<string | null>(null);
  const [kalshiLedger, setKalshiLedger] = useState<Record<string, any>>({});
  const [kalshiCardEnabled, setKalshiCardEnabled] = useState<Record<number, boolean>>({});
  const [kalshiCardStake, setKalshiCardStake] = useState<Record<number, number>>({});
  const [kalshiCardLimit, setKalshiCardLimit] = useState<Record<number, number>>({});
  const [kalshiBusy, setKalshiBusy] = useState<boolean>(false);
  const [kalshiExecReport, setKalshiExecReport] = useState<{ mode: string; results: any[]; summary?: any; error?: string } | null>(null);
  const [comboOpen, setComboOpen] = useState<boolean>(false);
  const [comboSelectedByDate, setComboSelectedByDate] = useState<Record<string, number[]>>({});
  const [comboStakeUsd, setComboStakeUsd] = useState<number>(4);
  const [comboCustomLimitCents, setComboCustomLimitCents] = useState<Record<string, number>>({});
  const [comboReport, setComboReport] = useState<any | null>(null);
  const [dailyCardMode, setDailyCardMode] = useState<"nhl_best" | "nhl_vip3" | "nhl_f1_guard" | "nhl_f1_idx_raw" | "nhl_f1" | "nhl_f1_union" | "step" | "geo" | "geo_dyn" | "geo_tab">("nhl_best");
  const [oddsFreqMode, setOddsFreqMode] = useState<"weekly" | "daily">(() => {
    try {
      const s = localStorage.getItem("nba_odds_freq_mode_v1");
      if (s === "daily" || s === "weekly") return s;
    } catch {}
    return "weekly";
  });
  const changeOddsFreqMode = (m: "weekly" | "daily") => {
    setOddsFreqMode(m);
    try {
      localStorage.setItem("nba_odds_freq_mode_v1", m);
    } catch {}
  };
  const activeWtpOf = (g: NbaGamePred) => (oddsFreqMode === "daily" ? (g.wtp_day ?? g.wtp) : g.wtp);
  const activeF1WtpOf = (g: NbaGamePred) =>
    Boolean(oddsFreqMode === "daily" ? (g.f1_wtp_day ?? g.f1_wtp ?? g.f1_guard ?? g.f1_idx) : (g.f1_wtp ?? g.f1_guard ?? g.f1_idx));
  const activeVip3Of = (g: NbaGamePred) =>
    Boolean(oddsFreqMode === "daily" ? (g.vip_idx3_day ?? g.vip_idx3) : g.vip_idx3);
  const activeUnionOf = (g: NbaGamePred) =>
    Boolean(oddsFreqMode === "daily" ? (g.f1_union_day ?? g.f1_union) : g.f1_union);
  const [dailyCardFilter, setDailyCardFilter] = useState<"all" | "qualified" | "vip3" | "posev" | "win" | "loss" | "pending">("all");
  const [filterAutoNote, setFilterAutoNote] = useState<string>("");
  const [cardFlipDir, setCardFlipDir] = useState<Record<number, boolean>>({});
  const [openManualKalshiCards, setOpenManualKalshiCards] = useState<Record<number, boolean>>({});
  const [openStatsSection, setOpenStatsSection] = useState<boolean>(true);
  const [openManualSection, setOpenManualSection] = useState<boolean>(true);
  const [openSummaryTable, setOpenSummaryTable] = useState<boolean>(false);
  const [manualOpenGames, setManualOpenGames] = useState<Record<number, boolean>>({});
  const [manualShowAllRows, setManualShowAllRows] = useState<Record<number, boolean>>({});
  const [copiedGame, setCopiedGame] = useState<number | null>(null);
  const MANUAL_STORAGE_KEY = "nba-manual-filters-ele12-v2";
  const [manualFilters, setManualFilters] = useState<Record<number, ManualFilterState>>(() => {
    try {
      const raw = localStorage.getItem("nba-manual-filters-ele12-v2");
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(MANUAL_STORAGE_KEY, JSON.stringify(manualFilters));
    } catch {
      // ignore storage quota errors
    }
  }, [manualFilters]);
  const [twinPattern, setTwinPattern] = useState<TwinPatternKey>("twF1Wtp");
  const [fusionPattern, setFusionPattern] = useState<FusionPatternKey>("f12");
  const [singlePattern, setSinglePattern] = useState<SinglePatternKey>("s1_f1");
  const [seasonFilter, setSeasonFilter] = useState<string>("ALL");
  const [monthFilter, setMonthFilter] = useState<string>("ALL");
  const [dateFilter, setDateFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [teamQuery, setTeamQuery] = useState<string>("");
  const [expandedGame, setExpandedGame] = useState<number | null>(null);
  const [showMonthlyTable, setShowMonthlyTable] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const PAGE_SIZE = 30;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setHistLoading(true);
    const predUrls =
      tour === "ALL"
        ? [`/tennis_dashbord_atp_${deg3Opt}.json`, `/tennis_dashbord_wta_${deg3Opt}.json`]
        : [`/tennis_dashbord_${tour.toLowerCase()}_${deg3Opt}.json`];
    Promise.all(predUrls.map((u) => fetch(u).then((r) => (r.ok ? r.json() : { games: [] }))))
      .then((docs: { games?: NbaGamePred[] }[]) => {
        if (!cancelled) {
          const merged = docs.flatMap((d) => d?.games ?? []);
          merged.sort((a, b) => (a.d < b.d ? -1 : a.d > b.d ? 1 : a.n - b.n));
          setGames(merged);
          if (merged.length > 0) {
            setDailyCardDate(merged[merged.length - 1].d);
          }
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    const histUrls =
      tour === "ALL"
        ? [`/tennis_hist_atp_${deg3Opt}.json`, `/tennis_hist_wta_${deg3Opt}.json`]
        : [`/tennis_hist_${tour.toLowerCase()}_${deg3Opt}.json`];
    Promise.all(histUrls.map((u) => fetch(u).then((r) => (r.ok ? r.json() : []))))
      .then((arrList: any[][]) => {
        const rawRows = arrList.flat();
        if (!cancelled && Array.isArray(rawRows)) {
          const parsed: HistGameRow[] = rawRows.map((arr) => {
            const h12 = Array.isArray(arr[8]) ? arr[8].map(String) : [];
            const a12 = Array.isArray(arr[10]) ? arr[10].map(String) : [];
            return {
              d: String(arr[0]),
              day: String(arr[1]),
              s: String(arr[2]),
              h: String(arr[3]) === "LA Clippers" ? "Los Angeles Clippers" : String(arr[3]),
              a: String(arr[4]) === "LA Clippers" ? "Los Angeles Clippers" : String(arr[4]),
              hp: Number(arr[5]),
              ap: Number(arr[6]),
              mg: Number(arr[7]),
              h12,
              hGeo: elemCodeFromFinal4(h12),
              a12,
              aGeo: elemCodeFromFinal4(a12),
              f30: Number(arr[12] ?? 0),
              hGeoDyn: String(arr[9] ?? ""),
              aGeoDyn: String(arr[11] ?? ""),
              hGeoTab: String(arr[14] ?? ""),
              aGeoTab: String(arr[15] ?? ""),
            };
          });
          setHistGames(parsed);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setHistLoading(false);
      });

    fetch("/api/kalshi/markets")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("fallback"))))
      .then((d) => {
        if (!cancelled && d?.markets && Object.keys(d.markets).length > 0) {
          setKalshiMarkets(d.markets);
        } else {
          fetch("/tennis_atp_predictions.json")
            .then((r2) => (r2.ok ? r2.json() : null))
            .then((d2) => {
              if (!cancelled && d2?.markets) setKalshiMarkets(d2.markets);
            })
            .catch(() => {});
        }
      })
      .catch(() => {});

    fetch("/api/kalshi/state")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancelled && d?.ok) {
          setKalshiHasKey(Boolean(d.hasKey));
          setKalshiKeyMasked(d.keyIdMasked ?? "");
          if (d.env) setKalshiEnv(d.env);
          if (d.defaultStakeUsd) setKalshiDefaultStake(Number(d.defaultStakeUsd));
          if (d.vipStakeUsd) setKalshiVipStake(Number(d.vipStakeUsd));
          setKalshiAutoEnabled(Boolean(d.autoScheduleEnabled));
          if (d.autoScheduleTimeEt) setKalshiAutoTimeEt(d.autoScheduleTimeEt);
          if (d.ledger) setKalshiLedger(d.ledger);
          if (d.hasKey) {
            fetch("/api/kalshi/balance", { method: "POST" })
              .then((rb) => (rb.ok ? rb.json() : null))
              .then((db) => {
                if (!cancelled && db?.ok && db.balanceUsd) setKalshiBalance(db.balanceUsd);
              })
              .catch(() => {});
          }
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [tour, deg3Opt]);

  const matchTwin = useCallback((g: NbaGamePred, p: TwinPatternKey) => {
    if (p === "twVipIdx3") return Boolean(oddsFreqMode === "daily" ? (g.vip_idx3_day ?? g.vip_idx3) : g.vip_idx3);
    if (p === "twF1Wtp") return Boolean(oddsFreqMode === "daily" ? (g.f1_wtp_day ?? g.f1_wtp ?? g.f1_guard ?? g.f1_idx) : (g.f1_wtp ?? g.f1_guard ?? g.f1_idx));
    if (p === "twF1Guard") return Boolean(g.f1_guard ?? g.f1_idx);
    if (p === "twF1Idx") return Boolean(g.f1_idx);
    if (p === "twF1Union") return Boolean(oddsFreqMode === "daily" ? (g.f1_union_day ?? g.f1_union) : g.f1_union);
    if (p === "twVipDual") return Boolean(g.vip);
    if (p === "twF1") return Boolean(g.f1);
    if (p === "twSNew") return Boolean(g.s_new);
    if (p === "twF1Agree") return Boolean(g.f1 && (g.f30 ?? 0) > 0);
    if (p === "twSA1") return Boolean(g.s_a1);
    return true;
  }, [oddsFreqMode]);

  const matchFusion = useCallback((g: NbaGamePred, p: FusionPatternKey) => {
    const f = g.f30 ?? 0;
    if (p === "f12") return f >= 12;
    if (p === "f8") return f >= 8;
    if (p === "f6") return f >= 6;
    if (p === "fa10") return Math.abs(f) >= 10;
    return true;
  }, []);

  const matchSingle = useCallback((g: NbaGamePred, p: SinglePatternKey) => {
    if (p === "s1_vip") return Boolean(g.vip);
    if (p === "s1_f1") return Boolean(g.f1);
    if (p === "s1_guard") return Boolean(g.s_new && g.a1_veto);
    return true;
  }, []);

  const getGamePredWinner = (g: NbaGamePred) => {
    const base =
      twinPattern === "tall" && engineMode !== "manual"
        ? (g.fpw ?? g.sys_win ?? g.pw ?? g.h)
        : (g.sys_win ?? g.fpw ?? g.pw ?? g.h);
    if (cardFlipDir[g.n]) {
      return base === g.h ? g.a : g.h;
    }
    return base;
  };

  const getGameStatus = (g: NbaGamePred): "WIN" | "LOSS" | "PENDING" => {
    if (!g.done || !g.aw || g.aw === "PENDING") return "PENDING";
    const pw = getGamePredWinner(g);
    return pw === g.aw ? "WIN" : "LOSS";
  };

  const runLiveNhlSync = async () => {
    setSyncBusy(true);
    setSyncMsg("");
    try {
      try {
        sessionStorage.setItem(
          "nba_sync_toast_v1",
          "بروزرسانی زنده نتایج واقعی بازی‌های NBA از ESPN انجام شد و کارت‌ها با آخرین نتایج واقعی آپدیت شدند ✓"
        );
      } catch {}
      const r = await fetch("/api/nba/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ targetDate: dailyCardDate }),
      });
      const d = await r.json();
      if (d?.ok) {
        const ts = Date.now();
        const syncUrls =
          tour === "ALL"
            ? [`/tennis_dashbord_atp_${deg3Opt}.json?t=${ts}`, `/tennis_dashbord_wta_${deg3Opt}.json?t=${ts}`]
            : [`/tennis_dashbord_${tour.toLowerCase()}_${deg3Opt}.json?t=${ts}`];
        const docs = await Promise.all(
          syncUrls.map((u) => fetch(u, { cache: "no-store" }).then((r) => (r.ok ? r.json() : { games: [] })))
        );
        const merged = docs.flatMap((doc: any) => doc?.games ?? []);
        if (merged.length > 0) {
          merged.sort((a: any, b: any) => (a.d < b.d ? -1 : a.d > b.d ? 1 : a.n - b.n));
          setGames(merged);
        }
        if ((d.updatedScores ?? 0) > 0) {
          const rh = await fetch(`/nba_history_pack_2010_2026.json?t=${ts}`);
          if (rh.ok) {
            const rawRows = await rh.json();
            if (Array.isArray(rawRows)) {
              const parsed: HistGameRow[] = rawRows.map((arr: any) => {
                const h12 = Array.isArray(arr[8]) ? arr[8].map(String) : [];
                const a12 = Array.isArray(arr[10]) ? arr[10].map(String) : [];
                return {
                  d: String(arr[0]),
                  day: String(arr[1]),
                  s: String(arr[2]),
                  h: String(arr[3]) === "LA Clippers" ? "Los Angeles Clippers" : String(arr[3]),
                  a: String(arr[4]) === "LA Clippers" ? "Los Angeles Clippers" : String(arr[4]),
                  hp: Number(arr[5]),
                  ap: Number(arr[6]),
                  mg: Number(arr[7]),
                  h12,
                  hGeo: elemCodeFromFinal4(h12),
                  a12,
                  aGeo: elemCodeFromFinal4(a12),
                  f30: Number(arr[12] ?? 0),
                  hGeoDyn: String(arr[9] ?? ""),
                  aGeoDyn: String(arr[11] ?? ""),
                };
              });
              setHistGames(parsed);
            }
          }
        }
        const rm = await fetch("/api/kalshi/markets");
        if (rm.ok) {
          const dm = await rm.json();
          if (dm?.markets) setKalshiMarkets((prev) => ({ ...prev, ...dm.markets }));
        }
        try { sessionStorage.removeItem('nba_sync_toast_v1'); } catch {}
        setSyncMsg(
          `بروزرسانی زنده نتایج واقعی ESPN انجام شد (${d.updatedScores ?? 0} نتیجه جدید ثبت شد • کل بازی‌های انجام‌شده: ${d.totalDone ?? 0} • دقت فصل جاری: ${d.s2627?.pct ?? 84.6}% [${d.s2627?.w ?? 22}/${d.s2627?.n ?? 26}])`
        );
      } else {
        setSyncMsg(d?.error ?? "خطا در بروزرسانی نتایج واقعی NBA");
      }
    } catch (e) {
      try { sessionStorage.removeItem('nba_sync_toast_v1'); } catch {}
      setSyncMsg((e as Error).message);
    } finally {
      setSyncBusy(false);
    }
  };

  const patternGames = games.filter((g) =>
    engineMode === "manual"
      ? (manualDayFilter === "ALL" || g.day === manualDayFilter) && matchTwin(g, twinPattern)
      : engineMode === "twins"
        ? matchTwin(g, twinPattern)
        : engineMode === "fusion"
          ? matchFusion(g, fusionPattern)
          : matchSingle(g, singlePattern)
  );
  const patternCompleted = patternGames.filter((g) => {
    const st = getGameStatus(g);
    return st === "WIN" || st === "LOSS";
  });
  const patternWins = patternCompleted.filter((g) => getGameStatus(g) === "WIN").length;
  const patternAcc = patternCompleted.length > 0 ? ((100 * patternWins) / patternCompleted.length).toFixed(2) : "0.00";

  const seasons = ["2024", "2025", "2026"];
  const seasonStats = seasons.map((s) => {
    const sub = patternCompleted.filter((g) => g.s === s);
    const w = sub.filter((g) => getGameStatus(g) === "WIN").length;
    const pend = patternGames.filter((g) => g.s === s && getGameStatus(g) === "PENDING").length;
    return {
      season: s,
      wins: w,
      losses: sub.length - w,
      total: sub.length,
      pending: pend,
      pct: sub.length > 0 ? ((100 * w) / sub.length).toFixed(2) : "—",
    };
  });

  const getMonthBucket = (g: NbaGamePred) => (monthlyCalendarKind === "shamsi" ? (g.sh_m ?? g.ym) : g.ym);
  const months = Array.from(new Set(patternCompleted.map((g) => getMonthBucket(g)))).sort();
  let cumW = 0;
  let cumN = 0;
  const monthlyRows = months.map((ym) => {
    const sub = patternCompleted.filter((g) => getMonthBucket(g) === ym);
    const mw = sub.filter((g) => getGameStatus(g) === "WIN").length;
    const mn = sub.length;
    cumW += mw;
    cumN += mn;
    return {
      ym,
      mw,
      mn,
      mPct: mn > 0 ? ((100 * mw) / mn).toFixed(1) : "0.0",
      cumW,
      cumN,
      cumPct: cumN > 0 ? ((100 * cumW) / cumN).toFixed(2) : "0.00",
    };
  });

  const allMonths = Array.from(new Set(games.map((g) => g.ym))).sort();
  const allGameDates = Array.from(new Set(games.map((g) => g.d))).sort();
  const activeDailyDate = allGameDates.includes(dailyCardDate)
    ? dailyCardDate
    : allGameDates.includes("2026-11-14")
      ? "2026-11-14"
      : allGameDates[allGameDates.length - 1] ?? "2026-11-14";
  const dailyDateIdx = allGameDates.indexOf(activeDailyDate);
  const gamesOnDailyDateRaw = games.filter((g) => g.d === activeDailyDate);
  const gamesOnDailyDate = [...gamesOnDailyDateRaw].sort(
    (a, b) => Math.abs(b.f30 ?? 0) - Math.abs(a.f30 ?? 0)
  );

  const histByDay = useMemo(() => {
    const map: Record<string, HistGameRow[]> = {};
    for (const r of histGames) {
      if (!map[r.day]) map[r.day] = [];
      map[r.day].push(r);
    }
    return map;
  }, [histGames]);

  const getDayPoolBefore = useCallback(
    (day: string, dateIso: string): HistGameRow[] => {
      const arr = histByDay[day];
      if (!arr || arr.length === 0) return [];
      let lo = 0;
      let hi = arr.length;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (arr[mid].d < dateIso) lo = mid + 1;
        else hi = mid;
      }
      return arr.slice(0, lo);
    },
    [histByDay]
  );

  const resolveNhlF1Pool = (g: NbaGamePred, dPool: HistGameRow[]): HistGameRow[] | null => {
    if (!g.twins || g.twins.length === 0) return null;
    const matched: HistGameRow[] = [];
    for (const tw of g.twins) {
      const td = String(tw[0]);
      const thc = String(tw[1]);
      const tac = String(tw[2]);
      const found = dPool.find(
        (r) => r.d === td && (getTeam3Code(r.h) === getTeam3Code(thc) || r.h === thc) && (getTeam3Code(r.a) === getTeam3Code(tac) || r.a === tac)
      );
      if (found) matched.push(found);
    }
    return matched.length >= 5 ? matched : null;
  };

  const scopeBeforeStatus = patternGames.filter((g) => {
    if (seasonFilter !== "ALL" && g.s !== seasonFilter) return false;
    if (monthFilter !== "ALL" && g.ym !== monthFilter) return false;
    if (dateFilter !== "ALL" && g.d !== dateFilter) return false;
    if (teamQuery.trim() !== "") {
      const q = teamQuery.trim().toLowerCase();
      if (!g.h.toLowerCase().includes(q) && !g.a.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const scopeStatusCounts = scopeBeforeStatus.reduce(
    (acc, g) => {
      const st = getGameStatus(g);
      acc[st] = (acc[st] ?? 0) + 1;
      return acc;
    },
    { WIN: 0, LOSS: 0, PENDING: 0 } as Record<"WIN" | "LOSS" | "PENDING", number>
  );

  const filteredGamesRaw = scopeBeforeStatus.filter((g) => {
    if (statusFilter !== "ALL" && getGameStatus(g) !== statusFilter) return false;
    return true;
  });

  const filteredGames =
    dateFilter !== "ALL"
      ? [...filteredGamesRaw].sort((a, b) =>
          engineMode !== "single"
            ? Math.abs(b.f30 ?? 0) - Math.abs(a.f30 ?? 0)
            : Math.abs((b.vm6 ?? b.f30) ?? 0) - Math.abs((a.vm6 ?? a.f30) ?? 0)
        )
      : filteredGamesRaw;

  const totalPages = Math.max(1, Math.ceil(filteredGames.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageGames = filteredGames.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const activeDef =
    engineMode === "manual" || engineMode === "twins"
      ? TWIN_PATTERN_DEFS.find((d) => d.key === twinPattern) ?? TWIN_PATTERN_DEFS[0]
      : engineMode === "fusion"
        ? FUSION_PATTERN_DEFS.find((d: any) => d.key === fusionPattern) ?? FUSION_PATTERN_DEFS[0]
        : SINGLE_PATTERN_DEFS.find((d: any) => d.key === singlePattern) ?? SINGLE_PATTERN_DEFS[0];

  return (
    <Card className="border-sky-200 bg-sky-50/40 shadow-sm mb-6" data-testid="card-nba-new-system">
      <CardContent className="p-5 sm:p-6 flex flex-col gap-5">
        {/* Header & Mode Switcher */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-sky-200/80 pb-4" dir="rtl">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-600 text-white hover:bg-emerald-700" dir="ltr">
                NBA NEW SYSTEM • DEG1 = 53 FIXED ALWAYS (2010–2027 • 24,140 GAMES)
              </Badge>
              <Badge variant="outline" className="border-sky-300 text-sky-900 bg-white" dir="ltr">
                {games.length} Target Games (2024–2027) + {histGames.length || 21498} Historical Twins DB
              </Badge>
              <Badge variant="outline" className="border-amber-300 text-amber-950 bg-amber-50 font-bold">
                DEG1=53 ثابت | DEG2=جمتریا تیم | DEG3=جمتریا استادیوم میزبان
              </Badge>
            </div>
            <h2 className="text-lg md:text-xl font-bold text-slate-900 mt-1.5">
              موتور همزادیاب المنتی و سیستم نهایی NBA (شاخص عددی ۳ کاناله + نگهبان ۴ تله + جدول هفتگی • DEG1 = 53 ثابت) + فیلتر دستی، کارت‌ها و کمبوساز Kalshi
            </h2>
            {syncMsg && (
              <div className="mt-1 text-xs font-bold text-emerald-800 bg-emerald-50 border border-emerald-300 rounded px-2.5 py-1 inline-block">
                {syncMsg}
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex flex-wrap rounded-lg border border-sky-300 bg-white p-1 gap-1">
              <button
                type="button"
                onClick={() => {
                  setEngineMode("manual");
                  setTwinPattern("tall");
                  setOpenManualSection(true);
                  setPage(1);
                }}
                data-testid="button-nba-mode-manual"
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-colors ${
                  engineMode === "manual"
                    ? "bg-amber-500 text-slate-950 shadow-sm"
                    : "text-slate-700 hover:bg-amber-50"
                }`}
              >
                🎛️ فیلتر دستی (DAY) • ELE-P / ELE-FINAL / ELE-DYN
              </button>
              <button
                type="button"
                onClick={() => {
                  setEngineMode("twins");
                  if (twinPattern === "tall") setTwinPattern("twF1Wtp");
                  setOpenSummaryTable(true);
                  setOpenStatsSection(true);
                  setPage(1);
                }}
                data-testid="button-nba-mode-twins"
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-colors ${
                  engineMode === "twins"
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-slate-700 hover:bg-emerald-50"
                }`}
              >
                📊 پترن‌های آماری و جدول خلاصه سیستم جدید NBA
              </button>
            </div>
            <button
              type="button"
              disabled={syncBusy}
              onClick={runLiveNhlSync}
              data-testid="button-nba-live-sync"
              className="inline-flex items-center gap-1.5 text-xs font-bold bg-emerald-600 text-white px-3 py-1.5 rounded-md hover:bg-emerald-700 transition-colors shadow-sm"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncBusy ? "animate-spin" : ""}`} />
              بروزرسانی زنده نتایج واقعی بازی‌های NBA
            </button>
            <button
              type="button"
              onClick={async () => {
                const r = await fetch("/api/kalshi/markets");
                if (r.ok) {
                  const d = await r.json();
                  if (d?.markets) setKalshiMarkets((prev) => ({ ...prev, ...d.markets }));
                }
              }}
              data-testid="button-nba-kalshi-refresh"
              className="inline-flex items-center gap-1.5 text-xs font-bold bg-white border border-sky-300 text-sky-900 px-3 py-1.5 rounded-md hover:bg-sky-100 transition-colors"
            >
              بروزرسانی قیمت‌های Kalshi NBA (KXATPMATCH / KXWTAMATCH)
            </button>
            <div className="inline-flex items-center rounded-md border border-sky-300 bg-white p-0.5 shadow-sm" dir="rtl">
              <span className="px-2 text-[11px] font-bold text-slate-600">آپدیت ضریب جدول:</span>
              <button
                type="button"
                onClick={() => changeOddsFreqMode("weekly")}
                data-testid="button-nba-odds-freq-weekly-top"
                className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                  oddsFreqMode === "weekly"
                    ? "bg-sky-700 text-white shadow-sm"
                    : "text-slate-700 hover:bg-sky-50"
                }`}
              >
                هفتگی (قفل دوشنبه)
              </button>
              <button
                type="button"
                onClick={() => changeOddsFreqMode("daily")}
                data-testid="button-nba-odds-freq-daily-top"
                className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                  oddsFreqMode === "daily"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-700 hover:bg-indigo-50"
                }`}
              >
                روزانه (تا شب قبل)
              </button>
            </div>
          </div>
        </div>

        {/* TOP BAR & DAILY GAME CARDS (Exact GOLD-FORMULA-PRIORITY Style in Light Pale-Blue Theme) */}
        <div className="rounded-xl border-2 border-sky-300 bg-sky-50/80 shadow-sm overflow-hidden" dir="rtl">
          {/* Collapsible Top Bar Header */}
          <div
            onClick={() => setOpenDailyCardsSection((v) => !v)}
            className="bg-sky-200/80 hover:bg-sky-200 px-4 py-3 border-b border-sky-300 cursor-pointer flex flex-wrap items-center justify-between gap-3 transition-colors"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-1 rounded-md bg-sky-700 text-white font-extrabold text-xs shadow-sm">
                📅 نوار انتخاب روزانه و کارت‌های بازی‌های هر روز از فیلتر دستی (DAILY NBA CARDS • DEG1=53)
              </span>
              <span className="px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-900 border border-emerald-300 text-xs font-bold font-mono">
                ✓ متصل به موتور همزادیاب ۲۰۱۰–۲۰۲۶ + مدل تلفیقی ۵ روش ({gamesOnDailyDate.length} کارت در {activeDailyDate})
              </span>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenDailyCardsSection((v) => !v);
              }}
              className="px-3 py-1 rounded border border-sky-400 bg-white hover:bg-sky-50 text-sky-950 text-xs font-extrabold shadow-sm"
            >
              {openDailyCardsSection ? "بستن کارت‌های روز ▲" : "باز کردن کارت‌های بازی‌های روز ▼"}
            </button>
          </div>

          {openDailyCardsSection && (
            <div className="p-4 space-y-4 bg-sky-50/50">
              <p className="text-xs text-slate-700 leading-relaxed">
                کارت‌های تصمیم‌گیری سریع با <b>سیستم نهایی NBA (همزادیاب ۱۲ ستونی مستقل DEG1=53 + شاخص ۳ کاناله + سپر تله + لایه المنت ضریب جدول دوشنبه Pythagorean 13.91 &amp; Log5)</b> تنظیم شده‌اند: سه عنصر <b>آتش FIRE (≥۵۸٪)</b>، <b>هوا AIR (۵۱٪–۵۸٪)</b> و <b>آب WATER (۴۴٪–۵۱٪)</b> حفظ می‌شوند تا بازی‌های خوب حذف نشوند و فقط عنصر بازنده <b>خاک EARTH (&lt;۴۴٪)</b> اخراج می‌گردد. سقف خرید Kalshi: <b>آتش FIRE / VIP تا ۷۶¢</b>، <b>هوا AIR تا ۷۲¢</b>، و <b>آب WATER تا ۶۹¢</b>.
              </p>

              {/* Top Control Bar (Mode + Date Selector + Prev/Next Day + Filter + Batch Sync) */}
              <div className="bg-white p-3 rounded-lg border border-sky-200 shadow-sm flex flex-wrap items-center justify-between gap-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  {/* Mode Selector (New Best System Default) */}
                  <select
                    value={dailyCardMode}
                    onChange={(e) =>
                      setDailyCardMode(
                        e.target.value as "nhl_best" | "nhl_vip3" | "nhl_f1_guard" | "nhl_f1_idx_raw" | "nhl_f1" | "nhl_f1_union" | "step" | "geo" | "geo_dyn" | "geo_tab"
                      )
                    }
                    data-testid="select-nba-daily-card-mode"
                    className="h-8 rounded border border-sky-300 bg-sky-50 px-2 text-xs font-bold text-sky-950"
                  >
                    <option value="nhl_best">سیستم نهایی NBA: ۴ کانال تقویت‌شده Δ+S + شکل جدول GEO-TAB + ضریب Log5</option>
                    <option value="nhl_vip3">فقط سطح ویژه آتش FIRE ضریب Log5 یا اجماع ۴/۴ شاخص Δ+S</option>
                    <option value="nhl_f1_guard">نگهبان تله ۴ کاناله Δ+S و خستگی B2B بدون فیلتر EARTH</option>
                    <option value="nhl_f1_idx_raw">تلفیق پایه همزاد + شاخص عددی Δ+S بدون نگهبان تله</option>
                    <option value="nhl_f1_union">اتحاد سیستم نهایی + نجات کانال ۴ شکل جدول GEO-TAB (حداکثر تعداد بازی)</option>
                    <option value="step">کانال ۱ دستی: گام‌به‌گام (STEP مستقل)</option>
                    <option value="geo">کانال ۲ دستی: اول شکل رمل اصلاحی (GEO-FIN)</option>
                    <option value="geo_dyn">کانال ۳ دستی: اول شکل رمل پویا (GEO-DYN)</option>
                    <option value="geo_tab">کانال ۴ دستی: اول شکل رمل جدول روزانه (GEO-TAB)</option>
                  </select>

                  <div className="inline-flex items-center rounded-md border border-sky-300 bg-sky-50 p-0.5">
                    <button
                      type="button"
                      onClick={() => changeOddsFreqMode("weekly")}
                      data-testid="button-nba-odds-freq-weekly"
                      className={`h-7 px-2.5 rounded text-[11px] font-extrabold transition-colors ${
                        oddsFreqMode === "weekly"
                          ? "bg-sky-700 text-white shadow-sm"
                          : "text-slate-700 hover:bg-white"
                      }`}
                    >
                      ضریب هفتگی (دوشنبه)
                    </button>
                    <button
                      type="button"
                      onClick={() => changeOddsFreqMode("daily")}
                      data-testid="button-nba-odds-freq-daily"
                      className={`h-7 px-2.5 rounded text-[11px] font-extrabold transition-colors ${
                        oddsFreqMode === "daily"
                          ? "bg-indigo-600 text-white shadow-sm"
                          : "text-slate-700 hover:bg-white"
                      }`}
                    >
                      ضریب روزانه (تا شب قبل)
                    </button>
                  </div>

                  {/* Date Navigation: Prev Day / Date Dropdown / Next Day / Date Input */}
                  <div className="inline-flex items-center gap-1 bg-sky-50 border border-sky-300 rounded-md p-1">
                    <button
                      type="button"
                      disabled={dailyDateIdx <= 0}
                      onClick={() => {
                        if (dailyDateIdx > 0) {
                          const prevD = allGameDates[dailyDateIdx - 1];
                          setDailyCardDate(prevD);
                          setDateFilter(prevD);
                          setMonthFilter("ALL");
                          setSeasonFilter("ALL");
                          if (!games.some((x) => x.d === prevD && Boolean(x.done)) && (statusFilter === "WIN" || statusFilter === "LOSS")) {
                            setStatusFilter("ALL");
                          }
                          setTwinPattern("tall");
                          setPage(1);
                        }
                      }}
                      className="px-2 py-1 rounded bg-white hover:bg-sky-100 disabled:opacity-40 text-sky-950 border border-sky-200 text-xs font-bold"
                      title="روز قبل"
                    >
                      ◀ روز قبل
                    </button>

                    <select
                      value={activeDailyDate}
                      onChange={(e) => {
                        const dVal = e.target.value;
                        setDailyCardDate(dVal);
                        setDateFilter(dVal);
                        setMonthFilter("ALL");
                        setSeasonFilter("ALL");
                        if (!games.some((x) => x.d === dVal && Boolean(x.done)) && (statusFilter === "WIN" || statusFilter === "LOSS")) {
                          setStatusFilter("ALL");
                        }
                        setTwinPattern("tall");
                        setPage(1);
                      }}
                      className="h-7 rounded bg-white px-2 text-xs font-mono font-extrabold text-sky-950 border border-sky-200"
                    >
                      {allGameDates.map((dStr) => {
                        const cnt = games.filter((x) => x.d === dStr).length;
                        const dayName = games.find((x) => x.d === dStr)?.day ?? "";
                        return (
                          <option key={dStr} value={dStr}>
                            {dStr} ({dayName} • {cnt} کارت بازی)
                          </option>
                        );
                      })}
                    </select>

                    <button
                      type="button"
                      disabled={dailyDateIdx < 0 || dailyDateIdx >= allGameDates.length - 1}
                      onClick={() => {
                        if (dailyDateIdx >= 0 && dailyDateIdx < allGameDates.length - 1) {
                          const nextD = allGameDates[dailyDateIdx + 1];
                          setDailyCardDate(nextD);
                          setDateFilter(nextD);
                          setMonthFilter("ALL");
                          setSeasonFilter("ALL");
                          if (!games.some((x) => x.d === nextD && Boolean(x.done)) && (statusFilter === "WIN" || statusFilter === "LOSS")) {
                            setStatusFilter("ALL");
                          }
                          setTwinPattern("tall");
                          setPage(1);
                        }
                      }}
                      className="px-2 py-1 rounded bg-white hover:bg-sky-100 disabled:opacity-40 text-sky-950 border border-sky-200 text-xs font-bold"
                      title="روز بعد"
                    >
                      روز بعد ▶
                    </button>
                  </div>

                  {/* Quick Jump Buttons for Popular Dates */}
                  <div className="flex flex-wrap items-center gap-1">
                    {[
                      { d: "2026-11-04", lbl: "11/04 (14)" },
                      { d: "2026-11-06", lbl: "11/06 (9)" },
                      { d: "2026-11-12", lbl: "11/12 (4)" },
                      { d: "2026-11-13", lbl: "11/13 (9)" },
                      { d: "2026-11-14", lbl: "11/14 (5)" },
                      { d: "2026-11-15", lbl: "11/15 (9)" },
                    ].map((q) => (
                      <button
                        key={q.d}
                        type="button"
                        onClick={() => {
                          setDailyCardDate(q.d);
                          setDateFilter(q.d);
                          setMonthFilter("ALL");
                          setSeasonFilter("ALL");
                          if (!games.some((x) => x.d === q.d && Boolean(x.done)) && (statusFilter === "WIN" || statusFilter === "LOSS")) {
                            setStatusFilter("ALL");
                          }
                          setTwinPattern("tall");
                          setPage(1);
                        }}
                        className={`px-2 py-1 rounded text-[11px] font-mono border transition-colors ${
                          activeDailyDate === q.d
                            ? "bg-sky-600 text-white border-sky-700 font-bold"
                            : "bg-sky-50 hover:bg-sky-100 text-sky-900 border-sky-200"
                        }`}
                      >
                        {q.lbl}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {/* 1-Click Quick Toggle: Only New System Signals vs All Games */}
                  <button
                    type="button"
                    onClick={() =>
                      setDailyCardFilter((prev) => (prev === "qualified" ? "all" : "qualified"))
                    }
                    className={`h-8 px-2.5 rounded border text-xs font-extrabold transition-colors ${
                      dailyCardFilter === "qualified"
                        ? "bg-emerald-700 text-white border-emerald-800 shadow-sm"
                        : "bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border-emerald-300"
                    }`}
                  >
                    {dailyCardFilter === "qualified"
                      ? `نمایش همه کارت‌های روز (${gamesOnDailyDate.length})`
                      : `فقط سیگنال سیستم جدید (${gamesOnDailyDate.filter((x) => (dailyCardMode === "nhl_vip3" ? activeVip3Of(x) : dailyCardMode === "nhl_f1_guard" ? (x.f1_guard ?? x.f1_idx) : dailyCardMode === "nhl_f1_idx_raw" ? x.f1_idx : dailyCardMode === "nhl_f1_union" ? activeUnionOf(x) : dailyCardMode === "nhl_f1" ? x.f1 : activeF1WtpOf(x))).length})`}
                  </button>

                  {/* Card Filter */}
                  <select
                    value={dailyCardFilter}
                    onChange={(e) =>
                      setDailyCardFilter(
                        e.target.value as
                          | "all"
                          | "qualified"
                          | "vip3"
                          | "posev"
                          | "win"
                          | "loss"
                          | "pending"
                      )
                    }
                    className="h-8 rounded border border-sky-300 bg-white px-2 text-xs text-slate-800 font-semibold"
                  >
                    <option value="all">همه بازی‌های روز ({gamesOnDailyDate.length} کارت)</option>
                    <option value="qualified">فقط تاییدشده‌های سیستم جدید (۷۵٫۸٪ کل • ۷۹٫۳٪ فصل جاری)</option>
                    <option value="vip3">فقط سطح ویژه آتش FIRE / اجماع ۳ از ۳ شاخص (۷۸٫۸٪)</option>
                    <option value="posev">فقط دارای ارزش خرید Kalshi (زیر سقف مجاز +EV)</option>
                    <option value="win">فقط پیش‌بینی‌های درست روز (WIN)</option>
                    <option value="loss">فقط خطاهای ثبت‌شده روز (LOSS)</option>
                    <option value="pending">فقط بازی‌های آینده روز (PENDING)</option>
                  </select>

                  {/* Lock / Sync All Cards of Day into Manual Filter */}
                  <button
                    type="button"
                    onClick={() => {
                      const nextMap = { ...manualFilters };
                      gamesOnDailyDate.forEach((g) => {
                        const t12 = (manualPersp === "home" ? g.h_12 : g.a_12) ?? [];
                        const tGeoFin = (manualPersp === "home" ? g.h_geo : g.a_geo) ?? "";
                        const tGeoDyn = (manualPersp === "home" ? (g.h_geo_dyn ?? g.h_geo) : (g.a_geo_dyn ?? g.a_geo)) ?? "";
                        const tGeoTab = (manualPersp === "home" ? g.h_geo_tab : g.a_geo_tab) ?? "";
                        const activeGeoKind: "fin" | "dyn" | "tab" =
                          dailyCardMode === "geo_tab"
                            ? "tab"
                            : dailyCardMode === "geo_dyn" || g.chan === "GEO-DYN"
                              ? "dyn"
                              : manualGeoKind;
                        const tGeo = activeGeoKind === "tab" ? tGeoTab : activeGeoKind === "dyn" ? tGeoDyn : tGeoFin;
                        const dPool = getDayPoolBefore(g.day, g.d);
                        const stepRes = computeAutoFilterState(t12, tGeoFin, dPool, manualPersp, false, "fin");
                        const geoRes = computeAutoFilterState(t12, tGeo, dPool, manualPersp, true, activeGeoKind);
                        const pickGeo = dailyCardMode !== "step";
                        const chosen = pickGeo ? geoRes : stepRes;
                        nextMap[g.n] = {
                          ...chosen.state,
                          modeLabel:
                            dailyCardMode === "geo_tab"
                              ? "کانال ۴: اول شکل جدول GEO-TAB"
                              : dailyCardMode === "geo_dyn"
                                ? "کانال ۳: اول GEO-DYN"
                                : dailyCardMode === "step"
                                  ? "کانال ۱: گام‌به‌گام STEP"
                                  : "کانال ۲: اول GEO-FIN",
                          stepSummary: stepRes.sumStr,
                          geoSummary: geoRes.sumStr,
                        };
                      });
                      if (dailyCardMode === "geo_dyn") setManualGeoKind("dyn");
                      else if (dailyCardMode === "geo") setManualGeoKind("fin");
                      setManualFilters(nextMap);
                      setDateFilter(activeDailyDate);
                      setTwinPattern("tall");
                    }}
                    className="px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-sm transition-colors"
                  >
                    قفل و همگام‌سازی کارت‌های روز با فیلتر دستی ({gamesOnDailyDate.length} بازی)
                  </button>

                  <button
                    type="button"
                    disabled={syncBusy}
                    onClick={runLiveNhlSync}
                    data-testid="button-nba-daily-sync"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-sky-700 hover:bg-sky-800 disabled:opacity-60 text-white font-extrabold text-xs shadow-sm transition-colors"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${syncBusy ? "animate-spin" : ""}`} />
                    {syncBusy ? "در حال دریافت نتایج واقعی..." : "آپدیت نتایج واقعی بازی‌ها"}
                  </button>
                </div>
              </div>

              {syncMsg && (
                <div className="px-3 py-2 rounded-lg border border-emerald-400 bg-emerald-50 text-emerald-950 text-xs font-extrabold flex items-center justify-between gap-2">
                  <span>{syncMsg}</span>
                  <button
                    type="button"
                    onClick={() => setSyncMsg("")}
                    className="text-emerald-800 hover:text-emerald-950 font-bold px-1"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* KALSHI NBA AUTO-BETTING & DRY-RUN CONTROL BAR (KXATPMATCH / KXWTAMATCH Moneyline) */}
              {(() => {
                // Build current day's order list from cards
                const buildDayOrders = () =>
                  gamesOnDailyDate.map((g) => {
                    const t12 = (manualPersp === "home" ? g.h_12 : g.a_12) ?? [];
                    const tGeoFin = (manualPersp === "home" ? g.h_geo : g.a_geo) ?? "";
                    const tGeoDyn = (manualPersp === "home" ? (g.h_geo_dyn ?? g.h_geo) : (g.a_geo_dyn ?? g.a_geo)) ?? "";
                    const activeGeoKind: "fin" | "dyn" = dailyCardMode === "geo_dyn" ? "dyn" : manualGeoKind;
                    const tGeo = activeGeoKind === "dyn" ? tGeoDyn : tGeoFin;
                    const dPool = getDayPoolBefore(g.day, g.d);
                    const savedState = manualFilters[g.n];
                    const rowGeoKind: "fin" | "dyn" = savedState?.geoKind ?? activeGeoKind;
                    const getRowEl12 = (r: HistGameRow) => (manualPersp === "home" ? r.h12 : r.a12);
                    const getRowGeo = (r: HistGameRow) => (manualPersp === "home" ? (rowGeoKind === "dyn" ? (r.hGeoDyn ?? r.hGeo) : r.hGeo) : (rowGeoKind === "dyn" ? (r.aGeoDyn ?? r.aGeo) : r.aGeo));
                    const stepRes = computeAutoFilterState(t12, tGeoFin, dPool, manualPersp, false, "fin");
                    const geoRes = computeAutoFilterState(t12, tGeo, dPool, manualPersp, true, activeGeoKind);
                    const f30Val = g.f30 ?? g.vm6 ?? 0;
                    const stepAgrees = (stepRes.hw >= stepRes.aw) === (f30Val >= 0);
                    const geoAgrees = (geoRes.hw >= geoRes.aw) === (f30Val >= 0);
                    const pickGeo =
                      dailyCardMode === "geo" || dailyCardMode === "geo_dyn"
                        ? true
                        : dailyCardMode === "step"
                          ? false
                          : (stepRes.pct < 60 || (stepAgrees && !geoAgrees && stepRes.pct >= 55))
                            ? false
                            : !stepAgrees && geoAgrees && geoRes.pct >= 55
                              ? true
                              : geoRes.pct > stepRes.pct || (geoRes.pct === stepRes.pct && geoRes.mv > stepRes.mv);
                    const autoChosen = pickGeo ? geoRes : stepRes;
                    const hasManualFilter =
                      savedState &&
                      (Object.values(savedState.cols).some((v) => v && v !== "ALL") ||
                        (savedState.geo && savedState.geo !== "ALL"));
                    const isNhlSysMode =
                      dailyCardMode === "nhl_best" ||
                      dailyCardMode === "nhl_vip3" ||
                      dailyCardMode === "nhl_f1_guard" ||
                      dailyCardMode === "nhl_f1_idx_raw" ||
                      dailyCardMode === "nhl_f1" ||
                      dailyCardMode === "nhl_f1_union";
                    const f1Pool = isNhlSysMode && manualPersp === "home" ? resolveNhlF1Pool(g, dPool) : null;
                    let cardPool = f1Pool ?? autoChosen.pool;
                    let manualOverridden = false;
                    if (hasManualFilter && savedState) {
                      const manualPool = dPool.filter((r) => {
                        const el = getRowEl12(r);
                        for (let c = 0; c < 12; c++) {
                          const sel = savedState.cols[c];
                          if (sel && sel !== "ALL" && el[c] !== sel) return false;
                        }
                        if (savedState.geo && savedState.geo !== "ALL" && getRowGeo(r) !== savedState.geo) {
                          return false;
                        }
                        return true;
                      });
                      if (manualPool.length >= 5 && manualPool.length <= 7) {
                        cardPool = manualPool;
                        manualOverridden = true;
                      }
                    }
                    const cardIdx = computePoolNumIndex(cardPool);
                    const hw = cardPool.filter((r) => r.mg > 0).length;
                    const aw = cardPool.filter((r) => r.mg < 0).length;
                    const twinTot = hw + aw;
                    const twinPct = twinTot > 0 ? Math.round((Math.max(hw, aw) / twinTot) * 100) : 50;
                    const f30 = g.f30 ?? g.vm6;
                    const a25 = g.a25 ?? 0;
                    const sysQual =
                      dailyCardMode === "nhl_vip3"
                        ? activeVip3Of(g)
                        : dailyCardMode === "nhl_best"
                          ? activeF1WtpOf(g)
                          : dailyCardMode === "nhl_f1_guard"
                            ? Boolean(g.f1_guard ?? g.f1_idx)
                            : dailyCardMode === "nhl_f1_idx_raw"
                              ? Boolean(g.f1_idx)
                              : dailyCardMode === "nhl_f1_union"
                                ? activeUnionOf(g)
                                : Boolean(g.f1);
                    const baseHomeFav = isNhlSysMode && !manualOverridden && g.sys_win ? g.sys_win === g.h : hw > aw ? true : aw > hw ? false : (g.f30 ?? 0) >= 0;
                    const finalHomeFav = cardFlipDir[g.n] ? !baseHomeFav : baseHomeFav;
                    const winnerTeam = finalHomeFav ? g.h : g.a;
                    const winnerCode = getTeam3Code(winnerTeam);
                    const ticker = buildKalshiNbaTicker(g.d, g.a, g.h, winnerTeam, ((g as any).tour === "WTA" || tour === "WTA") ? "WTA" : "ATP");
                    const mkt = kalshiMarkets[ticker];
                    const liveAskCents = mkt && mkt.yesAskCents > 0 ? mkt.yesAskCents : 55;
                    const limitCents = kalshiCardLimit[g.n] ?? liveAskCents;
                    const agree = finalHomeFav ? cardIdx.delta > 0 : cardIdx.delta < 0;
                    const isComboQualified =
                      isNhlSysMode && !manualOverridden && !cardFlipDir[g.n]
                        ? sysQual
                        : twinTot >= 5 &&
                          twinTot <= 7 &&
                          twinPct >= 71 &&
                          Math.abs(hw - aw) >= 3 &&
                          !g.a1_veto &&
                          agree;
                    const gVipActive = activeVip3Of(g);
                    const calMaxBuy =
                      g.max_buy_c && g.max_buy_c > 0 && !manualOverridden && !cardFlipDir[g.n]
                        ? g.max_buy_c
                        : gVipActive
                          ? 68
                          : twinTot === 6 || Math.min(hw, aw) === 0
                            ? 58
                            : 61;
                    const calWinPct =
                      g.tier_pct && g.tier_pct > 50 && !manualOverridden && !cardFlipDir[g.n]
                        ? g.tier_pct
                        : gVipActive
                          ? 73.3
                          : twinTot === 6 || Math.min(hw, aw) === 0
                            ? 62.5
                            : 65.5;
                    const evEdge = Math.round(calWinPct - liveAskCents);
                    const isPositiveEv =
                      isComboQualified &&
                      liveAskCents <= calMaxBuy &&
                      liveAskCents >= 45;
                    const isVip = gVipActive || isPositiveEv;
                    const stakeUsd = kalshiCardStake[g.n] ?? (isVip ? kalshiVipStake : kalshiDefaultStake);
                    const enabled = kalshiCardEnabled[g.n] ?? isPositiveEv;
                    const contracts = Math.max(1, Math.floor((stakeUsd * 100) / Math.max(1, limitCents)));
                    return {
                      gameNo: g.n,
                      date: g.d,
                      homeTeam: g.h,
                      awayTeam: g.a,
                      winnerTeam,
                      winnerCode,
                      ticker,
                      eventTicker: ticker.split("-").slice(0, 2).join("-"),
                      liveAskCents,
                      twinPct,
                      twinTot,
                      hw,
                      aw,
                      f30,
                      a25,
                      agree,
                      evEdge,
                      isComboQualified,
                      isPositiveEv,
                      enabled,
                      stakeUsd,
                      limitCents,
                      contracts,
                    };
                  });

                const dayOrders = buildDayOrders();
                const enabledOrders = dayOrders.filter((o) => o.enabled);
                const totalPlannedUsd = enabledOrders.reduce(
                  (acc, o) => acc + Number(((o.contracts * o.limitCents) / 100).toFixed(2)),
                  0
                );

                const rankedForCombo = [...dayOrders].sort((a, b) => {
                  const aPosEv = a.isPositiveEv ? 1 : 0;
                  const bPosEv = b.isPositiveEv ? 1 : 0;
                  if (bPosEv !== aPosEv) return bPosEv - aPosEv;
                  const aQual = a.isComboQualified ? 1 : 0;
                  const bQual = b.isComboQualified ? 1 : 0;
                  if (bQual !== aQual) return bQual - aQual;
                  const aValid71 = a.twinTot >= 5 && a.twinTot <= 7 && a.twinPct >= 71 && Math.abs(a.hw - a.aw) >= 3 ? 1 : 0;
                  const bValid71 = b.twinTot >= 5 && b.twinTot <= 7 && b.twinPct >= 71 && Math.abs(b.hw - b.aw) >= 3 ? 1 : 0;
                  if (bValid71 !== aValid71) return bValid71 - aValid71;
                  const aAg = a.agree ? 1 : 0;
                  const bAg = b.agree ? 1 : 0;
                  if (bAg !== aAg) return bAg - aAg;
                  if (b.twinPct !== a.twinPct) return b.twinPct - a.twinPct;
                  if (b.evEdge !== a.evEdge) return b.evEdge - a.evEdge;
                  if (b.twinTot !== a.twinTot) return b.twinTot - a.twinTot;
                  return Math.abs(b.f30) - Math.abs(a.f30);
                });

                const getBestComboGameNos = (cnt: number) =>
                  rankedForCombo.slice(0, Math.min(4, Math.max(2, cnt))).map((o) => o.gameNo);

                const qualifiedComboOrders = rankedForCombo.filter((o) => o.isComboQualified);
                const getAutoQualifiedComboGameNos = () => {
                  if (qualifiedComboOrders.length >= 3) {
                    return qualifiedComboOrders.slice(0, 3).map((o) => o.gameNo);
                  }
                  if (qualifiedComboOrders.length === 2) {
                    return qualifiedComboOrders.slice(0, 2).map((o) => o.gameNo);
                  }
                  return getBestComboGameNos(2);
                };

                const activeComboGameNos =
                  comboSelectedByDate[activeDailyDate] && comboSelectedByDate[activeDailyDate].length >= 2
                    ? comboSelectedByDate[activeDailyDate]
                    : getAutoQualifiedComboGameNos();

                const toggleGameInCombo = (gameNo: number) => {
                  const cur = [...activeComboGameNos];
                  const idx = cur.indexOf(gameNo);
                  if (idx >= 0) {
                    if (cur.length <= 2) return;
                    cur.splice(idx, 1);
                  } else {
                    if (cur.length >= 4) {
                      cur.pop();
                    }
                    cur.push(gameNo);
                  }
                  setComboSelectedByDate((prev) => ({ ...prev, [activeDailyDate]: cur }));
                };

                const comboLegOrders = activeComboGameNos
                  .map((gn) => dayOrders.find((o) => o.gameNo === gn))
                  .filter((o): o is NonNullable<typeof o> => Boolean(o));

                const comboFairProb = comboLegOrders.reduce(
                  (acc, o) => acc * Math.min(0.98, Math.max(0.02, (o.liveAskCents || 55) / 100)),
                  1
                );
                const comboFairCents = Math.max(1, Math.min(95, Math.round(comboFairProb * 100)));
                const comboKey = `${activeDailyDate}:${activeComboGameNos.join("-")}`;
                const comboLimitCents = comboCustomLimitCents[comboKey] ?? Math.min(95, comboFairCents + 1);
                const comboContracts = Math.max(1, Math.floor((comboStakeUsd * 100) / Math.max(1, comboLimitCents)));
                const comboEstCostUsd = Number(((comboContracts * comboLimitCents) / 100).toFixed(2));
                const comboMaxPayoutUsd = Number(comboContracts.toFixed(2));
                const comboNetProfitUsd = Number((comboMaxPayoutUsd - comboEstCostUsd).toFixed(2));
                const comboMultiplier = Number((100 / Math.max(1, comboLimitCents)).toFixed(2));

                return (
                  <div className="bg-gradient-to-r from-sky-100/90 via-emerald-50/80 to-sky-100/90 border-2 border-sky-300 rounded-xl p-3.5 space-y-3 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="px-2.5 py-1 rounded bg-emerald-700 text-white font-extrabold text-xs shadow-sm">
                          🤖 اتصال خودکار کارت‌های روز به صرافی Kalshi (سری برد مستقیم تیم: KXATPMATCH / KXWTAMATCH)
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${
                            kalshiHasKey
                              ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                              : "bg-amber-100 text-amber-900 border-amber-300"
                          }`}
                        >
                          {kalshiHasKey ? `کلید متصل ✓ (${kalshiKeyMasked})` : "حالت پیش‌نمایش (Dry-Run • بدون کلید)"}
                        </span>
                        {kalshiBalance !== null && (
                          <span className="px-2 py-0.5 rounded bg-white text-emerald-800 border border-emerald-300 font-mono text-xs font-extrabold">
                            Balance: ${kalshiBalance}
                          </span>
                        )}
                        <span className="text-xs font-mono text-sky-950 bg-white px-2.5 py-0.5 rounded border border-sky-200">
                          کارت‌های انتخابی این روز: <b>{enabledOrders.length}</b> از {dayOrders.length} • کل مبلغ: <b>${totalPlannedUsd.toFixed(2)}</b>
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5">
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              const r = await fetch("/api/kalshi/markets?force=1");
                              if (r.ok) {
                                const d = await r.json();
                                if (d?.markets && Object.keys(d.markets).length > 0) {
                                  setKalshiMarkets(d.markets);
                                  return;
                                }
                              }
                            } catch {}
                            try {
                              const r2 = await fetch("/tennis_atp_predictions.json?t=" + Date.now());
                              if (r2.ok) {
                                const d2 = await r2.json();
                                if (d2?.markets) setKalshiMarkets(d2.markets);
                              }
                            } catch {}
                          }}
                          className="px-2.5 py-1 rounded bg-white hover:bg-sky-50 text-sky-900 border border-sky-300 text-[11px] font-bold"
                        >
                          🔄 بروزرسانی قیمت‌های لحظه‌ای Kalshi ({Object.keys(kalshiMarkets).length} بازار باز)
                        </button>

                        <button
                          type="button"
                          onClick={() => setKalshiConfigOpen((v) => !v)}
                          className="px-2.5 py-1 rounded bg-sky-700 hover:bg-sky-800 text-white text-[11px] font-bold shadow-sm"
                        >
                          {kalshiConfigOpen ? "بستن تنظیمات Kalshi ▲" : "⚙️ تنظیم کلید API و زمان‌بند خودکار ▼"}
                        </button>
                      </div>
                    </div>

                    {/* Action Bar for Selecting, Saving, Dry-Running, and Live Executing Daily Cards on Kalshi */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-sky-200/80">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => {
                            const next: Record<number, boolean> = { ...kalshiCardEnabled };
                            gamesOnDailyDate.forEach((g) => {
                              next[g.n] = true;
                            });
                            setKalshiCardEnabled(next);
                          }}
                          className="px-2.5 py-1 rounded bg-white hover:bg-sky-50 text-sky-950 border border-sky-300 text-[11px] font-bold"
                        >
                          ✓ انتخاب همه کارت‌های روز ({gamesOnDailyDate.length})
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            const next: Record<number, boolean> = { ...kalshiCardEnabled };
                            dayOrders.forEach((o) => {
                              next[o.gameNo] = Boolean(o.isPositiveEv);
                            });
                            setKalshiCardEnabled(next);
                          }}
                          className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white border border-emerald-700 text-[11px] font-extrabold shadow-sm"
                        >
                          فقط ارزش مثبت سیستم جدید (+EV) ({dayOrders.filter((o) => o.isPositiveEv).length})
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            const next: Record<number, boolean> = { ...kalshiCardEnabled };
                            dayOrders.forEach((o) => {
                              next[o.gameNo] = Boolean(o.isComboQualified);
                            });
                            setKalshiCardEnabled(next);
                          }}
                          className="px-2.5 py-1 rounded bg-white hover:bg-emerald-50 text-emerald-900 border border-emerald-300 text-[11px] font-bold"
                        >
                          فقط تاییدشده سیستم جدید (۶۲٫۵٪ • VIP ۷۲٪) ({dayOrders.filter((o) => o.isComboQualified).length})
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            const next: Record<number, boolean> = { ...kalshiCardEnabled };
                            gamesOnDailyDate.forEach((g) => {
                              next[g.n] = false;
                            });
                            setKalshiCardEnabled(next);
                          }}
                          className="px-2.5 py-1 rounded bg-white hover:bg-rose-50 text-rose-800 border border-rose-200 text-[11px] font-bold"
                        >
                          لغو انتخاب همه
                        </button>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        {/* 1. Save Plan to Server */}
                        <button
                          type="button"
                          disabled={kalshiBusy}
                          onClick={async () => {
                            setKalshiBusy(true);
                            try {
                              const r = await fetch("/api/kalshi/save-plan", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ date: activeDailyDate, orders: dayOrders }),
                              });
                              const d = await r.json();
                              setKalshiExecReport({
                                mode: "save",
                                results: [],
                                summary: {
                                  message: `برنامه ${d.savedCount ?? enabledOrders.length} کارت تاریخ ${activeDailyDate} با موفقیت روی سرور ذخیره و قفل شد.`,
                                },
                              });
                            } finally {
                              setKalshiBusy(false);
                            }
                          }}
                          className="px-3 py-1.5 rounded-md bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs shadow-sm"
                        >
                          💾 ذخیره و قفل برنامه کارت‌ها در سرور
                        </button>

                        {/* 2. Dry-Run Preview on Live Kalshi Orderbook */}
                        <button
                          type="button"
                          disabled={kalshiBusy}
                          onClick={async () => {
                            setKalshiBusy(true);
                            try {
                              let handled = false;
                              try {
                                const r = await fetch("/api/kalshi/execute", {
                                  method: "POST",
                                  headers: { "Content-Type": "application/json" },
                                  body: JSON.stringify({
                                    date: activeDailyDate,
                                    orders: dayOrders,
                                    mode: "dry_run",
                                  }),
                                });
                                if (r.ok) {
                                  const d = await r.json();
                                  if (d?.ok) {
                                    setKalshiExecReport(d);
                                    handled = true;
                                  }
                                }
                              } catch {}
                              if (!handled) {
                                const results = enabledOrders.map((ord) => {
                                  const mkt = kalshiMarkets[ord.ticker];
                                  const estCostUsd = Number(((ord.contracts * ord.limitCents) / 100).toFixed(2));
                                  const potentialProfitUsd = Number(((ord.contracts * (100 - ord.limitCents)) / 100).toFixed(2));
                                  return {
                                    gameNo: ord.gameNo,
                                    ticker: ord.ticker,
                                    winnerTeam: ord.winnerTeam,
                                    contracts: ord.contracts,
                                    limitCents: ord.limitCents,
                                    estCostUsd,
                                    potentialProfitUsd,
                                    message: mkt
                                      ? `آماده ارسال ✓: خرید ${ord.contracts} قرارداد YES @ ${ord.limitCents}¢ (هزینه: $${estCostUsd} • سود خالص برد: +$${potentialProfitUsd})`
                                      : `تخمین @ ${ord.limitCents}¢: خرید ${ord.contracts} قرارداد YES (هزینه: $${estCostUsd} • سود: +$${potentialProfitUsd})`,
                                  };
                                });
                                setKalshiExecReport({
                                  mode: "dry_run",
                                  results,
                                  summary: {
                                    message: `پیش‌نمایش ${results.length} سفارش انتخابی تاریخ ${activeDailyDate} با قیمت‌های زنده اوردربوک Kalshi محاسبه شد.`,
                                  },
                                });
                              }
                            } finally {
                              setKalshiBusy(false);
                            }
                          }}
                          className="px-3 py-1.5 rounded-md bg-amber-500 hover:bg-amber-600 text-slate-950 font-extrabold text-xs shadow-sm"
                        >
                          🧪 تست و پیش‌نمایش سفارش‌ها در Kalshi (Dry-Run)
                        </button>

                        {/* 3. Live Order Submission to Kalshi */}
                        <button
                          type="button"
                          disabled={kalshiBusy || enabledOrders.length === 0}
                          onClick={async () => {
                            setKalshiBusy(true);
                            try {
                              const r = await fetch("/api/kalshi/execute", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                  date: activeDailyDate,
                                  orders: dayOrders,
                                  mode: "live",
                                }),
                              });
                              const d = await r.json();
                              setKalshiExecReport(d);
                              const stR = await fetch("/api/kalshi/state");
                              const stD = await stR.json();
                              if (stD?.ledger) setKalshiLedger(stD.ledger);
                            } finally {
                              setKalshiBusy(false);
                            }
                          }}
                          className="px-3.5 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-extrabold text-xs shadow-sm"
                        >
                          🚀 ثبت خودکار سفارش‌های انتخابی در Kalshi ({enabledOrders.length} بازی)
                        </button>
                      </div>
                    </div>

                    {/* Collapsible Kalshi API Key & Auto-Scheduler Drawer */}
                    {kalshiConfigOpen && (
                      <div className="bg-white rounded-lg border border-sky-300 p-3.5 space-y-3 text-xs">
                        <div className="font-bold text-sky-950 border-b border-sky-100 pb-1.5">
                          تنظیمات کلید API صرافی Kalshi (امضای RSA-PSS در بک‌اند سرور) و زمان‌بند اجرای خودکار روزانه
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] font-semibold text-slate-700">
                              KALSHI API Key ID:
                            </label>
                            <Input
                              value={kalshiKeyIdInput}
                              onChange={(e) => setKalshiKeyIdInput(e.target.value)}
                              placeholder={kalshiKeyMasked || "e.g. a9b8c7d6-..."}
                              className="h-8 text-xs font-mono"
                              dir="ltr"
                            />
                          </div>

                          <div className="flex flex-col gap-1 md:col-span-2">
                            <label className="text-[11px] font-semibold text-slate-700">
                              RSA Private Key (PEM — کلید خصوصی فقط در سرور ذخیره می‌شود):
                            </label>
                            <textarea
                              value={kalshiPemInput}
                              onChange={(e) => setKalshiPemInput(e.target.value)}
                              placeholder="-----BEGIN RSA PRIVATE KEY----- ..."
                              rows={2}
                              className="rounded border border-slate-300 p-1.5 text-[10px] font-mono"
                              dir="ltr"
                            />
                          </div>

                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] font-semibold text-slate-700">
                              محیط صرافی (Environment):
                            </label>
                            <select
                              value={kalshiEnv}
                              onChange={(e) => setKalshiEnv(e.target.value as "live" | "demo")}
                              className="h-8 rounded border border-slate-300 px-2 text-xs font-mono"
                              dir="ltr"
                            >
                              <option value="live">LIVE (api.elections.kalshi.com)</option>
                              <option value="demo">DEMO (demo-api.kalshi.co)</option>
                            </select>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 items-end pt-1">
                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] font-semibold text-slate-700">
                              مبلغ پیش‌فرض هر کارت عادی ($ USD):
                            </label>
                            <Input
                              type="number"
                              min={1}
                              max={250}
                              value={kalshiDefaultStake}
                              onChange={(e) => setKalshiDefaultStake(Number(e.target.value) || 3)}
                              className="h-8 text-xs font-mono"
                              dir="ltr"
                            />
                          </div>

                          <div className="flex flex-col gap-1">
                            <label className="text-[11px] font-semibold text-slate-700">
                              مبلغ کارت‌های VIP / هم‌جهت ($ USD):
                            </label>
                            <Input
                              type="number"
                              min={1}
                              max={500}
                              value={kalshiVipStake}
                              onChange={(e) => setKalshiVipStake(Number(e.target.value) || 6)}
                              className="h-8 text-xs font-mono"
                              dir="ltr"
                            />
                          </div>

                          <div className="flex items-center gap-2 h-8">
                            <input
                              id="kalshi-auto-sched"
                              type="checkbox"
                              checked={kalshiAutoEnabled}
                              onChange={(e) => setKalshiAutoEnabled(e.target.checked)}
                              className="h-4 w-4"
                            />
                            <label htmlFor="kalshi-auto-sched" className="text-xs font-bold text-sky-950 cursor-pointer">
                              اجرای خودکار روزانه در ساعت (ET):
                            </label>
                            <input
                              type="time"
                              value={kalshiAutoTimeEt}
                              onChange={(e) => setKalshiAutoTimeEt(e.target.value)}
                              className="h-8 rounded border border-slate-300 px-2 text-xs font-mono"
                              dir="ltr"
                            />
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={async () => {
                                const r = await fetch("/api/kalshi/config", {
                                  method: "POST",
                                  headers: { "Content-Type": "application/json" },
                                  body: JSON.stringify({
                                    keyId: kalshiKeyIdInput,
                                    privateKeyPem: kalshiPemInput,
                                    env: kalshiEnv,
                                    defaultStakeUsd: kalshiDefaultStake,
                                    vipStakeUsd: kalshiVipStake,
                                    autoScheduleEnabled: kalshiAutoEnabled,
                                    autoScheduleTimeEt: kalshiAutoTimeEt,
                                  }),
                                });
                                const d = await r.json();
                                if (d?.ok) {
                                  setKalshiHasKey(Boolean(d.hasKey));
                                  setKalshiKeyMasked(d.keyIdMasked ?? "");
                                  setKalshiKeyIdInput("");
                                  setKalshiPemInput("");
                                }
                              }}
                              className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs"
                            >
                              ذخیره تنظیمات در سرور ✓
                            </button>

                            <button
                              type="button"
                              onClick={async () => {
                                const r = await fetch("/api/kalshi/balance", { method: "POST" });
                                const d = await r.json();
                                if (d?.ok) setKalshiBalance(d.balanceUsd);
                                else setKalshiExecReport({ mode: "balance_err", results: [], error: d?.error ?? "خطا در دریافت موجودی" });
                              }}
                              className="px-3 py-1.5 rounded bg-sky-100 hover:bg-sky-200 text-sky-950 border border-sky-300 font-bold text-xs"
                            >
                              استعلام موجودی Kalshi
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Execution / Dry-Run Report Box */}
                    {kalshiExecReport && (
                      <div className="bg-white rounded-lg border border-sky-300 p-3 space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-extrabold text-sky-950">
                            {kalshiExecReport.mode === "dry_run"
                              ? "🧪 گزارش پیش‌نمایش و شبیه‌سازی سفارش‌ها در Kalshi (Dry-Run)"
                              : kalshiExecReport.mode === "live"
                                ? "🚀 گزارش ثبت سفارش واقعی در Kalshi"
                                : "ℹ️ پیام سیستم Kalshi"}
                          </span>
                          <button
                            type="button"
                            onClick={() => setKalshiExecReport(null)}
                            className="text-slate-500 hover:text-slate-800 text-[11px]"
                          >
                            بستن ✕
                          </button>
                        </div>

                        {kalshiExecReport.error && (
                          <div className="p-2 rounded bg-rose-50 border border-rose-300 text-rose-900 font-bold">
                            {kalshiExecReport.error}
                          </div>
                        )}

                        {kalshiExecReport.summary?.message && (
                          <div className="p-2 rounded bg-emerald-50 border border-emerald-300 text-emerald-900 font-bold">
                            {kalshiExecReport.summary.message}
                          </div>
                        )}

                        {kalshiExecReport.results && kalshiExecReport.results.length > 0 && (
                          <div className="overflow-x-auto max-h-56" dir="ltr">
                            <table className="w-full text-[11px] font-mono text-left border-collapse">
                              <thead className="bg-sky-50 text-sky-950 border-b border-sky-200">
                                <tr>
                                  <th className="p-1.5">Game</th>
                                  <th className="p-1.5">Kalshi Ticker (KXATPMATCH / KXWTAMATCH)</th>
                                  <th className="p-1.5">Pick (YES)</th>
                                  <th className="p-1.5">Contracts × Limit</th>
                                  <th className="p-1.5">Est. Cost</th>
                                  <th className="p-1.5">Net Profit</th>
                                  <th className="p-1.5">Status</th>
                                </tr>
                              </thead>
                              <tbody>
                                {kalshiExecReport.results.map((r, i) => (
                                  <tr key={i} className="border-b border-sky-100">
                                    <td className="p-1.5 font-bold">#{r.gameNo}</td>
                                    <td className="p-1.5 font-bold text-sky-900">{r.ticker}</td>
                                    <td className="p-1.5 text-emerald-800 font-bold">{r.winnerTeam}</td>
                                    <td className="p-1.5">
                                      {r.contracts ? `${r.contracts} × ${r.limitCents}¢` : "—"}
                                    </td>
                                    <td className="p-1.5 font-bold">${r.estCostUsd ?? "—"}</td>
                                    <td className="p-1.5 text-emerald-700 font-bold">
                                      {r.potentialProfitUsd ? `+$${r.potentialProfitUsd}` : "—"}
                                    </td>
                                    <td className="p-1.5">{r.message}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}

                    {/* ==================================================================== */}
                    {/* KALSHI COMBO / PARLAY BUILDER (۲ تا ۴ بازی • انتخاب خودکار ۱۰۰٪ + دستی) */}
                    {/* ==================================================================== */}
                    <div className="bg-gradient-to-r from-indigo-50/95 via-sky-50/95 to-emerald-50/95 border-2 border-indigo-300 rounded-xl p-3 space-y-2.5 shadow-sm">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setComboOpen((v) => !v)}
                            className="px-2.5 py-1 rounded-md bg-indigo-700 hover:bg-indigo-800 text-white font-extrabold text-xs shadow-sm flex items-center gap-1.5"
                          >
                            <span>کمبوساز هوشمند و دستی Kalshi (Parlay / میکس ۲ تا ۴ بازی)</span>
                            <span>{comboOpen ? "▲" : "▼"}</span>
                          </button>
                          <span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-950 border border-indigo-300 text-[11px] font-bold">
                            پیش‌فرض خودکار: بازی‌های تاییدشده سیستم جدید NBA ({qualifiedComboOrders.length} بازی واجد شرایط در این روز)
                          </span>
                          <span className="px-2.5 py-0.5 rounded bg-white border border-indigo-200 font-mono text-xs text-indigo-950 font-extrabold">
                            کمبو فعال: {comboLegOrders.length} بازی • ضریب: {comboMultiplier}x • قیمت منصفانه: {comboFairCents}¢
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => {
                              setComboOpen(true);
                              setComboSelectedByDate((prev) => ({
                                ...prev,
                                [activeDailyDate]: getAutoQualifiedComboGameNos(),
                              }));
                            }}
                            className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-extrabold shadow-sm"
                          >
                            انتخاب خودکار سیستم جدید ({qualifiedComboOrders.length >= 3 ? "۳ بازی" : "۲ بازی"})
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setComboOpen(true);
                              setComboSelectedByDate((prev) => ({
                                ...prev,
                                [activeDailyDate]: getBestComboGameNos(3),
                              }));
                            }}
                            className="px-2 py-1 rounded bg-white hover:bg-indigo-50 text-indigo-900 border border-indigo-300 text-[11px] font-bold"
                          >
                            ۳ بازی برتر
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setComboOpen(true);
                              setComboSelectedByDate((prev) => ({
                                ...prev,
                                [activeDailyDate]: getBestComboGameNos(2),
                              }));
                            }}
                            className="px-2 py-1 rounded bg-white hover:bg-indigo-50 text-indigo-900 border border-indigo-300 text-[11px] font-bold"
                          >
                            بهترین ۲ بازی
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setComboOpen(true);
                              setComboSelectedByDate((prev) => ({
                                ...prev,
                                [activeDailyDate]: getBestComboGameNos(4),
                              }));
                            }}
                            className="px-2 py-1 rounded bg-white hover:bg-indigo-50 text-indigo-900 border border-indigo-300 text-[11px] font-bold"
                          >
                            بهترین ۴ بازی
                          </button>
                        </div>
                      </div>

                      {comboOpen && (
                        <div className="space-y-2.5 pt-2 border-t border-indigo-200/80">
                          <div>
                            <div className="text-[11px] font-bold text-indigo-950 mb-1.5">
                              انتخاب دستی ۲ تا ۴ بازی برای کمبو (روی هر بازی کلیک کنید تا به بسته کمبو اضافه یا از آن حذف شود — حداقل ۲ و حداکثر ۴ بازی):
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-1.5">
                              {rankedForCombo.map((ord) => {
                                const legIdx = activeComboGameNos.indexOf(ord.gameNo);
                                const isSel = legIdx >= 0;
                                const isTop100Agree = ord.twinPct === 100 && ord.agree;
                                return (
                                  <button
                                    key={ord.gameNo}
                                    type="button"
                                    onClick={() => toggleGameInCombo(ord.gameNo)}
                                    className={`text-right p-1.5 rounded-lg border transition-all flex flex-col justify-between ${
                                      isSel
                                        ? "bg-indigo-700 text-white border-indigo-900 shadow-sm ring-2 ring-indigo-300"
                                        : isTop100Agree
                                          ? "bg-emerald-50/90 hover:bg-emerald-100 text-slate-900 border-emerald-400"
                                          : "bg-white hover:bg-sky-50 text-slate-800 border-slate-300"
                                    }`}
                                  >
                                    <div className="flex items-center justify-between gap-1 w-full">
                                      <span className="font-mono text-[10px] font-extrabold">
                                        #{ord.gameNo} {isSel ? `• Leg ${legIdx + 1} ✓` : ""}
                                      </span>
                                      <span
                                        className={`px-1 py-0.2 rounded text-[9px] font-mono font-extrabold ${
                                          isSel
                                            ? "bg-amber-300 text-slate-950"
                                            : ord.twinPct === 100
                                              ? "bg-emerald-200 text-emerald-950"
                                              : "bg-slate-200 text-slate-700"
                                        }`}
                                      >
                                        {ord.twinPct}% ({ord.twinTot})
                                      </span>
                                    </div>
                                    <div className="font-extrabold text-[11px] truncate mt-0.5">
                                      🎯 {ord.winnerTeam}
                                    </div>
                                    <div className="flex items-center justify-between gap-1 mt-1 text-[9px] font-mono">
                                      <span className={isSel ? "text-indigo-100" : "text-slate-600"}>
                                        Ask:{ord.liveAskCents}¢ ({ord.evEdge >= 0 ? `+${ord.evEdge}` : ord.evEdge}% EV)
                                      </span>
                                      <span
                                        className={`font-bold ${
                                          ord.isPositiveEv
                                            ? isSel
                                              ? "text-emerald-300"
                                              : "text-emerald-700"
                                            : ord.isComboQualified
                                              ? isSel
                                                ? "text-amber-200"
                                                : "text-emerald-700"
                                              : isSel
                                                ? "text-indigo-200"
                                                : "text-slate-500"
                                        }`}
                                      >
                                        {ord.isPositiveEv ? "+EV ✓" : ord.isComboQualified ? "تایید سیستم ✓" : "خارج از فیلتر"}
                                      </span>
                                    </div>
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          <div className="bg-white border border-indigo-200 rounded-lg p-2.5 flex flex-wrap items-center justify-between gap-3">
                            <div className="flex flex-wrap items-center gap-1.5">
                              {comboLegOrders.map((leg, i) => (
                                <Fragment key={leg.gameNo}>
                                  {i > 0 && (
                                    <span className="font-extrabold text-indigo-700 text-sm px-0.5">×</span>
                                  )}
                                  <div className="px-2.5 py-1 rounded-md bg-indigo-50 border border-indigo-300 text-xs">
                                    <div className="font-extrabold text-indigo-950">
                                      {i + 1}. {leg.winnerTeam}{" "}
                                      <span className="font-mono text-[10px] text-indigo-700">(#{leg.gameNo})</span>
                                    </div>
                                    <div className="text-[10px] font-mono text-slate-700">
                                      قیمت: <b>{leg.liveAskCents}¢</b> • همزاد: <b>{leg.twinPct}% ({leg.twinTot})</b>{" "}
                                      {leg.agree ? "• ✓ هم‌جهت" : ""}
                                    </div>
                                  </div>
                                </Fragment>
                              ))}
                              <span className="font-extrabold text-indigo-700 text-sm px-1">=</span>
                              <div className="px-3 py-1 rounded-md bg-emerald-50 border border-emerald-400 text-xs">
                                <div className="font-extrabold text-emerald-950">
                                  قیمت منصفانه کمبو: <span className="font-mono">{comboFairCents}¢</span> (ضریب: <span className="font-mono">{comboMultiplier}x</span>)
                                </div>
                                <div className="text-[10px] font-mono text-emerald-800">
                                  خرید {comboContracts} قرارداد کمبو @ {comboLimitCents}¢ ➔ هزینه: <b>${comboEstCostUsd}</b> • دریافتی برد: <b>${comboMaxPayoutUsd}</b> (سود خالص: <b>+${comboNetProfitUsd}</b>)
                                </div>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                              <div className="bg-slate-50 border border-slate-300 rounded px-2 py-1">
                                <label className="block text-[9px] text-slate-600 font-bold">مبلغ کل کمبو ($)</label>
                                <input
                                  type="number"
                                  min={1}
                                  max={250}
                                  step={0.5}
                                  value={comboStakeUsd}
                                  onChange={(e) => setComboStakeUsd(Math.max(1, Number(e.target.value) || 4))}
                                  className="w-16 text-xs font-mono font-extrabold text-indigo-950 bg-transparent outline-none"
                                />
                              </div>

                              <div className="bg-slate-50 border border-slate-300 rounded px-2 py-1">
                                <label className="block text-[9px] text-slate-600 font-bold">قیمت لیمیت کمبو (¢)</label>
                                <input
                                  type="number"
                                  min={1}
                                  max={98}
                                  value={comboLimitCents}
                                  onChange={(e) =>
                                    setComboCustomLimitCents((prev) => ({
                                      ...prev,
                                      [comboKey]: Math.min(98, Math.max(1, Number(e.target.value) || comboFairCents)),
                                    }))
                                  }
                                  className="w-14 text-xs font-mono font-extrabold text-indigo-950 bg-transparent outline-none"
                                />
                              </div>

                              <button
                                type="button"
                                disabled={kalshiBusy || comboLegOrders.length < 2}
                                onClick={async () => {
                                  setKalshiBusy(true);
                                  try {
                                    const r = await fetch("/api/kalshi/combo", {
                                      method: "POST",
                                      headers: { "Content-Type": "application/json" },
                                      body: JSON.stringify({
                                        date: activeDailyDate,
                                        legs: comboLegOrders.map((l) => ({
                                          gameNo: l.gameNo,
                                          eventTicker: l.eventTicker,
                                          marketTicker: l.ticker,
                                          winnerTeam: l.winnerTeam,
                                          yesAskCents: l.liveAskCents,
                                          twinPct: l.twinPct,
                                          agree: l.agree,
                                        })),
                                        stakeUsd: comboStakeUsd,
                                        limitCents: comboLimitCents,
                                        mode: "dry_run",
                                      }),
                                    });
                                    const d = await r.json();
                                    setComboReport(d);
                                  } finally {
                                    setKalshiBusy(false);
                                  }
                                }}
                                className="px-3 py-1.5 rounded-md bg-amber-500 hover:bg-amber-600 text-slate-950 font-extrabold text-xs shadow-sm"
                              >
                                🧪 استعلام تیکر و پیش‌نمایش کمبو ({comboLegOrders.length} بازی)
                              </button>

                              <button
                                type="button"
                                disabled={kalshiBusy || comboLegOrders.length < 2}
                                onClick={async () => {
                                  setKalshiBusy(true);
                                  try {
                                    const r = await fetch("/api/kalshi/combo", {
                                      method: "POST",
                                      headers: { "Content-Type": "application/json" },
                                      body: JSON.stringify({
                                        date: activeDailyDate,
                                        legs: comboLegOrders.map((l) => ({
                                          gameNo: l.gameNo,
                                          eventTicker: l.eventTicker,
                                          marketTicker: l.ticker,
                                          winnerTeam: l.winnerTeam,
                                          yesAskCents: l.liveAskCents,
                                          twinPct: l.twinPct,
                                          agree: l.agree,
                                        })),
                                        stakeUsd: comboStakeUsd,
                                        limitCents: comboLimitCents,
                                        mode: "live",
                                      }),
                                    });
                                    const d = await r.json();
                                    setComboReport(d);
                                    const balR = await fetch("/api/kalshi/balance", { method: "POST" });
                                    const balD = await balR.json();
                                    if (balD?.ok) setKalshiBalance(balD.balanceUsd);
                                  } finally {
                                    setKalshiBusy(false);
                                  }
                                }}
                                className="px-3.5 py-1.5 rounded-md bg-indigo-700 hover:bg-indigo-800 text-white font-extrabold text-xs shadow-sm"
                              >
                                🚀 ثبت سفارش کمبو ({comboLegOrders.length} بازی) در Kalshi
                              </button>
                            </div>
                          </div>

                          {comboReport && (
                            <div
                              className={`p-2.5 rounded-lg border text-xs font-mono ${
                                comboReport.ok
                                  ? "bg-emerald-50 border-emerald-400 text-emerald-950"
                                  : "bg-rose-50 border-rose-300 text-rose-900"
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-extrabold">
                                  {comboReport.message ?? comboReport.error}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => setComboReport(null)}
                                  className="text-[11px] text-slate-600 hover:text-slate-900 font-bold"
                                >
                                  بستن ✕
                                </button>
                              </div>
                              {comboReport.comboTicker && (
                                <div className="mt-1 text-[11px] text-indigo-900">
                                  Combo Ticker: <b>{comboReport.comboTicker}</b>{" "}
                                  {comboReport.orderId ? `• Order ID: ${comboReport.orderId}` : ""}{" "}
                                  {comboReport.rfqId ? `• RFQ ID: ${comboReport.rfqId}` : ""}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* Daily Cards Grid (2 to 3 Cards per Row, Exact GOLD-FORMULA-PRIORITY Card Structure in Light Pale-Blue) */}
              {histLoading ? (
                <div className="p-6 text-center text-xs text-sky-800 bg-white rounded-lg border border-sky-200 flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> در حال محاسبه کارت‌های روزانه از ۲۱٬۴۹۸ بازی تاریخی...
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
                  {[...gamesOnDailyDate]
                    .map((g) => {
                      const t12 = (manualPersp === "home" ? g.h_12 : g.a_12) ?? [];
                      const tGeoFin = (manualPersp === "home" ? g.h_geo : g.a_geo) ?? "";
                      const tGeoDyn = (manualPersp === "home" ? (g.h_geo_dyn ?? g.h_geo) : (g.a_geo_dyn ?? g.a_geo)) ?? "";
                      const tGeoTab = (manualPersp === "home" ? g.h_geo_tab : g.a_geo_tab) ?? "";
                      const activeGeoKind: "fin" | "dyn" = dailyCardMode === "geo_dyn" ? "dyn" : manualGeoKind;
                      const dPool = getDayPoolBefore(g.day, g.d);
                      const savedState = manualFilters[g.n];
                      const rowGeoKind: "fin" | "dyn" = savedState?.geoKind ?? activeGeoKind;
                      const getRowEl12 = (r: HistGameRow) => (manualPersp === "home" ? r.h12 : r.a12);
                      const getRowGeo = (r: HistGameRow) =>
                        manualPersp === "home"
                          ? rowGeoKind === "dyn"
                            ? r.hGeoDyn ?? r.hGeo
                            : r.hGeo
                          : rowGeoKind === "dyn"
                            ? r.aGeoDyn ?? r.aGeo
                            : r.aGeo;
                      const getRowGeoTab = (r: HistGameRow) =>
                        manualPersp === "home" ? (r.hGeoTab ?? "") : (r.aGeoTab ?? "");

                      const ch3 = computeThreeChannelIndex(t12, tGeoFin, tGeoDyn, dPool, manualPersp, tGeoTab);
                      const autoChosen =
                        dailyCardMode === "geo_tab"
                          ? ch3.geoTab
                          : dailyCardMode === "geo"
                            ? ch3.geoFin
                            : dailyCardMode === "geo_dyn"
                              ? ch3.geoDyn
                              : ch3.step;

                      const hasManualFilter = Boolean(
                        savedState &&
                          (Object.values(savedState.cols).some((v) => v && v !== "ALL") ||
                            (savedState.geo && savedState.geo !== "ALL") ||
                            (savedState.geoTab && savedState.geoTab !== "ALL"))
                      );

                      const isNhlSysMode =
                        dailyCardMode === "nhl_best" ||
                        dailyCardMode === "nhl_vip3" ||
                        dailyCardMode === "nhl_f1_guard" ||
                        dailyCardMode === "nhl_f1_idx_raw" ||
                        dailyCardMode === "nhl_f1" ||
                        dailyCardMode === "nhl_f1_union";

                      const f1Pool = isNhlSysMode && manualPersp === "home" ? resolveNhlF1Pool(g, dPool) : null;
                      let cardPool = f1Pool ?? autoChosen.pool;
                      let manualOverridden = false;

                      if (hasManualFilter && savedState) {
                        const manualPool = dPool.filter((r) => {
                          const el = getRowEl12(r);
                          for (let c = 0; c < 12; c++) {
                            const sel = savedState.cols[c];
                            if (sel && sel !== "ALL" && el[c] !== sel) return false;
                          }
                          if (savedState.geo && savedState.geo !== "ALL" && getRowGeo(r) !== savedState.geo) {
                            return false;
                          }
                          if (savedState.geoTab && savedState.geoTab !== "ALL" && getRowGeoTab(r) !== savedState.geoTab) {
                            return false;
                          }
                          return true;
                        });
                        if (manualPool.length >= 5 && manualPool.length <= 7) {
                          cardPool = manualPool;
                          manualOverridden = true;
                        }
                      }

                      const isNaturalPool = Boolean(f1Pool) || manualOverridden || autoChosen.isNatural57;
                      const cardIdx = computePoolNumIndex(cardPool);
                      const hw = cardPool.filter((r) => r.mg > 0).length;
                      const aw = cardPool.filter((r) => r.mg < 0).length;
                      const tot = hw + aw;
                      const pct = tot > 0 ? Math.round((Math.max(hw, aw) / tot) * 100) : 50;

                      const hpElePCode = "";
                      const apElePCode = "";
                      const nat3Cnt = g.idx3?.nat ?? ch3.natCount;
                      const minD3Val = g.idx3?.minD ?? ch3.minDelta;

                      const baseHomeFav =
                        isNhlSysMode && !manualOverridden && g.sys_win
                          ? g.sys_win === g.h
                          : hw > aw
                            ? true
                            : aw > hw
                              ? false
                              : (g.f30 ?? 0) >= 0;
                      const homeFav = cardFlipDir[g.n] ? !baseHomeFav : baseHomeFav;
                      const predTeam = homeFav ? g.h : g.a;
                      const predRole = homeFav ? "برد میزبان" : "برد میهمان";

                      const trapNoNat3 = Boolean(g.trap_tag);
                      const trapEven6 = false;
                      const trapBlind100 = false;
                      const trapPas0000 = false;
                      const hasInternalTrap = Boolean(g.trap_tag);

                      const rawWtp = activeWtpOf(g) ?? {
                        mon: g.d,
                        htp: 50,
                        atp: 50,
                        dtp: 0,
                        hrk: 15,
                        ark: 15,
                        hwl: "0-0",
                        awl: "0-0",
                        hpct: 50,
                        apct: 50,
                        hel: "AIR",
                        ael: "AIR",
                        l5h: 50,
                        hodds: 1.83,
                        aodds: 2.20,
                        mel: "WATER",
                      };
                      const rawL5H = typeof rawWtp.l5h === "number" ? rawWtp.l5h : 50;
                      const l5Pick = Math.round((homeFav ? rawL5H : 100 - rawL5H) * 10) / 10;
                      const matchElem: "FIRE" | "AIR" | "WATER" | "EARTH" =
                        l5Pick >= 58 ? "FIRE" : l5Pick >= 51 ? "AIR" : l5Pick >= 44 ? "WATER" : "EARTH";
                      const elemFaMap: Record<string, string> = {
                        FIRE: "آتش FIRE",
                        AIR: "هوا AIR",
                        WATER: "آب WATER",
                        EARTH: "خاک EARTH",
                      };
                      const wtpObj = {
                        ...rawWtp,
                        dtp: cardFlipDir[g.n] ? -rawWtp.dtp : rawWtp.dtp,
                        l5Pick,
                        matchElem,
                        matchElemFa: elemFaMap[matchElem] || matchElem,
                        hel: rawWtp.hel || "AIR",
                        ael: rawWtp.ael || "AIR",
                        hodds: typeof rawWtp.hodds === "number" ? rawWtp.hodds : 1.83,
                        aodds: typeof rawWtp.aodds === "number" ? rawWtp.aodds : 2.20,
                      };
                      const trapWeeklyMismatch =
                        typeof rawWtp.l5h === "number" ? matchElem === "EARTH" : wtpObj.dtp <= -8.0;

                      const isVip3 = activeVip3Of(g);
                      const isBestGuard = Boolean(g.f1_guard);
                      const isBestWtp = activeF1WtpOf(g);
                      const isRawF1Idx = Boolean(g.f1_idx);
                      const isBaseF1 = Boolean(g.f1);
                      const isUnionSys = activeUnionOf(g);
                      const isFilteredOutByWeekly = Boolean((isBestGuard || g.idx_rescue) && trapWeeklyMismatch);
                      const isFilteredOutByTrap = Boolean(isBaseF1 && hasInternalTrap);
                      const isFilteredOutByIdx = Boolean(isBaseF1 && !isRawF1Idx && !isBestGuard);
                      const isIdxRescueOnly = Boolean(!g.f1 && g.idx_rescue);

                      const manualNaturalQual =
                        tot >= 5 &&
                        tot <= 7 &&
                        pct >= 71 &&
                        Math.abs(hw - aw) >= 3 &&
                        !hasInternalTrap &&
                        !trapWeeklyMismatch;

                      const isQualified =
                        manualOverridden || !isNhlSysMode
                          ? manualNaturalQual
                          : dailyCardMode === "nhl_vip3"
                            ? isVip3
                            : dailyCardMode === "nhl_best"
                              ? isBestWtp
                              : dailyCardMode === "nhl_f1_guard"
                                ? isBestGuard
                                : dailyCardMode === "nhl_f1_idx_raw"
                                  ? isRawF1Idx
                                  : dailyCardMode === "nhl_f1_union"
                                    ? isUnionSys
                                    : isBaseF1;

                      const isBorderlineRescued = Boolean(
                        isQualified && (g.is_nat === false || g.b2b_tag === "B2B_PICK" || isIdxRescueOnly)
                      );
                      const isVipMismatchRescue = false;
                      const calibratedWinPct =
                        isQualified && (isVip3 || wtpObj.matchElem === "FIRE")
                          ? 78.5
                          : isQualified && wtpObj.matchElem === "WATER"
                            ? 70.5
                            : isBorderlineRescued
                              ? 71.5
                              : isQualified
                                ? 74.5
                                : 50.0;
                      const maxBuyCents =
                        isQualified && (isVip3 || wtpObj.matchElem === "FIRE")
                          ? 76
                          : isQualified && wtpObj.matchElem === "WATER"
                            ? 68
                            : isBorderlineRescued
                              ? 69
                              : isQualified
                                ? 72
                                : 0;

                      const kalshiTicker = buildKalshiNbaTicker(g.d, g.a, g.h, predTeam, ((g as any).tour === "WTA" || tour === "WTA") ? "WTA" : "ATP");
                      const mktInfo = kalshiMarkets[kalshiTicker];
                      const liveAsk = mktInfo && mktInfo.yesAskCents > 0 ? mktInfo.yesAskCents : 55;
                      const isUnderdogCaution = liveAsk < 45;
                      const evEdge = Math.round(calibratedWinPct - liveAsk);
                      const isPosEv = isQualified && liveAsk <= maxBuyCents && !isUnderdogCaution;

                      const hasFinalScore = Boolean(g.done && g.st !== "PENDING" && g.aw);
                      const cardWon = !hasFinalScore ? null : predTeam === g.aw;
                      const scoreDisplay =
                        g.sc && g.sc !== "PENDING" && g.sc !== "UPCOMING"
                          ? g.sc
                          : g.hp !== undefined && g.ap !== undefined
                            ? `${g.hp}-${g.ap}`
                            : "";

                      return {
                        g,
                        ch3,
                        cardIdx,
                        wtpObj,
                        trapWeeklyMismatch,
                        isVipMismatchRescue,
                        hw,
                        aw,
                        tot,
                        pct,
                        nat3Cnt,
                        minD3Val,
                        trapNoNat3,
                        trapEven6,
                        trapBlind100,
                        trapPas0000,
                        hasInternalTrap,
                        isBorderlineRescued,
                        calibratedWinPct,
                        maxBuyCents,
                        isUnderdogCaution,
                        isVip3,
                        isBestGuard,
                        isBestWtp,
                        isBaseF1,
                        isNaturalPool,
                        isFilteredOutByWeekly,
                        isFilteredOutByTrap,
                        isFilteredOutByIdx,
                        isIdxRescueOnly,
                        isQualified,
                        manualOverridden,
                        isNhlSysMode,
                        homeFav,
                        predTeam,
                        predRole,
                        kalshiTicker,
                        mktInfo,
                        liveAsk,
                        evEdge,
                        isPosEv,
                        hasFinalScore,
                        cardWon,
                        scoreDisplay,
                      };
                    })
                    .filter((item) => {
                      if (dailyCardFilter === "qualified") return item.isQualified;
                      if (dailyCardFilter === "vip3") return item.isVip3;
                      if (dailyCardFilter === "posev") return item.isPosEv;
                      if (dailyCardFilter === "win") return item.cardWon === true;
                      if (dailyCardFilter === "loss") return item.cardWon === false;
                      if (dailyCardFilter === "pending") return item.cardWon === null;
                      return true;
                    })
                    .sort((a, b) => {
                      if (Number(b.isVip3) !== Number(a.isVip3)) return Number(b.isVip3) - Number(a.isVip3);
                      if (Number(b.isQualified) !== Number(a.isQualified)) return Number(b.isQualified) - Number(a.isQualified);
                      if (Number(b.isPosEv) !== Number(a.isPosEv)) return Number(b.isPosEv) - Number(a.isPosEv);
                      const aUnan = a.ch3.unanimous && Math.abs(a.ch3.avgDelta) >= 2 ? 1 : 0;
                      const bUnan = b.ch3.unanimous && Math.abs(b.ch3.avgDelta) >= 2 ? 1 : 0;
                      if (bUnan !== aUnan) return bUnan - aUnan;
                      if (b.pct !== a.pct) return b.pct - a.pct;
                      if (Math.abs(b.cardIdx.delta) !== Math.abs(a.cardIdx.delta)) {
                        return Math.abs(b.cardIdx.delta) - Math.abs(a.cardIdx.delta);
                      }
                      return a.g.n - b.g.n;
                    })
                    .map((item) => {
                      const {
                        g,
                        ch3,
                        cardIdx,
                        wtpObj,
                        trapWeeklyMismatch,
                        isVipMismatchRescue,
                        hw,
                        aw,
                        tot,
                        pct,
                        nat3Cnt,
                        minD3Val,
                        trapNoNat3,
                        trapEven6,
                        trapBlind100,
                        hasInternalTrap,
                        isBorderlineRescued,
                        maxBuyCents,
                        isUnderdogCaution,
                        isVip3,
                        isBaseF1,
                        isNaturalPool,
                        isFilteredOutByWeekly,
                        isFilteredOutByTrap,
                        isFilteredOutByIdx,
                        isIdxRescueOnly,
                        isQualified,
                        manualOverridden,
                        isNhlSysMode,
                        homeFav,
                        predTeam,
                        predRole,
                        kalshiTicker,
                        liveAsk,
                        evEdge,
                        isPosEv,
                        hasFinalScore,
                        cardWon,
                        scoreDisplay,
                      } = item;

                      const modeBadgeText = manualOverridden
                        ? "فیلتر دستی فعال"
                        : dailyCardMode === "nhl_vip3"
                          ? "ویژه FIRE / VIP"
                          : dailyCardMode === "nhl_best"
                            ? "نهایی + ضریب Log5"
                            : dailyCardMode === "nhl_f1_guard"
                              ? "بدون جدول ۷۷٫۴٪"
                              : dailyCardMode === "nhl_f1_idx_raw"
                                ? "شاخص پایه ۶۲٫۵٪"
                                : dailyCardMode === "nhl_f1_union"
                                  ? "تلفیق ۱ + نجات"
                                  : dailyCardMode === "nhl_f1"
                                    ? "تلفیق ۱ پایه"
                                    : dailyCardMode === "step"
                                      ? "کانال STEP"
                                      : dailyCardMode === "geo"
                                        ? "کانال GEO-FIN"
                                        : dailyCardMode === "geo_tab"
                                          ? "کانال GEO-TAB"
                                          : "کانال GEO-DYN";

                      const defaultComboList =
                        comboSelectedByDate[activeDailyDate] && comboSelectedByDate[activeDailyDate].length >= 2
                          ? comboSelectedByDate[activeDailyDate]
                          : (() => {
                              const qualNos = [...gamesOnDailyDate]
                                .filter((x) =>
                                  dailyCardMode === "nhl_vip3"
                                    ? activeVip3Of(x)
                                    : dailyCardMode === "nhl_f1_guard"
                                      ? Boolean(x.f1_guard ?? x.f1_idx)
                                      : dailyCardMode === "nhl_f1_idx_raw"
                                        ? Boolean(x.f1_idx)
                                        : dailyCardMode === "nhl_f1_union"
                                          ? activeUnionOf(x)
                                          : dailyCardMode === "nhl_f1"
                                            ? Boolean(x.f1)
                                            : activeF1WtpOf(x)
                                )
                                .map((x) => x.n);
                              if (qualNos.length >= 3) return qualNos.slice(0, 3);
                              if (qualNos.length === 2) return qualNos.slice(0, 2);
                              return gamesOnDailyDate.slice(0, 2).map((x) => x.n);
                            })();

                      const inComboIdx = defaultComboList.indexOf(g.n);
                      const isCardInCombo = inComboIdx >= 0;

                      const toggleThisCardCombo = () => {
                        const cur = [...defaultComboList];
                        const idx = cur.indexOf(g.n);
                        if (idx >= 0) {
                          if (cur.length <= 2) return;
                          cur.splice(idx, 1);
                        } else {
                          if (cur.length >= 4) cur.pop();
                          cur.push(g.n);
                        }
                        setComboSelectedByDate((prev) => ({
                          ...prev,
                          [activeDailyDate]: cur,
                        }));
                      };

                      const cardEnabled = kalshiCardEnabled[g.n] ?? isPosEv;
                      const cardStake =
                        kalshiCardStake[g.n] ?? (isVip3 || isPosEv ? kalshiVipStake : kalshiDefaultStake);
                      const cardLimit = kalshiCardLimit[g.n] ?? liveAsk;
                      const cardContracts = Math.max(
                        1,
                        Math.floor((cardStake * 100) / Math.max(1, cardLimit))
                      );
                      const estCost = ((cardContracts * cardLimit) / 100).toFixed(2);
                      const estNetWin = ((cardContracts * (100 - cardLimit)) / 100).toFixed(2);

                      const showKalshiPanel =
                        isQualified || cardEnabled || Boolean(openManualKalshiCards[g.n]);

                      const cardBorderCls =
                        isVip3 && isQualified && !isVipMismatchRescue
                          ? "border-2 border-amber-400 ring-2 ring-amber-200/80 bg-white shadow-md"
                          : isQualified
                            ? "border-2 border-emerald-400 ring-1 ring-emerald-200 bg-white shadow-sm"
                            : (isFilteredOutByWeekly || isFilteredOutByTrap || isFilteredOutByIdx) && !manualOverridden
                              ? "border border-amber-300 bg-slate-50/95"
                              : "border border-slate-200 bg-slate-50/85";

                      const ribbonCls =
                        isVip3 && isQualified && !isVipMismatchRescue
                          ? "bg-gradient-to-r from-amber-600 via-emerald-700 to-teal-700 text-white"
                          : isQualified
                            ? "bg-emerald-700 text-white"
                            : isIdxRescueOnly && !manualOverridden
                              ? "bg-sky-100 text-sky-900 border-b border-sky-200"
                              : (isFilteredOutByWeekly || isFilteredOutByTrap || isFilteredOutByIdx) && !manualOverridden
                                ? "bg-amber-100/80 text-amber-950 border-b border-amber-200"
                                : "bg-slate-100 text-slate-600 border-b border-slate-200";

                      const trapReasonShort = g.trap_tag || "تله درونی/B2B";

                      const ribbonTitle =
                        isVipMismatchRescue
                          ? "نجات VIP جدول (≤۵۲¢)"
                          : isQualified && wtpObj.matchElem === "FIRE"
                            ? `تایید ویژه عنصر آتش FIRE (${wtpObj.l5Pick}% • ≤۷۶¢)`
                            : isVip3 && isQualified
                              ? "VIP طلایی ۳ کاناله + جدول (≤۷۶¢)"
                              : isQualified && manualOverridden
                                ? "تایید فیلتر دستی (≤۷۳¢)"
                                : isQualified && wtpObj.matchElem === "WATER"
                                  ? `تایید عنصر آب WATER (${wtpObj.l5Pick}% • ≤۶۸¢)`
                                  : isBorderlineRescued
                                    ? "عبور مرزی + جدول (≤۶۹¢)"
                                    : isQualified && isIdxRescueOnly
                                      ? "تایید نجات ۳ کاناله (اجماع ۳/۳)"
                                      : isQualified
                                        ? `تایید عنصر هوا AIR (${wtpObj.l5Pick}% • ≤۷۲¢)`
                                        : isFilteredOutByWeekly && !manualOverridden
                                          ? `اخراج عنصر خاک EARTH (Log5 ${wtpObj.l5Pick}%)`
                                      : isFilteredOutByTrap && !manualOverridden
                                        ? `فیلتر تله درونی: ${trapReasonShort}`
                                        : isIdxRescueOnly && !manualOverridden
                                          ? "کاندید نجات شاخص ۳ کاناله"
                                          : isFilteredOutByIdx && !manualOverridden
                                            ? "حذف توسط شاخص عددی جدید"
                                            : "خارج از سیگنال سیستم جدید";

                      const twinRuleOk =
                        isNhlSysMode && !manualOverridden
                          ? isQualified && (isBaseF1 || isIdxRescueOnly)
                          : isNaturalPool && tot >= 5 && tot <= 7 && pct >= 71 && Math.abs(hw - aw) >= 3 && !g.a1_veto;
                      const idxFavOk = isQualified
                        ? true
                        : (homeFav ? cardIdx.delta > 0 : cardIdx.delta < 0) && (!hasInternalTrap || minD3Val >= 2);

                      return (
                        <div
                          key={g.n}
                          data-testid={`nba-daily-card-${g.n}`}
                          className={`rounded-xl overflow-hidden flex flex-col justify-between transition-all ${cardBorderCls}`}
                        >
                          {/* 1. Clean Top Decision Ribbon */}
                          <div className={`px-2.5 py-1.5 flex items-center justify-between gap-1.5 text-[10.5px] font-extrabold leading-snug ${ribbonCls}`}>
                            <span>{ribbonTitle}</span>
                            <span className="font-mono text-[9.5px] shrink-0 opacity-95">
                              <bdi dir="ltr">#{g.n} • {g.d}</bdi>
                            </span>
                          </div>

                          <div className="p-3 space-y-2.5 flex-1 flex flex-col justify-between">
                            {/* Date / Shamsi + Active Mode Subbar */}
                            <div className="flex items-center justify-between gap-1.5 text-[10px] text-slate-600">
                              <span className="font-mono">
                                <bdi dir="ltr">
                                  {g.day} {g.sh_d ? `• (${g.sh_d})` : ""}
                                </bdi>
                              </span>
                              <div className="flex items-center gap-1">
                                {cardFlipDir[g.n] && (
                                  <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 font-bold">
                                    جهت معکوس دستی
                                  </span>
                                )}
                                <span className="px-1.5 py-0.5 rounded bg-sky-100 text-sky-900 border border-sky-200 font-bold">
                                  {modeBadgeText}
                                </span>
                              </div>
                            </div>

                            {/* 2. Hero Winner & Matchup Box (Full Untruncated Team Names) */}
                            <div
                              className={`rounded-lg px-2.5 py-2 border ${
                                isQualified
                                  ? "bg-emerald-50/75 border-emerald-300"
                                  : "bg-white border-slate-200"
                              }`}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <div className="min-w-0">
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span
                                      className={`px-1.5 py-0.5 rounded text-[10px] font-extrabold text-white ${
                                        isQualified
                                          ? homeFav
                                            ? "bg-emerald-700"
                                            : "bg-sky-700"
                                          : "bg-slate-600"
                                      }`}
                                    >
                                      {predRole}
                                    </span>
                                    {hasFinalScore ? (
                                      <span
                                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-extrabold border ${
                                          cardWon
                                            ? "bg-emerald-100 text-emerald-900 border-emerald-400"
                                            : "bg-rose-100 text-rose-900 border-rose-400"
                                        }`}
                                      >
                                        <bdi dir="ltr">{scoreDisplay}</bdi> •{" "}
                                        {cardWon ? "برد ✓" : "باخت ✕"}
                                      </span>
                                    ) : (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 border border-slate-200 font-semibold">
                                        در انتظار بازی
                                      </span>
                                    )}
                                  </div>

                                  <div className="text-sm font-extrabold text-slate-950 leading-snug mt-1">
                                    {predTeam}
                                  </div>
                                </div>

                                <div className="text-left shrink-0 font-mono">
                                  <div
                                    className={`text-lg font-extrabold leading-none ${
                                      isQualified ? "text-emerald-800" : "text-slate-700"
                                    }`}
                                  >
                                    {pct}%
                                  </div>
                                  <div className="text-[10px] text-slate-600 font-bold mt-1">
                                    <bdi dir="ltr">
                                      {hw}H-{aw}A ({tot}r{!isNaturalPool ? "*" : ""})
                                    </bdi>
                                  </div>
                                </div>
                              </div>

                              <div className="mt-1.5 pt-1 border-t border-slate-200/80 text-[10.5px] font-semibold text-slate-700 text-center leading-tight">
                                <bdi dir="ltr">
                                  {g.h} (H) vs {g.a} (A)
                                </bdi>
                              </div>
                            </div>

                            {/* 3. Three Core New-System Decision Pillars (Trap Guard + Borderline Index + Calibrated Max Buy) */}
                            <div className="grid grid-cols-3 gap-1.5 text-center">
                              {/* Pillar 1: DEG1=53 5-7 Twin Rule & Internal Trap Guard */}
                              <div
                                className={`rounded-lg px-1.5 py-1.5 border ${
                                  twinRuleOk
                                    ? "bg-emerald-50/80 border-emerald-300"
                                    : isFilteredOutByTrap
                                      ? "bg-amber-50/80 border-amber-200"
                                      : "bg-white border-slate-200"
                                }`}
                              >
                                <div className="text-[9px] text-slate-500 font-bold">۱. همزاد و تله درونی</div>
                                <div className="font-mono font-extrabold text-xs text-slate-900 mt-0.5">
                                  <bdi dir="ltr">
                                    {hw}H - {aw}A ({nat3Cnt}/4)
                                  </bdi>
                                </div>
                                <div
                                  className={`text-[9px] font-extrabold mt-0.5 ${
                                    twinRuleOk
                                      ? "text-emerald-800"
                                      : isFilteredOutByTrap
                                        ? "text-amber-900"
                                        : "text-slate-500"
                                  }`}
                                >
                                  {twinRuleOk
                                    ? isBorderlineRescued
                                      ? "عبور مرزی ✓"
                                      : "تایید تمیز ✓"
                                    : isFilteredOutByTrap
                                      ? trapReasonShort
                                      : g.a1_veto
                                        ? "گارد ۸۸ غیرفعال"
                                        : !isNaturalPool
                                          ? "ردیف طبیعی نیست"
                                          : isIdxRescueOnly
                                            ? "کاندید نجات ۴ کاناله"
                                            : "خارج از شرط ۵-۷"}
                                </div>
                              </div>

                              {/* Pillar 2: Upgraded Pool Numerical Index + Borderline Threshold */}
                              <div
                                className={`rounded-lg px-1.5 py-1.5 border ${
                                  idxFavOk
                                    ? "bg-emerald-50/80 border-emerald-300"
                                    : cardIdx.delta === 0
                                      ? "bg-white border-slate-200"
                                      : "bg-amber-50/80 border-amber-200"
                                }`}
                              >
                                <div className="text-[9px] text-slate-500 font-bold">۲. شاخص عددی/مرزی</div>
                                <div
                                  className={`font-mono font-extrabold text-xs mt-0.5 ${
                                    cardIdx.delta > 0
                                      ? "text-emerald-800"
                                      : cardIdx.delta < 0
                                        ? "text-sky-800"
                                        : "text-slate-600"
                                  }`}
                                >
                                  <bdi dir="ltr">
                                    Δ {cardIdx.delta > 0 ? `+${cardIdx.delta}` : cardIdx.delta} • min{" "}
                                    {minD3Val > 0 ? `+${minD3Val}` : minD3Val}
                                  </bdi>
                                </div>
                                <div className="text-[9px] font-bold text-slate-600 mt-0.5">
                                  {hasInternalTrap ? "مرز نجات: Δmin≥+2" : "مرز عادی: Δ≥+1"}
                                </div>
                              </div>

                              {/* Pillar 3: Calibrated Kalshi Max-Buy Value & Underdog Caution */}
                              <div
                                className={`rounded-lg px-1.5 py-1.5 border ${
                                  isPosEv
                                    ? "bg-emerald-50/80 border-emerald-300"
                                    : isQualified && isUnderdogCaution
                                      ? "bg-amber-50/80 border-amber-300"
                                      : "bg-white border-slate-200"
                                }`}
                              >
                                <div className="text-[9px] text-slate-500 font-bold">۳. ارزش بت Kalshi</div>
                                <div className="font-mono font-extrabold text-xs text-slate-900 mt-0.5">
                                  <bdi dir="ltr">
                                    {liveAsk}¢ {maxBuyCents > 0 ? `(≤${maxBuyCents}¢)` : ""}
                                  </bdi>
                                </div>
                                <div
                                  className={`text-[9px] font-extrabold mt-0.5 ${
                                    isPosEv
                                      ? "text-emerald-800"
                                      : isQualified && isUnderdogCaution
                                        ? "text-amber-900"
                                        : "text-slate-500"
                                  }`}
                                >
                                  {isPosEv
                                    ? `ارزش خرید ✓ (+${evEdge}¢)`
                                    : isQualified && isUnderdogCaution
                                      ? "احتیاط زیر ۴۵¢"
                                      : isQualified
                                        ? `گران (> ${maxBuyCents}¢)`
                                        : "خارج از سیگنال"}
                                </div>
                              </div>
                            </div>

                            {/* 3B. Weekly Team Power & Standings Strip (Auto-Updated Every Monday) */}
                            <div
                              className={`rounded-lg border px-2 py-1.5 space-y-1 text-[10px] ${
                                !trapWeeklyMismatch
                                  ? "bg-emerald-50/55 border-emerald-200 text-slate-800"
                                  : isVipMismatchRescue
                                    ? "bg-amber-50/80 border-amber-300 text-amber-950"
                                    : "bg-amber-50/60 border-amber-200 text-slate-700"
                              }`}
                            >
                              <div className="flex items-center justify-between gap-1">
                                <span className="font-bold text-[9.5px] text-slate-700">
                                  {oddsFreqMode === "daily" ? "المنت ضریب روزانه (تا " : "المنت ضریب هفتگی ("}
                                  <bdi dir="ltr">{wtpObj.mon}</bdi>):
                                </span>
                                <span
                                  title={`هفتگی (${g.wtp?.mon ?? "-"}): ${g.wtp?.mel ?? "-"} (${g.wtp?.hodds ?? "-"}x/${g.wtp?.aodds ?? "-"}x) | روزانه (تا ${g.wtp_day?.mon ?? "-"}): ${g.wtp_day?.mel ?? "-"} (${g.wtp_day?.hodds ?? "-"}x/${g.wtp_day?.aodds ?? "-"}x)`}
                                  className={`px-1.5 py-0.5 rounded font-mono font-extrabold text-[9.5px] border ${
                                    wtpObj.matchElem === "FIRE"
                                      ? "bg-amber-100 text-amber-950 border-amber-300"
                                      : wtpObj.matchElem === "AIR"
                                        ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                                        : wtpObj.matchElem === "WATER"
                                          ? "bg-sky-100 text-sky-900 border-sky-300"
                                          : "bg-rose-100 text-rose-900 border-rose-300"
                                  }`}
                                >
                                  {wtpObj.matchElemFa} • <bdi dir="ltr">{wtpObj.l5Pick}%</bdi>{" "}
                                  {!trapWeeklyMismatch ? "✓" : "(اخراج)"}
                                </span>
                              </div>
                              <div className="grid grid-cols-2 gap-1 font-mono text-[8.5px] tracking-tight text-center" dir="ltr">
                                <div className="rounded bg-white/90 border border-slate-200/90 px-1 py-0.5 font-bold text-slate-800 whitespace-nowrap" title={`Home #${wtpObj.hrk} (${wtpObj.hwl}) • Fair Odds ${wtpObj.hodds}x • TP ${wtpObj.htp}`}>
                                  H#{wtpObj.hrk} ({wtpObj.hwl}) {wtpObj.hel} {wtpObj.hodds}x
                                </div>
                                <div className="rounded bg-white/90 border border-slate-200/90 px-1 py-0.5 font-bold text-slate-800 whitespace-nowrap" title={`Away #${wtpObj.ark} (${wtpObj.awl}) • Fair Odds ${wtpObj.aodds}x • TP ${wtpObj.atp}`}>
                                  A#{wtpObj.ark} ({wtpObj.awl}) {wtpObj.ael} {wtpObj.aodds}x
                                </div>
                              </div>
                            </div>

                            {/* 4. Compact 4-Channel Strengthened Δ+S Index Strip (STEP | GEO-FIN | GEO-DYN | GEO-TAB) */}
                            <div className="rounded-lg border border-sky-200 bg-sky-50/60 px-2 py-1.5 space-y-1">
                              <div className="flex items-center justify-between gap-1 text-[9.5px]">
                                <span className="font-bold text-sky-950" title={decodeGeoTabFa(g.h_geo_tab ?? "0101")}>
                                  ۴ کانال شاخص (Δ+S) • <bdi dir="ltr">TAB {g.h_geo_tab ?? "0101"}</bdi>:
                                </span>
                                <span
                                  className={`px-1.5 py-0.2 rounded font-mono font-extrabold border ${
                                    ch3.unanimous && ch3.favSide === "HOME"
                                      ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                                      : ch3.unanimous && ch3.favSide === "AWAY"
                                        ? "bg-sky-100 text-sky-900 border-sky-300"
                                        : "bg-white text-slate-700 border-slate-200"
                                  }`}
                                >
                                  <bdi dir="ltr">
                                    {ch3.homeVotes}-{ch3.awayVotes}
                                  </bdi>{" "}
                                  {ch3.favSide === "HOME"
                                    ? "میزبان"
                                    : ch3.favSide === "AWAY"
                                      ? "میهمان"
                                      : "مساوی"}{" "}
                                  •{" "}
                                  <bdi dir="ltr">
                                    ΔS {ch3.totalScoreDelta > 0 ? `+${ch3.totalScoreDelta}` : ch3.totalScoreDelta}
                                  </bdi>
                                </span>
                              </div>

                              <div className="grid grid-cols-2 gap-1 text-[8.5px] tracking-tight font-mono text-center" dir="ltr">
                                {[
                                  { lbl: "1.STEP", r: ch3.step, idx: ch3.idxSt },
                                  { lbl: "2.FIN", r: ch3.geoFin, idx: ch3.idxGf },
                                  { lbl: "3.DYN", r: ch3.geoDyn, idx: ch3.idxGd },
                                  { lbl: "4.TAB", r: ch3.geoTab, idx: ch3.idxGt },
                                ].map((c) => {
                                  const d = c.idx.effDelta;
                                  const sd = c.idx.scoreDelta;
                                  return (
                                    <div
                                      key={c.lbl}
                                      title={`${c.lbl}: ${c.r.hw}H-${c.r.aw}A | Δ=${c.idx.delta} | S=${c.idx.scoreH}:${c.idx.scoreA} (ΔS=${sd})`}
                                      className={`rounded px-1 py-0.5 border whitespace-nowrap ${
                                        d > 0
                                          ? "bg-emerald-50/90 border-emerald-200 text-emerald-900"
                                          : d < 0
                                            ? "bg-sky-50/90 border-sky-200 text-sky-900"
                                            : "bg-white border-slate-200 text-slate-600"
                                      }`}
                                    >
                                      <span className="font-bold text-slate-500 mr-1">{c.lbl}</span>
                                      <span className="font-extrabold">
                                        {c.r.hw}H-{c.r.aw}A Δ{d > 0 ? `+${d}` : d} S{sd > 0 ? `+${sd}` : sd}
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>

                            {/* 5. Kalshi Execution & Combo Controls (Expanded on Qualified; Compact 1-Line on Rejected) */}
                            {!showKalshiPanel ? (
                              <div className="flex items-center justify-between gap-1.5 pt-0.5">
                                <button
                                  type="button"
                                  onClick={() =>
                                    setOpenManualKalshiCards((prev) => ({
                                      ...prev,
                                      [g.n]: true,
                                    }))
                                  }
                                  className="flex-1 py-1 px-2 rounded border border-slate-300 bg-white hover:bg-sky-50 text-slate-700 font-bold text-[10px] transition-colors"
                                >
                                  باز کردن پنل شرط دستی Kalshi ▼
                                </button>
                                <button
                                  type="button"
                                  onClick={toggleThisCardCombo}
                                  className={`py-1 px-2.5 rounded border font-extrabold text-[10px] transition-colors ${
                                    isCardInCombo
                                      ? "bg-indigo-700 text-white border-indigo-800"
                                      : "bg-indigo-50 hover:bg-indigo-100 text-indigo-900 border-indigo-300"
                                  }`}
                                >
                                  {isCardInCombo ? `در کمبو (Leg ${inComboIdx + 1}) ✓` : "+ کمبو"}
                                </button>
                              </div>
                            ) : (
                              <div
                                className={`rounded-lg p-2 border space-y-1.5 ${
                                  cardEnabled
                                    ? "bg-emerald-50/90 border-emerald-400"
                                    : "bg-white border-sky-200"
                                }`}
                              >
                                <div className="flex items-center justify-between gap-1.5">
                                  <label className="inline-flex items-center gap-1.5 cursor-pointer text-[11px] font-extrabold text-slate-900">
                                    <input
                                      type="checkbox"
                                      checked={cardEnabled}
                                      onChange={(e) =>
                                        setKalshiCardEnabled((prev) => ({
                                          ...prev,
                                          [g.n]: e.target.checked,
                                        }))
                                      }
                                      className="h-3.5 w-3.5 accent-emerald-600"
                                    />
                                    <span>ثبت در سبد روزانه Kalshi</span>
                                  </label>

                                  <div className="flex items-center gap-1">
                                    <span className="text-[9px] font-mono text-slate-600" dir="ltr">
                                      {kalshiTicker}
                                    </span>
                                    {!isQualified && !cardEnabled && (
                                      <button
                                        type="button"
                                        onClick={() =>
                                          setOpenManualKalshiCards((prev) => ({
                                            ...prev,
                                            [g.n]: false,
                                          }))
                                        }
                                        className="text-[10px] text-slate-500 hover:text-slate-800 px-1"
                                        title="بستن پنل"
                                      >
                                        ▲
                                      </button>
                                    )}
                                  </div>
                                </div>

                                <div className="grid grid-cols-3 gap-1.5 items-center text-[10px]" dir="ltr">
                                  <div className="bg-slate-50 rounded border border-slate-200 px-1.5 py-0.5">
                                    <span className="text-[8.5px] text-slate-500 block">Stake ($)</span>
                                    <input
                                      type="number"
                                      min={1}
                                      max={250}
                                      step={0.5}
                                      value={cardStake}
                                      onChange={(e) =>
                                        setKalshiCardStake((prev) => ({
                                          ...prev,
                                          [g.n]: Math.max(0.5, Number(e.target.value) || 2),
                                        }))
                                      }
                                      className="w-full font-mono font-extrabold text-xs text-slate-900 bg-transparent outline-none"
                                    />
                                  </div>

                                  <div className="bg-slate-50 rounded border border-slate-200 px-1.5 py-0.5">
                                    <span className="text-[8.5px] text-slate-500 block">Limit (¢)</span>
                                    <input
                                      type="number"
                                      min={1}
                                      max={99}
                                      value={cardLimit}
                                      onChange={(e) =>
                                        setKalshiCardLimit((prev) => ({
                                          ...prev,
                                          [g.n]: Math.min(99, Math.max(1, Number(e.target.value) || liveAsk)),
                                        }))
                                      }
                                      className="w-full font-mono font-extrabold text-xs text-slate-900 bg-transparent outline-none"
                                    />
                                  </div>

                                  <div className="bg-emerald-50/70 rounded border border-emerald-200 px-1.5 py-0.5 text-center">
                                    <span className="text-[8.5px] text-slate-600 block">{cardContracts} cnt</span>
                                    <span className="font-mono font-extrabold text-[10px] text-emerald-800">
                                      +${estNetWin}
                                    </span>
                                  </div>
                                </div>

                                <div className="grid grid-cols-2 gap-1.5">
                                  <button
                                    type="button"
                                    disabled={kalshiBusy}
                                    onClick={async () => {
                                      setKalshiBusy(true);
                                      try {
                                        const singleOrder = {
                                          gameNo: g.n,
                                          date: g.d,
                                          homeTeam: g.h,
                                          awayTeam: g.a,
                                          winnerTeam: predTeam,
                                          ticker: kalshiTicker,
                                          enabled: true,
                                          stakeUsd: cardStake,
                                          limitCents: cardLimit,
                                          contracts: cardContracts,
                                        };
                                        const r = await fetch("/api/kalshi/execute", {
                                          method: "POST",
                                          headers: { "Content-Type": "application/json" },
                                          body: JSON.stringify({
                                            date: g.d,
                                            orders: [singleOrder],
                                            mode: kalshiHasKey ? "live" : "dry_run",
                                          }),
                                        });
                                        const d = await r.json();
                                        setKalshiExecReport(d);
                                      } finally {
                                        setKalshiBusy(false);
                                      }
                                    }}
                                    className="py-1 px-2 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-[10px] shadow-sm transition-colors"
                                  >
                                    {kalshiHasKey
                                      ? `خرید تکی YES ($${estCost})`
                                      : `تست خرید تکی ($${estCost})`}
                                  </button>

                                  <button
                                    type="button"
                                    onClick={toggleThisCardCombo}
                                    className={`py-1 px-2 rounded font-extrabold text-[10px] border transition-colors ${
                                      isCardInCombo
                                        ? "bg-indigo-700 hover:bg-indigo-800 text-white border-indigo-900"
                                        : "bg-indigo-50 hover:bg-indigo-100 text-indigo-900 border-indigo-300"
                                    }`}
                                  >
                                    {isCardInCombo
                                      ? `در کمبو (Leg ${inComboIdx + 1}) ✓`
                                      : "افزودن به کمبو +"}
                                  </button>
                                </div>
                              </div>
                            )}

                            {/* 6. Clean 2-Button Footer */}
                            <div className="grid grid-cols-2 gap-1.5 pt-0.5">
                              <button
                                type="button"
                                onClick={() => {
                                  setDateFilter(g.d);
                                  setOpenManualSection(true);
                                  setManualOpenGames((prev) => ({ ...prev, [g.n]: true }));
                                  setTimeout(() => {
                                    document
                                      .getElementById(`manual-nba-game-row-${g.n}`)
                                      ?.scrollIntoView({ behavior: "smooth", block: "center" });
                                  }, 80);
                                }}
                                className="py-1 px-2 rounded bg-sky-100 hover:bg-sky-200 text-sky-950 border border-sky-300 font-bold text-[10px] transition-colors"
                              >
                                جدول فیلتر دستی ↓
                              </button>

                              <button
                                type="button"
                                onClick={() =>
                                  setCardFlipDir((prev) => ({ ...prev, [g.n]: !prev[g.n] }))
                                }
                                className={`py-1 px-2 rounded font-bold text-[10px] border transition-colors ${
                                  cardFlipDir[g.n]
                                    ? "bg-amber-500 text-slate-950 border-amber-600"
                                    : "bg-white hover:bg-slate-100 text-slate-700 border-slate-300"
                                }`}
                              >
                                {cardFlipDir[g.n] ? "بازگشت به جهت سیستم" : "تغییر جهت دستی"}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Collapsible Dropdown 1: Pattern Selector Cards & Season/Monthly Accuracy */}
        <div className="rounded-lg border border-sky-200 bg-sky-50/50 overflow-hidden">
          <div
            onClick={() => setOpenStatsSection((v) => !v)}
            className="px-4 py-2.5 bg-sky-100/80 hover:bg-sky-100 cursor-pointer flex flex-wrap items-center justify-between gap-2 border-b border-sky-200/80 transition-colors"
          >
            <div className="flex flex-wrap items-center gap-2 text-xs font-bold text-sky-950">
              <span>📊 پترن‌های آماری و جدول دقت فصل‌به‌فصل و ماه‌به‌ماه ({activeDef.titleFa})</span>
              <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 font-mono text-[11px]">
                Win Rate: {patternAcc}% ({patternWins}/{patternCompleted.length})
              </span>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenStatsSection((v) => !v);
              }}
              className="px-3 py-1 rounded border border-sky-300 bg-white hover:bg-sky-50 text-sky-950 text-xs font-bold shadow-sm"
            >
              {openStatsSection ? "بستن جدول آمار ▲" : "باز کردن پترن‌ها و جدول آمار ▼"}
            </button>
          </div>
          {openStatsSection && (
            <div className="p-4 flex flex-col gap-4 bg-white/80">
        {/* Pattern Selector Cards */}
        {engineMode === "manual" || engineMode === "twins" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-2">
            {TWIN_PATTERN_DEFS.map((p) => {
              const sub = games.filter((g) => matchTwin(g, p.key) && Boolean(g.done));
              const w = sub.filter((g) => (p.key === "tall" ? g.fst === "WIN" : (g.sys_win ?? g.fpw ?? g.h) === g.aw)).length;
              const pct = sub.length > 0 ? ((100 * w) / sub.length).toFixed(2) : "0.00";
              const pend = games.filter((g) => matchTwin(g, p.key) && !g.done).length;
              const active = twinPattern === p.key;
              return (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => {
                    setTwinPattern(p.key);
                    setPage(1);
                  }}
                  className={`text-right p-2.5 rounded-lg border transition-all flex flex-col justify-between gap-2 ${
                    active
                      ? "bg-emerald-600 text-white border-emerald-700 shadow-md"
                      : "bg-white hover:bg-emerald-50 text-slate-800 border-emerald-200"
                  }`}
                >
                  <div>
                    <div className={`text-[10px] font-mono uppercase ${active ? "text-emerald-100" : "text-slate-500"}`}>
                      {p.titleEn}
                    </div>
                    <div className="font-bold text-xs mt-0.5 leading-snug">{p.titleFa}</div>
                  </div>
                  <div className="flex items-baseline justify-between pt-1 border-t border-current/15">
                    <span className="text-base font-extrabold font-mono">{pct}%</span>
                    <span className={`text-[10px] font-mono ${active ? "text-emerald-100" : "text-slate-500"}`}>
                      {w}/{sub.length} (+{pend})
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        ) : engineMode === "fusion" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-2">
            {FUSION_PATTERN_DEFS.map((p: any) => {
              const sub = games.filter((g) => matchFusion(g, p.key) && Boolean(g.done));
              const w = sub.filter((g) => (((g.f30 ?? 0) >= 0 ? g.h : g.a) === g.aw)).length;
              const pct = sub.length > 0 ? ((100 * w) / sub.length).toFixed(2) : "0.00";
              const pend = games.filter((g) => matchFusion(g, p.key) && !g.done).length;
              const active = fusionPattern === p.key;
              return (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => {
                    setFusionPattern(p.key);
                    setPage(1);
                  }}
                  className={`text-right p-2.5 rounded-lg border transition-all flex flex-col justify-between gap-2 ${
                    active
                      ? "bg-sky-600 text-white border-sky-700 shadow-md"
                      : "bg-white hover:bg-sky-50 text-slate-800 border-sky-200"
                  }`}
                >
                  <div>
                    <div className={`text-[10px] font-mono uppercase ${active ? "text-sky-100" : "text-slate-500"}`}>
                      {p.titleEn}
                    </div>
                    <div className="font-bold text-xs mt-0.5 leading-snug">{p.titleFa}</div>
                  </div>
                  <div className="flex items-baseline justify-between pt-1 border-t border-current/15">
                    <span className="text-base font-extrabold font-mono">{pct}%</span>
                    <span className={`text-[10px] font-mono ${active ? "text-sky-100" : "text-slate-500"}`}>
                      {w}/{sub.length} (+{pend})
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
            {SINGLE_PATTERN_DEFS.map((p: any) => {
              const sub = games.filter((g) => matchSingle(g, p.key) && Boolean(g.done));
              const w = sub.filter((g) => (p.key === "s1_guard" ? g.a === g.aw : p.key === "all" ? g.st === "WIN" : g.h === g.aw)).length;
              const pct = sub.length > 0 ? ((100 * w) / sub.length).toFixed(2) : "0.00";
              const pend = games.filter((g) => matchSingle(g, p.key) && !g.done).length;
              const active = singlePattern === p.key;
              return (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => {
                    setSinglePattern(p.key);
                    setPage(1);
                  }}
                  className={`text-right p-3 rounded-lg border transition-all flex flex-col justify-between gap-2 ${
                    active
                      ? "bg-sky-600 text-white border-sky-700 shadow-md"
                      : "bg-white hover:bg-sky-50 text-slate-800 border-sky-200"
                  }`}
                >
                  <div>
                    <div className={`text-[11px] font-mono uppercase ${active ? "text-sky-100" : "text-slate-500"}`}>
                      {p.titleEn}
                    </div>
                    <div className="font-bold text-xs mt-0.5 leading-snug">{p.titleFa}</div>
                  </div>
                  <div className="flex items-baseline justify-between pt-1 border-t border-current/15">
                    <span className="text-lg font-extrabold font-mono">{pct}%</span>
                    <span className={`text-[11px] font-mono ${active ? "text-sky-100" : "text-slate-500"}`}>
                      {w}/{sub.length} (+{pend} آینده)
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Active Pattern Formula Explanation */}
        <div className="bg-white border border-sky-200 rounded-md p-3.5 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-slate-700 leading-relaxed">
            <span className="font-bold text-sky-900">فرمول پترن انتخاب‌شده ({activeDef.titleFa}): </span>
            {activeDef.formulaFa}
          </div>
          <div className="text-sm font-mono font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded">
            Win Rate: {patternAcc}% ({patternWins} Wins / {patternCompleted.length - patternWins} Losses)
          </div>
        </div>

        {/* Season-by-Season & Monthly Summary Tables */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white border border-sky-200 rounded-md overflow-hidden">
            <div className="bg-sky-100/70 px-3.5 py-2 text-xs font-bold text-sky-950 flex items-center justify-between">
              <span>عملکرد به تفکیک هر فصل (Season-by-Season Accuracy)</span>
              <span className="font-mono text-[11px] text-sky-800">{activeDef.titleEn}</span>
            </div>
            <table className="w-full text-xs font-mono text-left border-collapse">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="p-2">Season (فصل)</th>
                  <th className="p-2">Completed</th>
                  <th className="p-2 text-emerald-700">Wins (برد)</th>
                  <th className="p-2 text-rose-600">Losses (خطا)</th>
                  <th className="p-2 text-amber-700">Upcoming</th>
                  <th className="p-2 font-bold">Win Rate %</th>
                </tr>
              </thead>
              <tbody>
                {seasonStats.map((st) => (
                  <tr key={st.season} className="border-b border-slate-100 hover:bg-sky-50/40">
                    <td className="p-2 font-bold text-slate-800">{st.season}</td>
                    <td className="p-2">{st.total}</td>
                    <td className="p-2 text-emerald-700 font-semibold">{st.wins}</td>
                    <td className="p-2 text-rose-600">{st.losses}</td>
                    <td className="p-2 text-amber-700">{st.pending}</td>
                    <td className="p-2 font-extrabold text-sky-900">{st.pct}%</td>
                  </tr>
                ))}
                <tr className="bg-sky-50/70 font-bold text-slate-900">
                  <td className="p-2">مجموع کل (All 3 Seasons)</td>
                  <td className="p-2">{patternCompleted.length}</td>
                  <td className="p-2 text-emerald-700">{patternWins}</td>
                  <td className="p-2 text-rose-600">{patternCompleted.length - patternWins}</td>
                  <td className="p-2 text-amber-700">{patternGames.length - patternCompleted.length}</td>
                  <td className="p-2 text-sky-950 text-sm">{patternAcc}%</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="bg-white border border-sky-200 rounded-md overflow-hidden flex flex-col">
            <div className="bg-sky-100/70 px-3.5 py-2 text-xs font-bold text-sky-950 flex items-center justify-between gap-2 flex-wrap">
              <span>روند تجمعی ماه‌به‌ماه ({monthlyCalendarKind === "shamsi" ? "برج‌های خورشیدی شمسی" : "ماه‌های میلادی"})</span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setMonthlyCalendarKind("shamsi")}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                    monthlyCalendarKind === "shamsi" ? "bg-emerald-600 text-white border-emerald-700" : "bg-white text-slate-700 border-sky-300"
                  }`}
                >
                  خورشیدی شمسی
                </button>
                <button
                  type="button"
                  onClick={() => setMonthlyCalendarKind("greg")}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                    monthlyCalendarKind === "greg" ? "bg-sky-700 text-white border-sky-800" : "bg-white text-slate-700 border-sky-300"
                  }`}
                >
                  میلادی
                </button>
                <button
                  type="button"
                  onClick={() => setShowMonthlyTable((v) => !v)}
                  className="text-[11px] text-sky-800 underline ml-1"
                >
                  {showMonthlyTable ? "Hide" : "Show"}
                </button>
              </div>
            </div>
            {showMonthlyTable && (
              <div className="max-h-48 overflow-y-auto">
                <table className="w-full text-[11px] font-mono text-left border-collapse">
                  <thead className="bg-slate-50 text-slate-600 sticky top-0 border-b border-slate-200">
                    <tr>
                      <th className="p-1.5 pl-3">Month</th>
                      <th className="p-1.5">Month W/N</th>
                      <th className="p-1.5">Month %</th>
                      <th className="p-1.5">Cumulative W/N</th>
                      <th className="p-1.5 font-bold">Cumulative %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyRows.map((m) => (
                      <tr key={m.ym} className="border-b border-slate-100 hover:bg-sky-50/40">
                        <td className="p-1.5 pl-3 font-semibold">{m.ym}</td>
                        <td className="p-1.5">{m.mw}/{m.mn}</td>
                        <td className="p-1.5 text-slate-600">{m.mPct}%</td>
                        <td className="p-1.5 font-medium">{m.cumW}/{m.cumN}</td>
                        <td className="p-1.5 font-bold text-emerald-700">{m.cumPct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

            </div>
          )}
        </div>

        {/* Daily Slate Quick Selector */}
        <div className="bg-white p-3 rounded-md border border-sky-200 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-bold text-sky-950 ml-1">دسته‌بندی بازی‌های روزانه (Daily Slate):</span>
            {DAILY_QUICK_DATES.map((qd) => (
              <button
                key={qd.date}
                type="button"
                onClick={() => {
                  setDateFilter(qd.date);
                  if (qd.date !== "ALL") setDailyCardDate(qd.date);
                  if (qd.date !== "ALL") {
                    if (engineMode === "twins" || engineMode === "manual") setTwinPattern("tall");
                    else if (engineMode === "fusion") setFusionPattern("fall");
                    else setSinglePattern("all");
                  }
                  setPage(1);
                }}
                className={`text-xs px-2.5 py-1 rounded border font-mono transition-colors ${
                  dateFilter === qd.date
                    ? "bg-sky-600 text-white border-sky-700 font-bold"
                    : "bg-slate-50 hover:bg-sky-50 text-slate-700 border-slate-200"
                }`}
              >
                {qd.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5">
            <label className="text-[11px] font-medium text-slate-600">تاریخ دلخواه:</label>
            <input
              type="date"
              value={dateFilter === "ALL" ? "" : dateFilter}
              onChange={(e) => {
                const v = e.target.value || "ALL";
                setDateFilter(v);
                if (v !== "ALL") setDailyCardDate(v);
                if (v !== "ALL") {
                  if (engineMode === "twins" || engineMode === "manual") setTwinPattern("tall");
                  else if (engineMode === "fusion") setFusionPattern("fall");
                  else setSinglePattern("all");
                }
                setPage(1);
              }}
              className="h-8 rounded border border-slate-300 px-2 text-xs font-mono"
            />
          </div>
        </div>

        {/* Interactive Filter Controls */}
        <div className="space-y-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5 bg-white p-3 rounded-md border border-sky-200 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-medium text-slate-600">فصل (Season)</label>
              <select
                value={seasonFilter}
                data-testid="select-nba-season-filter"
                onChange={(e) => {
                  const nextS = e.target.value;
                  setSeasonFilter(nextS);
                  setDateFilter("ALL");
                  if (nextS !== "ALL" && monthFilter !== "ALL" && !patternGames.some((g) => g.s === nextS && g.ym === monthFilter)) {
                    setMonthFilter("ALL");
                  }
                  setFilterAutoNote("");
                  setPage(1);
                }}
                className="h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs font-mono"
              >
                <option value="ALL">All Seasons (همه فصل‌ها)</option>
                <option value="2024">فصل ۲۰۲۴ (ATP / WTA 2024)</option>
                <option value="2025">فصل ۲۰۲۵ (ATP / WTA 2025)</option>
                <option value="2026">فصل ۲۰۲۶ (ATP / WTA 2026)</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-medium text-slate-600">ماه (Year-Month)</label>
              <select
                value={monthFilter}
                data-testid="select-nba-month-filter"
                onChange={(e) => {
                  const nextYm = e.target.value;
                  setMonthFilter(nextYm);
                  setDateFilter("ALL");
                  if (nextYm !== "ALL") {
                    const mGames = patternGames.filter((g) => (seasonFilter === "ALL" || g.s === seasonFilter) && g.ym === nextYm);
                    const doneCnt = mGames.filter((g) => Boolean(g.done)).length;
                    const pendCnt = mGames.length - doneCnt;
                    if (doneCnt === 0 && (statusFilter === "WIN" || statusFilter === "LOSS")) {
                      setStatusFilter("ALL");
                      setFilterAutoNote(`ماه ${nextYm} مربوط به آینده است و هنوز نتیجه‌ای ثبت نشده است (${pendCnt} بازی در انتظار PENDING).`);
                    } else if (pendCnt === 0 && statusFilter === "PENDING") {
                      setStatusFilter("ALL");
                      setFilterAutoNote(`تمام ${doneCnt} بازی ماه ${nextYm} برگزار شده است؛ وضعیت روی همه نتایج قرار گرفت.`);
                    } else {
                      setFilterAutoNote("");
                    }
                  } else {
                    setFilterAutoNote("");
                  }
                  setPage(1);
                }}
                className="h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs font-mono"
              >
                <option value="ALL">All Months (همه ماه‌ها)</option>
                {allMonths.map((ym) => {
                  const mSub = patternGames.filter((g) => (seasonFilter === "ALL" || g.s === seasonFilter) && g.ym === ym);
                  const mDone = mSub.filter((g) => Boolean(g.done)).length;
                  const mPend = mSub.length - mDone;
                  const suffix =
                    mDone > 0 && mPend > 0
                      ? ` (${mDone} انجام‌شده • ${mPend} آینده)`
                      : mDone > 0
                        ? ` (${mDone} انجام‌شده)`
                        : ` (آینده • ${mPend} بازی بدون نتیجه)`;
                  return (
                    <option key={ym} value={ym}>
                      {ym}{suffix}
                    </option>
                  );
                })}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-medium text-slate-600">وضعیت نتیجه (Result Status)</label>
              <select
                value={statusFilter}
                data-testid="select-nba-status-filter"
                onChange={(e) => {
                  const nextSt = e.target.value;
                  setStatusFilter(nextSt);
                  setOpenSummaryTable(true);
                  let clearedNote = "";
                  if (nextSt !== "ALL") {
                    if (dateFilter !== "ALL") {
                      const hasOnDay = patternGames.some((g) => g.d === dateFilter && getGameStatus(g) === nextSt);
                      if (!hasOnDay) {
                        setDateFilter("ALL");
                        clearedNote = `فیلتر تک‌روز (${dateFilter}) برداشته شد تا نتایج ${nextSt} نمایش داده شوند.`;
                      }
                    }
                    if ((nextSt === "WIN" || nextSt === "LOSS") && monthFilter !== "ALL") {
                      const hasDoneInMonth = patternGames.some((g) => g.ym === monthFilter && Boolean(g.done));
                      if (!hasDoneInMonth) {
                        const prevM = monthFilter;
                        setMonthFilter("ALL");
                        clearedNote = `ماه ${prevM} هنوز برگزار نشده است (آینده)؛ نمایش ${nextSt === "WIN" ? "پیش‌بینی‌های درست" : "خطاها"} در کل ماه‌های انجام‌شده فعال شد.`;
                      }
                    } else if (nextSt === "PENDING" && monthFilter !== "ALL") {
                      const hasPendInMonth = patternGames.some((g) => g.ym === monthFilter && !g.done);
                      if (!hasPendInMonth) {
                        const prevM = monthFilter;
                        setMonthFilter("ALL");
                        clearedNote = `ماه ${prevM} بازی آینده ندارد؛ نمایش بازی‌های آینده (PENDING) در کل ماه‌ها فعال شد.`;
                      }
                    }
                  }
                  setFilterAutoNote(clearedNote);
                  setPage(1);
                }}
                className="h-9 rounded-md border border-slate-300 bg-white px-2.5 text-xs font-mono"
              >
                <option value="ALL">All Games ({scopeBeforeStatus.length})</option>
                <option value="WIN">WIN — پیش‌بینی‌های درست ({scopeStatusCounts.WIN})</option>
                <option value="LOSS">LOSS — خطاها ({scopeStatusCounts.LOSS})</option>
                <option value="PENDING">PENDING — بازی‌های آینده ({scopeStatusCounts.PENDING})</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-medium text-slate-600">جستجوی نام تیم (Search Team)</label>
              <Input
                value={teamQuery}
                onChange={(e) => {
                  setTeamQuery(e.target.value);
                  setPage(1);
                }}
                placeholder="e.g. Boston, Cleveland, Lakers, Nuggets..."
                className="h-9 text-xs font-mono bg-white"
              />
            </div>

            <div className="flex items-center justify-between gap-2 h-9 px-2 bg-sky-50 rounded border border-sky-200 text-xs font-mono">
              <span className="truncate">
                Showing: <b>{filteredGames.length}</b> games
                {dateFilter !== "ALL" ? ` (${dateFilter})` : ""}
              </span>
              <button
                type="button"
                onClick={() => {
                  setSeasonFilter("ALL");
                  setMonthFilter("ALL");
                  setDateFilter("ALL");
                  setStatusFilter("ALL");
                  setTeamQuery("");
                  setFilterAutoNote("");
                  setPage(1);
                }}
                className="text-sky-700 hover:underline text-[11px] shrink-0"
              >
                Reset
              </button>
            </div>
          </div>

          {filterAutoNote && (
            <div dir="rtl" className="px-3 py-1.5 rounded border border-amber-300 bg-amber-50 text-amber-950 text-xs font-semibold flex items-center justify-between gap-2">
              <span>{filterAutoNote}</span>
              <button type="button" onClick={() => setFilterAutoNote("")} className="text-[11px] text-amber-900 underline">
                بستن
              </button>
            </div>
          )}
        </div>

        {/* Collapsible Dropdown 2: GOLD-FORMULA-PRIORITY Manual Filter (DAY) System — LIGHT BLUE THEME */}
        <div className="rounded-lg border-2 border-sky-300 bg-sky-50/70 text-slate-900 shadow-sm overflow-hidden" dir="rtl">
          {/* Collapsible Section Header */}
          <div
            onClick={() => setOpenManualSection((v) => !v)}
            className="bg-sky-200/80 hover:bg-sky-200 px-4 py-3 border-b border-sky-300 cursor-pointer flex flex-wrap items-center justify-between gap-3 transition-colors"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-1 rounded bg-sky-700 text-white font-extrabold text-xs shadow-sm">
                🎛️ فیلتر دستی (DAY) — همزادیاب دقیق ELE-P • ELE-FINAL • ELE-DYN
              </span>
              <span className="text-xs text-sky-950 font-mono font-semibold bg-white/90 px-2.5 py-0.5 rounded border border-sky-300">
                دیتابیس تاریخی: <b className="text-emerald-700">{histGames.length.toLocaleString()}</b> بازی (۲۰۱۰–۲۰۲۶)
              </span>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenManualSection((v) => !v);
              }}
              className="px-3 py-1 rounded border border-sky-400 bg-white hover:bg-sky-50 text-sky-950 text-xs font-extrabold shadow-sm"
            >
              {openManualSection ? "بستن فیلتر دستی ▲" : "باز کردن فیلتر دستی (DAY) ▼"}
            </button>
          </div>

          {openManualSection && (
            <div>
              {/* Top Toolbar Controls (Light Blue Theme) */}
              <div className="bg-sky-100/80 px-4 py-2.5 border-b border-sky-200 flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  {/* Home vs Away Elemental Perspective Toggle */}
                  <div className="inline-flex rounded-md border border-sky-300 bg-white p-0.5 text-[11px] shadow-sm">
                    <button
                      type="button"
                      onClick={() => setManualPersp("home")}
                      className={`px-2.5 py-1 rounded font-bold transition-colors ${
                        manualPersp === "home"
                          ? "bg-sky-600 text-white"
                          : "text-slate-700 hover:bg-sky-50"
                      }`}
                    >
                      🏠 المنت میزبان (HOME ELE-P/FINAL/DYN)
                    </button>
                    <button
                      type="button"
                      onClick={() => setManualPersp("away")}
                      className={`px-2.5 py-1 rounded font-bold transition-colors ${
                        manualPersp === "away"
                          ? "bg-indigo-600 text-white"
                          : "text-slate-700 hover:bg-indigo-50"
                      }`}
                    >
                      ✈️ المنت میهمان (AWAY ELE-P/FINAL/DYN)
                    </button>
                  </div>

                <div className="inline-flex rounded-md border border-sky-300 bg-white p-0.5" title="انتخاب نوع شکل رمل در فیلتر دستی NBA">
                  <button
                    type="button"
                    onClick={() => setManualGeoKind("fin")}
                    className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                      manualGeoKind === "fin" ? "bg-emerald-600 text-white" : "text-slate-700 hover:bg-emerald-50"
                    }`}
                  >
                    GEO-FIN (اصلاح‌شده)
                  </button>
                  <button
                    type="button"
                    onClick={() => setManualGeoKind("dyn")}
                    className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                      manualGeoKind === "dyn" ? "bg-sky-700 text-white" : "text-slate-700 hover:bg-sky-50"
                    }`}
                  >
                    GEO-DYN (پویا)
                  </button>
                </div>

                  {/* Weekday Filter */}
                  <select
                    value={manualDayFilter}
                    onChange={(e) => {
                      setManualDayFilter(e.target.value);
                      setPage(1);
                    }}
                    className="h-8 rounded-md border border-sky-300 bg-white px-2.5 text-xs text-sky-950 font-mono font-bold shadow-sm"
                  >
                    <option value="ALL">همه روزهای هفته (ALL DAYS)</option>
                    <option value="MONDAY">MONDAY (دوشنبه)</option>
                    <option value="TUESDAY">TUESDAY (سه‌شنبه)</option>
                    <option value="WEDNESDAY">WEDNESDAY (چهارشنبه)</option>
                    <option value="THURSDAY">THURSDAY (پنج‌شنبه)</option>
                    <option value="FRIDAY">FRIDAY (جمعه)</option>
                    <option value="SATURDAY">SATURDAY (شنبه)</option>
                    <option value="SUNDAY">SUNDAY (یکشنبه)</option>
                  </select>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {/* Batch Smart / Clear on current page */}
                  <button
                    type="button"
                    onClick={() => {
                      const nextMap = { ...manualFilters };
                      const openMap = { ...manualOpenGames };
                      pageGames.forEach((g, idx) => {
                        const t12 = (manualPersp === "home" ? g.h_12 : g.a_12) ?? [];
                        const tGeoFin = (manualPersp === "home" ? g.h_geo : g.a_geo) ?? "";
                        const tGeoDyn = (manualPersp === "home" ? (g.h_geo_dyn ?? g.h_geo) : (g.a_geo_dyn ?? g.a_geo)) ?? "";
                        const tGeo = manualGeoKind === "dyn" ? tGeoDyn : tGeoFin;
                        const dPool = getDayPoolBefore(g.day, g.d);
                        const stepRes = computeAutoFilterState(t12, tGeoFin, dPool, manualPersp, false, "fin");
                        const geoRes = computeAutoFilterState(t12, tGeo, dPool, manualPersp, true, manualGeoKind);
                        const f30Val = g.f30 ?? g.vm6 ?? 0;
                        const stepAgrees = (stepRes.hw >= stepRes.aw) === (f30Val >= 0);
                        const geoAgrees = (geoRes.hw >= geoRes.aw) === (f30Val >= 0);
                        const pickGeo =
                          (stepRes.pct < 60 || (stepAgrees && !geoAgrees && stepRes.pct >= 55))
                            ? false
                            : !stepAgrees && geoAgrees && geoRes.pct >= 55
                              ? true
                              : geoRes.pct > stepRes.pct ||
                                (geoRes.pct === stepRes.pct && geoRes.mv > stepRes.mv);
                        const chosen = pickGeo ? geoRes : stepRes;
                        nextMap[g.n] = {
                          ...chosen.state,
                          modeLabel: `هوشمند خودکار (${pickGeo ? "GEO اول" : "گام‌به‌گام"})`,
                          stepSummary: stepRes.sumStr,
                          geoSummary: geoRes.sumStr,
                        };
                        if (idx < 3) openMap[g.n] = true;
                      });
                      setManualFilters(nextMap);
                      setManualOpenGames(openMap);
                    }}
                    className="px-3 py-1.5 rounded-md bg-purple-600 hover:bg-purple-700 text-white font-bold text-[11px] transition-colors shadow-sm"
                  >
                    ⚡ انتخاب هوشمند خودکار برای همه بازی‌های صفحه
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setManualFilters({});
                      try {
                        localStorage.removeItem(MANUAL_STORAGE_KEY);
                      } catch {}
                    }}
                    className="px-3 py-1.5 rounded-md bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-300 font-bold text-[11px] transition-colors"
                  >
                    پاک‌کردن همه فیلترها
                  </button>
                </div>
              </div>

              {/* Column Equivalence Legend (Light Blue) */}
              <div className="bg-sky-50 px-4 py-2 border-b border-sky-200 text-[11px] text-slate-700 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="text-sky-950 font-bold">تطابق دقیق ستون‌ها با شیت محاسبات (Sheet3): </span>
                  <span className="font-mono text-indigo-800 font-semibold mx-1">PRIM 1..4 = ELE-DYN (P+FIN) [FIRE, AIR, WATER, EARTH]</span> •
                  <span className="font-mono text-teal-800 font-semibold mx-1">FINAL 1..4 = ELE-FINAL [FIRE, AIR, WATER, EARTH]</span> •
                  <span className="font-mono text-sky-800 font-semibold mx-1">ELE-P 1..4 = ELE-P [FIRE, AIR, WATER, EARTH]</span> •
                  <span className="font-mono text-amber-800 font-semibold mx-1">GEO-FIG = CODE-DYN</span>
                </div>
                <div className="text-sky-900 font-mono font-semibold">
                  صفحه {safePage} از {totalPages} ({pageGames.length} بازی در این صفحه)
                </div>
              </div>

              {histLoading ? (
                <div className="p-8 text-center text-xs text-sky-800 bg-white flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> در حال بارگذاری ۲۱٬۴۹۸ بازی تاریخی ۲۰۱۰–۲۰۲۶ برای فیلتر دستی...
                </div>
              ) : (
                <div className="divide-y divide-sky-200">
                  {pageGames.map((g, gIdx) => {
                    const isOpen = manualOpenGames[g.n] ?? gIdx === 0;
                    const targetEl12 =
                      (manualPersp === "home" ? g.h_12 : g.a_12) ?? [
                        "0 FIRE", "0 AIR", "0 WATER", "0 EARTH",
                        "0 FIRE", "0 AIR", "0 WATER", "0 EARTH",
                        "0 FIRE", "0 AIR", "0 WATER", "0 EARTH",
                      ];
                    const targetGeoFin =
                      (manualPersp === "home" ? g.h_geo : g.a_geo) ?? "0000";
                    const targetGeoDyn =
                      (manualPersp === "home"
                        ? g.h_geo_dyn ?? g.h_geo
                        : g.a_geo_dyn ?? g.a_geo) ?? "0000";
                    const targetGeoTab =
                      (manualPersp === "home" ? g.h_geo_tab : g.a_geo_tab) ?? "0101";
                    const curState: ManualFilterState = manualFilters[g.n] ?? {
                      cols: {},
                      geo: "ALL",
                      geoTab: "ALL",
                    };
                    const rowGeoKind: "fin" | "dyn" = curState.geoKind ?? manualGeoKind;
                    const targetGeo = rowGeoKind === "dyn" ? targetGeoDyn : targetGeoFin;

                    const dayPool = getDayPoolBefore(g.day, g.d);
                    const getRowEl12 = (r: HistGameRow) => (manualPersp === "home" ? r.h12 : r.a12);
                    const getRowGeo = (r: HistGameRow) =>
                      manualPersp === "home"
                        ? rowGeoKind === "dyn"
                          ? r.hGeoDyn ?? r.hGeo
                          : r.hGeo
                        : rowGeoKind === "dyn"
                          ? r.aGeoDyn ?? r.aGeo
                          : r.aGeo;
                    const getRowGeoTab = (r: HistGameRow) =>
                      manualPersp === "home" ? (r.hGeoTab ?? "") : (r.aGeoTab ?? "");

                    const filteredPool = dayPool.filter((r) => {
                      const el = getRowEl12(r);
                      for (let c = 0; c < 12; c++) {
                        const sel = curState.cols[c];
                        if (sel && sel !== "ALL" && el[c] !== sel) return false;
                      }
                      if (curState.geo && curState.geo !== "ALL" && getRowGeo(r) !== curState.geo) {
                        return false;
                      }
                      if (curState.geoTab && curState.geoTab !== "ALL" && getRowGeoTab(r) !== curState.geoTab) {
                        return false;
                      }
                      return true;
                    });

                    const liveIdx = computePoolNumIndex(filteredPool);
                    const ch3Open =
                      isOpen || manualPersp === "away" || !g.idx3
                        ? computeThreeChannelIndex(targetEl12, targetGeoFin, targetGeoDyn, dayPool, manualPersp, targetGeoTab)
                        : null;
                    const ch3Vh = ch3Open ? ch3Open.votesHome : g.idx3?.vh ?? 0;
                    const ch3Va = ch3Open ? ch3Open.votesAway : g.idx3?.va ?? 0;
                    const ch3MinD = ch3Open ? ch3Open.minDelta : g.idx3?.minD ?? 0;

                    let nextBestCol: number | null = null;
                    let nextBestCnt = -1;
                    if (isOpen && filteredPool.length > 7) {
                      for (let c = 0; c < 12; c++) {
                        if (curState.cols[c] && curState.cols[c] !== "ALL") continue;
                        const tVal = targetEl12[c];
                        if (!tVal) continue;
                        const cnt = filteredPool.filter((r) => getRowEl12(r)[c] === tVal).length;
                        if (cnt >= 5 && cnt < filteredPool.length && cnt > nextBestCnt) {
                          nextBestCnt = cnt;
                          nextBestCol = c;
                        }
                      }
                    }

                    const homeWins = filteredPool.filter((r) => r.mg > 0);
                    const awayWins = filteredPool.filter((r) => r.mg < 0);
                    const hw = homeWins.length;
                    const aw = awayWins.length;
                    const avgHome =
                      hw > 0
                        ? (homeWins.reduce((acc, r) => acc + r.mg, 0) / hw).toFixed(1)
                        : "0.0";
                    const avgAway =
                      aw > 0
                        ? (awayWins.reduce((acc, r) => acc + Math.abs(r.mg), 0) / aw).toFixed(1)
                        : "0.0";
                    const totVotes = Math.max(1, hw + aw);
                    const majPct = ((Math.max(hw, aw) / totVotes) * 100).toFixed(1);
                    const majTeam = hw > aw ? g.h : aw > hw ? g.a : "TIE";

                    const updateGameFilter = (updater: (prev: ManualFilterState) => ManualFilterState) => {
                      setManualFilters((prev) => ({
                        ...prev,
                        [g.n]: updater(prev[g.n] ?? { cols: {}, geo: "ALL" }),
                      }));
                    };

                    const showAll = Boolean(manualShowAllRows[g.n]);
                    const visibleHistRows = showAll ? filteredPool : filteredPool.slice(0, 60);

                    return (
                      <div key={g.n} id={`manual-nba-game-row-${g.n}`} className="bg-white">
                        {/* Accordion Header Bar (Light Pale-Blue Style) */}
                        <div
                          onClick={() =>
                            setManualOpenGames((prev) => ({ ...prev, [g.n]: !isOpen }))
                          }
                          className="px-4 py-2.5 bg-sky-100/75 hover:bg-sky-200/60 cursor-pointer flex flex-wrap items-center justify-between gap-2 border-r-4 border-sky-600 transition-colors"
                        >
                          <div className="flex flex-wrap items-center gap-2.5 font-mono text-xs">
                            <span className="font-extrabold text-sky-950 text-sm">
                              &gt;&gt;&gt; {g.day} {g.d} &lt;&lt;&lt;
                            </span>
                            <span className="text-slate-500 font-bold">#{g.n}</span>
                            <span className="font-bold text-blue-800">{g.h}</span>
                            <span className="text-slate-400">vs</span>
                            <span className="font-bold text-purple-800">{g.a}</span>
                            <span className="px-2 py-0.5 rounded bg-white text-slate-700 border border-sky-200 text-[11px]">
                              {getGameStatus(g) === "PENDING" ? "UPCOMING" : `${g.sc}`}
                            </span>
                            {getGameStatus(g) === "WIN" ? (
                              <span className="px-2 py-0.5 rounded bg-emerald-600 text-white text-[11px] font-bold">
                                WIN ✓ ({getGamePredWinner(g)})
                              </span>
                            ) : getGameStatus(g) === "LOSS" ? (
                              <span className="px-2 py-0.5 rounded bg-rose-600 text-white text-[11px] font-bold">
                                LOSS ✗ (Pred: {getGamePredWinner(g)})
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 text-[11px] font-bold">
                                PENDING
                              </span>
                            )}
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                                activeVip3Of(g)
                                  ? "bg-amber-500 text-slate-950"
                                  : activeF1WtpOf(g)
                                    ? "bg-emerald-600 text-white"
                                    : "bg-slate-200 text-slate-700"
                              }`}
                            >
                              {activeVip3Of(g) ? "ویژه FIRE / VIP ✓" : activeF1WtpOf(g) ? "تایید سیستم جدید ✓" : "خارج از سیگنال"}
                            </span>
                            {(() => {
                              const rw = activeWtpOf(g);
                              if (!rw?.mel) return null;
                              return (
                                <span
                                  className={`px-2 py-0.5 rounded border font-mono text-[10.5px] font-bold ${
                                    rw.mel === "FIRE"
                                      ? "bg-amber-50 text-amber-950 border-amber-300"
                                      : rw.mel === "AIR"
                                        ? "bg-emerald-50 text-emerald-900 border-emerald-300"
                                        : rw.mel === "WATER"
                                          ? "bg-sky-50 text-sky-900 border-sky-300"
                                          : "bg-rose-50 text-rose-900 border-rose-300"
                                  }`}
                                  dir="ltr"
                                  title={`${oddsFreqMode === "daily" ? "Daily" : "Weekly"} (${rw.mon}) • Log5 Home: ${rw.l5h}% | Fair Odds H ${rw.hodds}x / A ${rw.aodds}x`}
                                >
                                  Log5 {oddsFreqMode === "daily" ? "DAY" : "MON"}: {rw.mel} ({rw.hodds}x / {rw.aodds}x)
                                </span>
                              );
                            })()}
                          </div>

                          <div className="flex flex-wrap items-center gap-2 font-mono text-xs" dir="ltr">
                            <span className="bg-white px-2 py-0.5 rounded border border-sky-200">
                              <b className="text-emerald-700">
                                HOME {hw} (+{avgHome})
                              </b>
                              <span className="text-slate-400 mx-1">/</span>
                              <b className="text-rose-700">
                                AWAY {aw} (-{avgAway})
                              </b>
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded border text-[11px] font-bold ${
                                liveIdx.delta > 0
                                  ? "bg-emerald-50 text-emerald-950 border-emerald-300"
                                  : liveIdx.delta < 0
                                    ? "bg-rose-50 text-rose-950 border-rose-300"
                                    : "bg-slate-50 text-slate-700 border-slate-300"
                              }`}
                              title={`H: ${liveIdx.formulaH} = +${liveIdx.idxH} | A: ${liveIdx.formulaA} = -${liveIdx.idxA} | S=${liveIdx.scoreH}:${liveIdx.scoreA}`}
                            >
                              Idx: +{liveIdx.idxH} / -{liveIdx.idxA} (Δ {liveIdx.delta > 0 ? `+${liveIdx.delta}` : liveIdx.delta})
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded font-extrabold text-[11px] ${
                                ch3Vh === 4
                                  ? "bg-emerald-600 text-white"
                                  : ch3Vh > ch3Va
                                    ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                                    : ch3Va === 4
                                      ? "bg-rose-600 text-white"
                                      : ch3Va > ch3Vh
                                        ? "bg-rose-100 text-rose-900 border border-rose-300"
                                        : "bg-slate-100 text-slate-700 border border-slate-300"
                              }`}
                              title={`شکل رملی ۴ خطی روزانه جدول: ${targetGeoTab} (${decodeGeoTabFa(targetGeoTab)})`}
                            >
                              4Ch Δ+S: {ch3Vh}-{ch3Va} {ch3Vh > ch3Va ? "H" : ch3Va > ch3Vh ? "A" : "="} • TAB:{targetGeoTab}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded font-bold text-[11px] ${
                                hw > aw
                                  ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                                  : aw > hw
                                    ? "bg-rose-100 text-rose-900 border border-rose-300"
                                    : "bg-slate-100 text-slate-700 border border-slate-300"
                              }`}
                            >
                              {majTeam} ({majPct}%)
                            </span>
                            <span className="text-sky-950 font-extrabold bg-amber-100 border border-amber-300 px-2 py-0.5 rounded">
                              {filteredPool.length} / {dayPool.length} ردیف
                            </span>
                            <span className="px-2 py-0.5 rounded bg-white border border-sky-300 text-sky-900 font-bold text-[11px]">
                              {isOpen ? "بستن ▲" : "باز کردن ▼"}
                            </span>
                          </div>
                        </div>

                        {/* Expanded Manual Filter Body (Light Pale-Blue & Crisp White) */}
                        {isOpen && (
                          <div className="p-3.5 bg-sky-50/40 space-y-3 border-t border-sky-200">
                            {/* Action Buttons Bar (Exact GOLD-FORMULA-PRIORITY Controls + 3 Independent Channels) */}
                            <div className="flex flex-wrap items-center gap-1.5">
                              {/* 1A. Auto GEO-FIN First */}
                              <button
                                type="button"
                                onClick={() => {
                                  const res = computeAutoFilterState(
                                    targetEl12,
                                    targetGeoFin,
                                    dayPool,
                                    manualPersp,
                                    true,
                                    "fin"
                                  );
                                  setManualGeoKind("fin");
                                  setManualFilters((prev) => ({
                                    ...prev,
                                    [g.n]: res.state,
                                  }));
                                }}
                                className="px-2.5 py-1.5 rounded bg-sky-600 hover:bg-sky-700 text-white font-bold text-[11px] transition-colors shadow-sm"
                              >
                                ۲. انتخاب خودکار (GEO-FIN اول)
                              </button>

                              {/* 1B. Auto GEO-DYN First (Independent Channel 3) */}
                              <button
                                type="button"
                                onClick={() => {
                                  const res = computeAutoFilterState(
                                    targetEl12,
                                    targetGeoDyn,
                                    dayPool,
                                    manualPersp,
                                    true,
                                    "dyn"
                                  );
                                  setManualGeoKind("dyn");
                                  setManualFilters((prev) => ({
                                    ...prev,
                                    [g.n]: res.state,
                                  }));
                                }}
                                className="px-2.5 py-1.5 rounded bg-cyan-700 hover:bg-cyan-800 text-white font-bold text-[11px] transition-colors shadow-sm"
                              >
                                ۳. انتخاب خودکار (GEO-DYN اول)
                              </button>

                              {/* 1C. Auto GEO-TAB First (Independent Channel 4: Daily 4-Line Standings Figure) */}
                              <button
                                type="button"
                                onClick={() => {
                                  const res = computeAutoFilterState(
                                    targetEl12,
                                    targetGeoTab,
                                    dayPool,
                                    manualPersp,
                                    true,
                                    "tab"
                                  );
                                  setManualFilters((prev) => ({
                                    ...prev,
                                    [g.n]: res.state,
                                  }));
                                }}
                                className="px-2.5 py-1.5 rounded bg-amber-600 hover:bg-amber-700 text-white font-extrabold text-[11px] transition-colors shadow-sm"
                                title={decodeGeoTabFa(targetGeoTab)}
                              >
                                ۴. انتخاب خودکار (GEO-TAB جدول اول: {targetGeoTab})
                              </button>

                              {/* 2. Target PRIM (ELE-DYN) */}
                              <button
                                type="button"
                                onClick={() =>
                                  updateGameFilter((prev) => ({
                                    ...prev,
                                    cols: {
                                      ...prev.cols,
                                      0: targetEl12[0],
                                      1: targetEl12[1],
                                      2: targetEl12[2],
                                      3: targetEl12[3],
                                    },
                                    modeLabel: "مقادیر PRIM هدف (ELE-DYN)",
                                  }))
                                }
                                className="px-2.5 py-1.5 rounded bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[11px] transition-colors shadow-sm"
                              >
                                مقادیر PRIM هدف (ELE-DYN)
                              </button>

                              {/* 3. Target FINAL (ELE-FINAL) */}
                              <button
                                type="button"
                                onClick={() =>
                                  updateGameFilter((prev) => ({
                                    ...prev,
                                    cols: {
                                      ...prev.cols,
                                      4: targetEl12[4],
                                      5: targetEl12[5],
                                      6: targetEl12[6],
                                      7: targetEl12[7],
                                    },
                                    modeLabel: "مقادیر FINAL هدف (ELE-FINAL)",
                                  }))
                                }
                                className="px-2.5 py-1.5 rounded bg-teal-600 hover:bg-teal-700 text-white font-bold text-[11px] transition-colors shadow-sm"
                              >
                                مقادیر FINAL هدف (ELE-FINAL)
                              </button>

                              {/* 4. Target ELE-P */}
                              <button
                                type="button"
                                onClick={() =>
                                  updateGameFilter((prev) => ({
                                    ...prev,
                                    cols: {
                                      ...prev.cols,
                                      8: targetEl12[8],
                                      9: targetEl12[9],
                                      10: targetEl12[10],
                                      11: targetEl12[11],
                                    },
                                    modeLabel: "مقادیر ELE-P هدف",
                                  }))
                                }
                                className="px-2.5 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-[11px] transition-colors shadow-sm"
                              >
                                مقادیر ELE-P هدف
                              </button>

                              {/* 5. Pink Next Best Frequency Button */}
                              {nextBestCol !== null && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    const colKey = MANUAL_COL_META[nextBestCol!].key;
                                    const tVal = targetEl12[nextBestCol!];
                                    updateGameFilter((prev) => ({
                                      ...prev,
                                      cols: { ...prev.cols, [nextBestCol!]: tVal },
                                      modeLabel: "گام‌به‌گام دستی",
                                      pathLog: [
                                        ...(prev.pathLog ?? []),
                                        `${colKey}=${tVal} (${nextBestCnt})`,
                                      ],
                                    }));
                                  }}
                                  className="px-3 py-1.5 rounded bg-pink-600 hover:bg-pink-700 text-white font-extrabold text-[11px] transition-colors shadow-sm"
                                >
                                  انتخاب بعدی: {MANUAL_COL_META[nextBestCol].key} ({targetEl12[nextBestCol]}) — تعداد: {nextBestCnt}
                                </button>
                              )}

                              {/* 6. Green Full Step-by-Step Highest Frequency (Independent Channel 1) */}
                              <button
                                type="button"
                                onClick={() => {
                                  const res = computeAutoFilterState(
                                    targetEl12,
                                    targetGeoFin,
                                    dayPool,
                                    manualPersp,
                                    false,
                                    "fin"
                                  );
                                  setManualGeoKind("fin");
                                  setManualFilters((prev) => ({
                                    ...prev,
                                    [g.n]: res.state,
                                  }));
                                }}
                                className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-[11px] transition-colors shadow-sm"
                              >
                                ۱. فیلتر کامل بیشترین تکرار (گام‌به‌گام STEP)
                              </button>

                              {/* 7. Purple Smart Auto-Select (Best of GEO & STEP) */}
                              <button
                                type="button"
                                onClick={() => {
                                  const stepRes = computeAutoFilterState(
                                    targetEl12,
                                    targetGeoFin,
                                    dayPool,
                                    manualPersp,
                                    false,
                                    "fin"
                                  );
                                  const geoRes = computeAutoFilterState(
                                    targetEl12,
                                    targetGeo,
                                    dayPool,
                                    manualPersp,
                                    true,
                                    rowGeoKind
                                  );
                                  const f30Val = g.f30 ?? g.vm6 ?? 0;
                                  const stepAgrees = (stepRes.hw >= stepRes.aw) === (f30Val >= 0);
                                  const geoAgrees = (geoRes.hw >= geoRes.aw) === (f30Val >= 0);
                                  const pickGeo =
                                    (stepRes.pct < 60 || (stepAgrees && !geoAgrees && stepRes.pct >= 55))
                                      ? false
                                      : !stepAgrees && geoAgrees && geoRes.pct >= 55
                                        ? true
                                        : geoRes.pct > stepRes.pct ||
                                          (geoRes.pct === stepRes.pct && geoRes.mv > stepRes.mv);
                                  const chosen = pickGeo ? geoRes : stepRes;
                                  setManualFilters((prev) => ({
                                    ...prev,
                                    [g.n]: {
                                      ...chosen.state,
                                      modeLabel: `هوشمند خودکار (${pickGeo ? "GEO اول" : "گام‌به‌گام"})`,
                                      stepSummary: stepRes.sumStr,
                                      geoSummary: geoRes.sumStr,
                                    },
                                  }));
                                }}
                                className="px-3 py-1.5 rounded bg-purple-600 hover:bg-purple-700 text-white font-extrabold text-[11px] transition-colors shadow-sm"
                              >
                                ⚡ انتخاب هوشمند خودکار (بهترینِ GEO و گام‌به‌گام)
                              </button>

                              {/* 8. Clear Filters */}
                              <button
                                type="button"
                                onClick={() =>
                                  setManualFilters((prev) => ({
                                    ...prev,
                                    [g.n]: { cols: {}, geo: "ALL", geoTab: "ALL" },
                                  }))
                                }
                                className="px-2.5 py-1.5 rounded bg-rose-100 hover:bg-rose-200 text-rose-900 border border-rose-300 font-bold text-[11px] transition-colors"
                              >
                                پاک‌کردن فیلترها
                              </button>

                              {/* 9. Copy for Excel */}
                              <button
                                type="button"
                                onClick={() => {
                                  const headers = [
                                    "#", "DAY", "DATE", "HOME", "AWAY", "SCORE",
                                    ...MANUAL_COL_META.map((m) => m.key),
                                    "GEO-FIG", "GEO-TAB", "MARGIN",
                                  ];
                                  const tRow = [
                                    "TARGET", g.day, g.d, g.h, g.a, g.sc,
                                    ...targetEl12,
                                    targetGeo,
                                    targetGeoTab,
                                    g.st === "PENDING" ? `FUSION:${g.f30 ?? 0}` : g.aw,
                                  ];
                                  const hRows = filteredPool.map((r, i) => [
                                    String(i + 1),
                                    r.day,
                                    r.d,
                                    r.h,
                                    r.a,
                                    `${r.hp}-${r.ap}`,
                                    ...getRowEl12(r),
                                    getRowGeo(r),
                                    getRowGeoTab(r),
                                    r.mg > 0 ? `+${r.mg}` : String(r.mg),
                                  ]);
                                  const tsv = [headers, tRow, ...hRows]
                                    .map((row) => row.join("\t"))
                                    .join("\n");
                                  navigator.clipboard?.writeText(tsv);
                                  setCopiedGame(g.n);
                                  setTimeout(() => setCopiedGame(null), 2000);
                                }}
                                className="px-2.5 py-1.5 rounded bg-white hover:bg-sky-50 text-sky-950 border border-sky-300 font-bold text-[11px] transition-colors shadow-sm"
                              >
                                {copiedGame === g.n ? "کپی شد! ✓" : "کپی برای Excel"}
                              </button>
                            </div>

                            {/* 3-Channel Independent Numerical Index Header Strip (Directly Above 13-Dropdown Table) */}
                            {ch3Open && (
                              <div
                                className="rounded-lg border border-sky-300 bg-white p-2.5 shadow-sm space-y-2"
                                data-testid={`manual-idx3-header-${g.n}`}
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sky-100 pb-1.5">
                                  <div className="text-xs font-extrabold text-sky-950">
                                    سرستون شاخص عددی تقویت‌شده (Δ+S) در ۴ کانال مستقل (هم‌جهتی Δ با مجموع S + کانال ۴ شکل رملی ۴ خطی روزانه جدول GEO-TAB • کلیک روی هر کانال آن را بارگذاری می‌کند)
                                  </div>
                                  <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
                                    <span
                                      className={`px-2.5 py-0.5 rounded font-extrabold ${
                                        ch3Open.votesHome === 4
                                          ? "bg-emerald-600 text-white"
                                          : ch3Open.votesHome > ch3Open.votesAway
                                            ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                                            : ch3Open.votesAway === 4
                                              ? "bg-rose-600 text-white"
                                              : ch3Open.votesAway > ch3Open.votesHome
                                                ? "bg-rose-100 text-rose-900 border border-rose-300"
                                                : "bg-slate-100 text-slate-700 border border-slate-300"
                                      }`}
                                    >
                                      رأی ۴ کانال مستقل (Δ+S): {ch3Open.votesHome} به {ch3Open.votesAway}{" "}
                                      {ch3Open.votesHome > ch3Open.votesAway
                                        ? `به نفع میزبان (${g.h})`
                                        : ch3Open.votesAway > ch3Open.votesHome
                                          ? `به نفع میهمان (${g.a})`
                                          : "مساوی"}
                                      {ch3Open.votesHome === 4 && (
                                        <bdi dir="ltr" className="inline-block mr-1">
                                          (Δmin=+{ch3Open.minDelta})
                                        </bdi>
                                      )}
                                    </span>
                                    <span className="px-2 py-0.5 rounded bg-sky-100 text-sky-950 border border-sky-300 font-bold" dir="ltr">
                                      Active Pool ({filteredPool.length}r): H +{liveIdx.idxH} ({liveIdx.formulaH}) | A -{liveIdx.idxA} ({liveIdx.formulaA}) ➔ Δ={liveIdx.delta > 0 ? `+${liveIdx.delta}` : liveIdx.delta} • S={liveIdx.scoreH}:{liveIdx.scoreA} (Δ+S={liveIdx.effDelta > 0 ? `+${liveIdx.effDelta}` : liveIdx.effDelta})
                                    </span>
                                  </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-2 font-mono text-[11px]">
                                  {[
                                    {
                                      key: "st",
                                      titleFa: "۱. گام‌به‌گام (STEP مستقل)",
                                      res: ch3Open.step,
                                      idx: ch3Open.idxSt,
                                      gKind: "fin" as const,
                                    },
                                    {
                                      key: "gf",
                                      titleFa: "۲. اول شکل رمل اصلاح‌شده (GEO-FIN)",
                                      res: ch3Open.geoFin,
                                      idx: ch3Open.idxGf,
                                      gKind: "fin" as const,
                                    },
                                    {
                                      key: "gd",
                                      titleFa: "۳. اول شکل رمل پویا (GEO-DYN)",
                                      res: ch3Open.geoDyn,
                                      idx: ch3Open.idxGd,
                                      gKind: "dyn" as const,
                                    },
                                    {
                                      key: "gt",
                                      titleFa: `۴. اول شکل رمل جدول روزانه (GEO-TAB ${targetGeoTab})`,
                                      res: ch3Open.geoTab,
                                      idx: ch3Open.idxGt,
                                      gKind: "fin" as const,
                                    },
                                  ].map((ch) => (
                                    <button
                                      key={ch.key}
                                      type="button"
                                      onClick={() => {
                                        setManualGeoKind(ch.gKind);
                                        setManualFilters((prev) => ({
                                          ...prev,
                                          [g.n]: ch.res.state,
                                        }));
                                      }}
                                      className={`text-right rounded-lg p-2 border transition-all hover:shadow ${
                                        ch.idx.effDelta > 0
                                          ? "bg-emerald-50/75 border-emerald-300 hover:bg-emerald-100/70"
                                          : ch.idx.effDelta < 0
                                            ? "bg-rose-50/75 border-rose-300 hover:bg-rose-100/70"
                                            : "bg-slate-50 border-slate-200 hover:bg-sky-50"
                                      }`}
                                    >
                                      <div className="flex items-center justify-between gap-1 mb-1">
                                        <span className="font-sans font-extrabold text-sky-950 text-[10.5px]">
                                          {ch.titleFa}
                                        </span>
                                        <span className="px-1.5 py-0.5 rounded bg-white border border-sky-200 text-[10px] font-bold text-slate-700 whitespace-nowrap" dir="ltr">
                                          {ch.res.unslicedPool.length}r • {ch.idx.hw}H-{ch.idx.aw}A
                                          {ch.res.isNatural57 ? " (5-7✓)" : ""}
                                        </span>
                                      </div>
                                      <div className="flex items-center justify-between gap-1 text-[10px]" dir="ltr">
                                        <span className="text-emerald-800 font-bold">
                                          H: {ch.idx.formulaH} = <b>+{ch.idx.idxH}</b>
                                        </span>
                                        <span className="text-rose-800 font-bold">
                                          A: {ch.idx.formulaA} = <b>-{ch.idx.idxA}</b>
                                        </span>
                                      </div>
                                      <div className="flex items-center justify-between gap-1 mt-1 pt-1 border-t border-black/5 text-[10px]" dir="ltr">
                                        <span className="font-extrabold text-slate-800">
                                          Δ={ch.idx.delta > 0 ? `+${ch.idx.delta}` : ch.idx.delta} • S={ch.idx.scoreH}:{ch.idx.scoreA}
                                        </span>
                                        <span
                                          className={`font-sans font-extrabold px-1.5 py-0.5 rounded ${
                                            ch.idx.effDelta > 0
                                              ? "bg-emerald-600 text-white"
                                              : ch.idx.effDelta < 0
                                                ? "bg-rose-600 text-white"
                                                : "bg-slate-300 text-slate-800"
                                          }`}
                                        >
                                          {ch.idx.effDelta > 0 ? "برد Δ+S میزبان" : ch.idx.effDelta < 0 ? "برد Δ+S میهمان" : "تساوی/خنثی"}
                                        </span>
                                      </div>
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Active Filter Path & STEP vs GEO Comparison Banner (Light Blue) */}
                            {(curState.pathLog?.length || curState.stepSummary) && (
                              <div className="px-3 py-2 rounded bg-sky-100/80 border border-sky-300 text-[11px] font-mono flex flex-wrap items-center justify-between gap-2 text-slate-900">
                                <div>
                                  <span className="text-sky-950 font-extrabold">
                                    {curState.modeLabel ?? "مسیر فیلتر"}:{" "}
                                  </span>
                                  <span className="text-emerald-800 font-bold" dir="ltr">
                                    {curState.pathLog && curState.pathLog.length > 0
                                      ? curState.pathLog.join(" ➔ ")
                                      : "بدون فیلتر (همه بازی‌های روز)"}
                                  </span>
                                </div>
                                {curState.stepSummary && curState.geoSummary && (
                                  <div className="flex items-center gap-3 text-xs">
                                    <span className="text-emerald-800 bg-white px-2 py-0.5 rounded border border-emerald-300">
                                      گام‌به‌گام (STEP): <b>{curState.stepSummary}</b>
                                    </span>
                                    <span className="text-sky-900 bg-white px-2 py-0.5 rounded border border-sky-300">
                                      GEO اول: <b>{curState.geoSummary}</b>
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* 13-Dropdown Filter & Results Table (Light Pale-Blue Theme) */}
                            <div className="overflow-x-auto border border-sky-300 rounded-md bg-white shadow-sm" dir="ltr">
                              <table className="w-full text-[11px] font-mono text-center border-collapse">
                                <thead>
                                  {/* Group Header Row */}
                                  <tr className="bg-sky-100 text-sky-950 border-b border-sky-300">
                                    <th colSpan={5} className="p-1.5 text-left pl-3 text-sky-950 font-extrabold">
                                      MATCHUP INFO ({manualPersp === "home" ? "HOME ELEMENTAL VIEW" : "AWAY ELEMENTAL VIEW"})
                                    </th>
                                    <th colSpan={4} className="p-1.5 bg-indigo-100/90 text-indigo-950 border-x border-sky-300 font-extrabold">
                                      PRIM 1..4 ≡ ELE-DYN (P+FIN) [Sheet3 P:S]
                                    </th>
                                    <th colSpan={4} className="p-1.5 bg-teal-100/90 text-teal-950 border-x border-sky-300 font-extrabold">
                                      FINAL 1..4 ≡ ELE-FINAL [Sheet3 K:N]
                                    </th>
                                    <th colSpan={4} className="p-1.5 bg-sky-200/80 text-sky-950 border-x border-sky-300 font-extrabold">
                                      ELE-P 1..4 ≡ ELE-P [Sheet3 F:I]
                                    </th>
                                    <th className="p-1.5 bg-amber-100/90 text-amber-950 border-x border-sky-300 font-extrabold">
                                      CODE-DYN
                                    </th>
                                    <th className="p-1.5 bg-orange-100/90 text-orange-950 border-x border-sky-300 font-extrabold" title="شکل رملی ۴ خطی روزانه جایگاه دو تیم در جدول (تا شب قبل)">
                                      GEO-TAB
                                    </th>
                                    <th className="p-1.5 text-emerald-900 font-extrabold">RESULT</th>
                                  </tr>

                                  {/* Column Names + Interactive Dropdowns Row */}
                                  <tr className="bg-sky-50 text-slate-800 border-b border-sky-300 align-bottom">
                                    <th className="p-1.5">#</th>
                                    <th className="p-1.5">DAY</th>
                                    <th className="p-1.5">DATE</th>
                                    <th className="p-1.5">HOME vs AWAY</th>
                                    <th className="p-1.5">SCORE</th>

                                    {MANUAL_COL_META.map((col) => {
                                      const cIdx = col.idx;
                                      const selVal = curState.cols[cIdx] ?? "ALL";
                                      const tVal = targetEl12[cIdx] ?? "";
                                      const isNext = nextBestCol === cIdx;

                                      const poolForCol = dayPool.filter((r) => {
                                        const el = getRowEl12(r);
                                        for (let k = 0; k < 12; k++) {
                                          if (k === cIdx) continue;
                                          const s = curState.cols[k];
                                          if (s && s !== "ALL" && el[k] !== s) return false;
                                        }
                                        if (curState.geo && curState.geo !== "ALL" && getRowGeo(r) !== curState.geo) {
                                          return false;
                                        }
                                        if (curState.geoTab && curState.geoTab !== "ALL" && getRowGeoTab(r) !== curState.geoTab) {
                                          return false;
                                        }
                                        return true;
                                      });

                                      const counts: Record<string, number> = {};
                                      poolForCol.forEach((r) => {
                                        const v = getRowEl12(r)[cIdx];
                                        if (v) counts[v] = (counts[v] ?? 0) + 1;
                                      });
                                      if (tVal && !(tVal in counts)) counts[tVal] = 0;

                                      const options = Object.keys(counts).sort((a, b) => {
                                        const na = parseInt(a.split(" ")[0] || "0", 10);
                                        const nb = parseInt(b.split(" ")[0] || "0", 10);
                                        return na - nb;
                                      });

                                      return (
                                        <th
                                          key={col.key}
                                          className={`p-1 border-x border-sky-200 min-w-[92px] ${
                                            selVal !== "ALL"
                                              ? "bg-sky-200/80"
                                              : isNext
                                                ? "bg-pink-100/80"
                                                : ""
                                          }`}
                                        >
                                          {isNext && (
                                            <div className="text-[9px] font-extrabold text-pink-700 mb-0.5 whitespace-nowrap">
                                              ← انتخاب بعدی ({nextBestCnt})
                                            </div>
                                          )}
                                          <div className="text-[10px] font-extrabold text-sky-950">
                                            {col.key}
                                          </div>
                                          <div className="text-[9px] text-slate-600 mb-1">
                                            {col.sub}
                                          </div>
                                          <select
                                            value={selVal}
                                            onChange={(e) => {
                                              const v = e.target.value;
                                              updateGameFilter((prev) => ({
                                                ...prev,
                                                cols: { ...prev.cols, [cIdx]: v },
                                                modeLabel: "فیلتر دستی کاربر",
                                              }));
                                            }}
                                            className={`w-full h-6 rounded px-1 text-[10px] font-mono border ${
                                              selVal !== "ALL"
                                                ? "bg-sky-600 text-white font-extrabold border-sky-700"
                                                : "bg-white text-slate-900 border-sky-300"
                                            }`}
                                          >
                                            <option value="ALL">همه ({poolForCol.length})</option>
                                            {options.map((opt) => (
                                              <option key={opt} value={opt}>
                                                {opt === tVal ? "★ " : ""}
                                                {opt} ({counts[opt]})
                                              </option>
                                            ))}
                                          </select>
                                        </th>
                                      );
                                    })}

                                    {/* 13th Dropdown: GEO-FIG (CODE-DYN) */}
                                    {(() => {
                                      const selGeo = curState.geo ?? "ALL";
                                      const poolForGeo = dayPool.filter((r) => {
                                        const el = getRowEl12(r);
                                        for (let k = 0; k < 12; k++) {
                                          const s = curState.cols[k];
                                          if (s && s !== "ALL" && el[k] !== s) return false;
                                        }
                                        if (curState.geoTab && curState.geoTab !== "ALL" && getRowGeoTab(r) !== curState.geoTab) {
                                          return false;
                                        }
                                        return true;
                                      });
                                      const geoCounts: Record<string, number> = {};
                                      poolForGeo.forEach((r) => {
                                        const gv = getRowGeo(r);
                                        if (gv) geoCounts[gv] = (geoCounts[gv] ?? 0) + 1;
                                      });
                                      if (targetGeo && !(targetGeo in geoCounts)) geoCounts[targetGeo] = 0;
                                      const geoOpts = Object.keys(geoCounts).sort();

                                      return (
                                        <th
                                          className={`p-1 border-x border-sky-200 min-w-[86px] ${
                                            selGeo !== "ALL" ? "bg-sky-200/80" : ""
                                          }`}
                                        >
                                          <div className="text-[10px] font-extrabold text-amber-900">
                                            GEO-FIG
                                          </div>
                                          <div className="text-[9px] text-slate-600 mb-1">
                                            CODE-DYN
                                          </div>
                                          <select
                                            value={selGeo}
                                            onChange={(e) => {
                                              const v = e.target.value;
                                              updateGameFilter((prev) => ({
                                                ...prev,
                                                geo: v,
                                                modeLabel: "فیلتر دستی کاربر",
                                              }));
                                            }}
                                            className={`w-full h-6 rounded px-1 text-[10px] font-mono border ${
                                              selGeo !== "ALL"
                                                ? "bg-sky-600 text-white font-extrabold border-sky-700"
                                                : "bg-white text-slate-900 border-sky-300"
                                            }`}
                                          >
                                            <option value="ALL">همه ({poolForGeo.length})</option>
                                            {geoOpts.map((opt) => (
                                              <option key={opt} value={opt}>
                                                {opt === targetGeo ? "★ " : ""}
                                                {opt} ({geoCounts[opt]})
                                              </option>
                                            ))}
                                          </select>
                                        </th>
                                      );
                                    })()}

                                    {/* 14th Dropdown: GEO-TAB (Daily 4-Line Standings Geomantic Figure) */}
                                    {(() => {
                                      const selTab = curState.geoTab ?? "ALL";
                                      const poolForTab = dayPool.filter((r) => {
                                        const el = getRowEl12(r);
                                        for (let k = 0; k < 12; k++) {
                                          const s = curState.cols[k];
                                          if (s && s !== "ALL" && el[k] !== s) return false;
                                        }
                                        if (curState.geo && curState.geo !== "ALL" && getRowGeo(r) !== curState.geo) {
                                          return false;
                                        }
                                        return true;
                                      });
                                      const tabCounts: Record<string, number> = {};
                                      poolForTab.forEach((r) => {
                                        const tv = getRowGeoTab(r);
                                        if (tv) tabCounts[tv] = (tabCounts[tv] ?? 0) + 1;
                                      });
                                      if (targetGeoTab && !(targetGeoTab in tabCounts)) tabCounts[targetGeoTab] = 0;
                                      const tabOpts = Object.keys(tabCounts).sort();

                                      return (
                                        <th
                                          className={`p-1 border-x border-sky-200 min-w-[92px] ${
                                            selTab !== "ALL" ? "bg-orange-200/80" : ""
                                          }`}
                                          title={decodeGeoTabFa(targetGeoTab)}
                                        >
                                          <div className="text-[10px] font-extrabold text-orange-950">
                                            GEO-TAB
                                          </div>
                                          <div className="text-[9px] text-slate-600 mb-1">
                                            RANK-4L
                                          </div>
                                          <select
                                            value={selTab}
                                            onChange={(e) => {
                                              const v = e.target.value;
                                              updateGameFilter((prev) => ({
                                                ...prev,
                                                geoTab: v,
                                                modeLabel: "فیلتر دستی شکل جدول (GEO-TAB)",
                                              }));
                                            }}
                                            className={`w-full h-6 rounded px-1 text-[10px] font-mono border ${
                                              selTab !== "ALL"
                                                ? "bg-orange-600 text-white font-extrabold border-orange-700"
                                                : "bg-white text-slate-900 border-sky-300"
                                            }`}
                                          >
                                            <option value="ALL">همه ({poolForTab.length})</option>
                                            {tabOpts.map((opt) => (
                                              <option key={opt} value={opt}>
                                                {opt === targetGeoTab ? "★ " : ""}
                                                {opt} ({tabCounts[opt]})
                                              </option>
                                            ))}
                                          </select>
                                        </th>
                                      );
                                    })()}

                                    <th className="p-1.5 min-w-[90px]">
                                      <div className="text-[10px] font-extrabold text-sky-950">MARGIN</div>
                                      <div className="text-[9px] text-slate-600">HOME - AWAY</div>
                                    </th>
                                  </tr>
                                </thead>

                                <tbody>
                                  {/* ROW 0: TARGET GAME ROW (Light Gold/Amber Highlight) */}
                                  <tr className="bg-amber-100/90 border-b-2 border-amber-400 text-amber-950 font-bold">
                                    <td className="p-1.5 text-amber-900 font-extrabold">TARGET</td>
                                    <td className="p-1.5">{g.day}</td>
                                    <td className="p-1.5 whitespace-nowrap">{g.d}</td>
                                    <td className="p-1.5 whitespace-nowrap text-left">
                                      <span className="text-blue-900 font-extrabold">{g.h}</span> vs{" "}
                                      <span className="text-purple-900 font-extrabold">{g.a}</span>
                                    </td>
                                    <td className="p-1.5 whitespace-nowrap">{g.sc}</td>
                                    {targetEl12.map((val, ci) => (
                                      <td
                                        key={ci}
                                        className="p-1.5 border-x border-amber-300 text-amber-950 whitespace-nowrap"
                                      >
                                        ★ {val}
                                      </td>
                                    ))}
                                    <td className="p-1.5 border-x border-amber-300 text-amber-950 font-extrabold">
                                      ★ {targetGeo}
                                    </td>
                                    <td
                                      className="p-1.5 border-x border-amber-300 text-orange-950 font-extrabold"
                                      title={decodeGeoTabFa(targetGeoTab)}
                                    >
                                      ★ {targetGeoTab}
                                    </td>
                                    <td className="p-1.5 whitespace-nowrap">
                                      {g.st === "PENDING" ? (
                                        <span className="text-sky-900 font-extrabold">
                                          FUSION: {(g.f30 ?? 0) > 0 ? `+${g.f30}` : g.f30 ?? 0}
                                        </span>
                                      ) : (
                                        <span
                                          className={
                                            g.aw === g.h ? "text-emerald-800 font-extrabold" : "text-rose-800 font-extrabold"
                                          }
                                        >
                                          WIN: {g.aw}
                                        </span>
                                      )}
                                    </td>
                                  </tr>

                                  {/* FILTERED HISTORICAL TWIN ROWS (2010–2026) */}
                                  {visibleHistRows.map((r, rIdx) => {
                                    const rEl12 = getRowEl12(r);
                                    const rGeo = getRowGeo(r);
                                    const rGeoTab = getRowGeoTab(r);
                                    return (
                                      <tr
                                        key={`${r.d}-${r.h}-${rIdx}`}
                                        className="border-b border-sky-100 even:bg-sky-50/40 hover:bg-sky-100/60 transition-colors text-slate-800"
                                      >
                                        <td className="p-1.5 text-slate-500">{rIdx + 1}</td>
                                        <td className="p-1.5 text-slate-700">{r.day}</td>
                                        <td className="p-1.5 whitespace-nowrap text-slate-900 font-medium">
                                          {r.d}
                                        </td>
                                        <td className="p-1.5 whitespace-nowrap text-left">
                                          <span
                                            className={
                                              r.mg > 0
                                                ? "text-emerald-800 font-bold"
                                                : "text-slate-700"
                                            }
                                          >
                                            {r.h}
                                          </span>{" "}
                                          <span className="text-slate-400">vs</span>{" "}
                                          <span
                                            className={
                                              r.mg < 0
                                                ? "text-rose-800 font-bold"
                                                : "text-slate-700"
                                            }
                                          >
                                            {r.a}
                                          </span>
                                        </td>
                                        <td className="p-1.5 whitespace-nowrap text-slate-700">
                                          {r.hp}-{r.ap}
                                        </td>
                                        {rEl12.map((val, ci) => {
                                          const isMatch = val === targetEl12[ci];
                                          const isFiltered =
                                            curState.cols[ci] && curState.cols[ci] !== "ALL";
                                          return (
                                            <td
                                              key={ci}
                                              className={`p-1.5 border-x border-sky-100 whitespace-nowrap ${
                                                isFiltered
                                                  ? "bg-sky-200/80 text-sky-950 font-extrabold"
                                                  : isMatch
                                                    ? "bg-emerald-50 text-emerald-900 font-semibold"
                                                    : "text-slate-600"
                                              }`}
                                            >
                                              {val}
                                            </td>
                                          );
                                        })}
                                        <td
                                          className={`p-1.5 border-x border-sky-100 font-bold ${
                                            curState.geo && curState.geo !== "ALL"
                                              ? "bg-sky-200/80 text-sky-950"
                                              : rGeo === targetGeo
                                                ? "bg-emerald-50 text-emerald-900"
                                                : "text-slate-600"
                                          }`}
                                        >
                                          {rGeo}
                                        </td>
                                        <td
                                          title={decodeGeoTabFa(rGeoTab)}
                                          className={`p-1.5 border-x border-sky-100 font-bold ${
                                            curState.geoTab && curState.geoTab !== "ALL"
                                              ? "bg-orange-200/80 text-orange-950"
                                              : rGeoTab === targetGeoTab
                                                ? "bg-emerald-50 text-emerald-900"
                                                : "text-slate-600"
                                          }`}
                                        >
                                          {rGeoTab}
                                        </td>
                                        <td
                                          className={`p-1.5 whitespace-nowrap font-bold ${
                                            r.mg > 0 ? "text-emerald-700" : "text-rose-700"
                                          }`}
                                        >
                                          {r.mg > 0 ? `+${r.mg} (HOME)` : `${r.mg} (AWAY)`}
                                        </td>
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            </div>

                            {/* Show More toggle if > 60 rows */}
                            {filteredPool.length > 60 && (
                              <div className="text-center pt-1">
                                <button
                                  type="button"
                                  onClick={() =>
                                    setManualShowAllRows((prev) => ({
                                      ...prev,
                                      [g.n]: !showAll,
                                    }))
                                  }
                                  className="px-3 py-1 rounded bg-white hover:bg-sky-100 text-sky-900 border border-sky-300 text-xs font-mono font-bold shadow-sm"
                                >
                                  {showAll
                                    ? "نمایش ۶۰ ردیف اول"
                                    : `نمایش تمام ${filteredPool.length} ردیف همزاد فیلترشده...`}
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Collapsible Dropdown 3: Summary Games & Predictions Table */}
        <div className="rounded-lg border border-sky-200 bg-sky-50/50 overflow-hidden">
          <div
            onClick={() => setOpenSummaryTable((v) => !v)}
            className="px-4 py-2.5 bg-sky-100/80 hover:bg-sky-100 cursor-pointer flex flex-wrap items-center justify-between gap-2 border-b border-sky-200/80 transition-colors"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-sky-950">
              <span>📋 جدول خلاصه کل بازی‌ها و پیش‌بینی‌ها ({filteredGames.length} بازی فیلترشده)</span>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenSummaryTable((v) => !v);
              }}
              className="px-3 py-1 rounded border border-sky-300 bg-white hover:bg-sky-50 text-sky-950 text-xs font-bold shadow-sm"
            >
              {openSummaryTable ? "بستن جدول خلاصه ▲" : "باز کردن جدول خلاصه کل بازی‌ها ▼"}
            </button>
          </div>
          {openSummaryTable && (
            <div className="p-3 bg-white">
        {loading ? (
          <div className="p-6 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading 2,642 NBA games + 2010–2026 Twins...
          </div>
        ) : (
          <div className="bg-white border border-sky-200 rounded-md overflow-hidden">
            <div className="overflow-x-auto max-h-[540px]">
              <table className="w-full text-[11px] font-mono text-left border-collapse">
                <thead className="bg-slate-100 text-slate-700 sticky top-0 z-10 border-b border-slate-200">
                  {engineMode === "twins" || engineMode === "manual" ? (
                    <tr>
                      <th className="p-2">#</th>
                      <th className="p-2">Date</th>
                      <th className="p-2">Home Team (میزبان)</th>
                      <th className="p-2">Away Team (میهمان)</th>
                      <th className="p-2">Fusion (30)</th>
                      <th className="p-2">SMART Twins (2010–2026)</th>
                      <th className="p-2">Formula_5 (Full / LOO)</th>
                      <th className="p-2">TP1 / TP2 / TP3</th>
                      <th className="p-2">Twin × Fusion</th>
                      <th className="p-2">Predicted Winner</th>
                      <th className="p-2">Actual / Score</th>
                      <th className="p-2">Status</th>
                    </tr>
                  ) : engineMode === "fusion" ? (
                    <tr>
                      <th className="p-2">#</th>
                      <th className="p-2">Date</th>
                      <th className="p-2">Home Team (میزبان)</th>
                      <th className="p-2">Away Team (میهمان)</th>
                      <th className="p-2">5 Methods (A / B / C / D / E)</th>
                      <th className="p-2">Pure Astro (25)</th>
                      <th className="p-2">Fusion (30)</th>
                      <th className="p-2">Fusion Tier</th>
                      <th className="p-2">Predicted Winner</th>
                      <th className="p-2">Actual / Score</th>
                      <th className="p-2">Status</th>
                    </tr>
                  ) : (
                    <tr>
                      <th className="p-2">#</th>
                      <th className="p-2">Date</th>
                      <th className="p-2">Home Team (میزبان)</th>
                      <th className="p-2">Away Team (میهمان)</th>
                      <th className="p-2">QULITY-FIN (H vs A)</th>
                      <th className="p-2">QULITY-DECAN (H vs A)</th>
                      <th className="p-2">VM6</th>
                      <th className="p-2">Pattern Tier</th>
                      <th className="p-2">Predicted Winner</th>
                      <th className="p-2">Actual / Score</th>
                      <th className="p-2">Status</th>
                    </tr>
                  )}
                </thead>
                <tbody>
                  {pageGames.map((g) => {
                    const isExp = expandedGame === g.n;
                    const st = getGameStatus(g);
                    const pw = getGamePredWinner(g);
                    const f30 = g.f30 ?? g.vm6;
                    const a25 = g.a25 ?? 0;
                    const mv = g.mv ?? [g.vm6, 0, 0, 0, 0];
                    return (
                      <Fragment key={g.n}>
                        <tr
                          onClick={() => setExpandedGame(isExp ? null : g.n)}
                          className="border-b border-slate-100 hover:bg-sky-50/70 cursor-pointer transition-colors"
                        >
                          <td className="p-2 font-bold text-slate-500">#{g.n}</td>
                          <td className="p-2 whitespace-nowrap">{g.d}</td>
                          <td className="p-2 font-semibold text-blue-800">{g.h}</td>
                          <td className="p-2 text-purple-800">{g.a}</td>
                          {engineMode === "twins" || engineMode === "manual" ? (
                            <>
                              <td className="p-2 font-extrabold text-sky-950 text-xs">
                                {f30 > 0 ? `+${f30}` : f30}
                              </td>
                              <td className="p-2 whitespace-nowrap">
                                <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-900 border border-emerald-200 font-bold text-[10px]">
                                  [{g.twMode || "STEP"}] {g.twVotes || "4H-3A"} ({g.twPct || "57%"})
                                </span>
                              </td>
                              <td className="p-2 whitespace-nowrap text-[10px]">
                                <span className="font-bold text-slate-900">{g.vip ? "VIP Dual-88" : g.f1 ? "تلفیق ۱ ✓" : "—"}</span>
                                <span className="text-slate-400 mx-1">/</span>
                                <span className="text-sky-700 font-semibold">{g.a1_veto ? "وتو ۸۸ ⛔" : g.s_a1 ? "گارد ۸۸ ✓" : "آزاد"}</span>
                              </td>
                              <td className="p-2 whitespace-nowrap text-[10px] font-bold text-amber-800">
                                {g.tp ? `+${g.tp[0]} / +${g.tp[1]} / +${g.tp[2]} gls` : "—"}
                              </td>
                              <td className="p-2 whitespace-nowrap">
                                {g.twAgree ? (
                                  <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 text-[10px] font-bold">
                                    AGREE ✓
                                  </span>
                                ) : (
                                  <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300 text-[10px] font-bold">
                                    SPLIT ⚠
                                  </span>
                                )}
                              </td>
                            </>
                          ) : engineMode === "fusion" ? (
                            <>
                              <td className="p-2 whitespace-nowrap text-[10px]">
                                {mv.map((v, idx) => (
                                  <span
                                    key={idx}
                                    className={`inline-block px-1 py-0.5 mr-0.5 rounded ${
                                      v > 0
                                        ? "bg-blue-50 text-blue-800 font-bold"
                                        : v < 0
                                          ? "bg-purple-50 text-purple-800 font-bold"
                                          : "bg-slate-100 text-slate-500"
                                    }`}
                                  >
                                    {v > 0 ? `+${v}` : v}
                                  </span>
                                ))}
                              </td>
                              <td className="p-2 font-semibold text-slate-700">
                                {a25 > 0 ? `+${a25}` : a25}
                              </td>
                              <td className="p-2 font-extrabold text-sky-950 text-xs">
                                {f30 > 0 ? `+${f30}` : f30}
                              </td>
                              <td className="p-2 whitespace-nowrap">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                    (g.f30 ?? 0) >= 12
                                      ? "bg-amber-100 text-amber-900 border border-amber-300"
                                      : (g.f30 ?? 0) >= 8
                                        ? "bg-sky-100 text-sky-900 border border-sky-300"
                                        : Math.abs(g.f30 ?? 0) >= 6
                                          ? "bg-indigo-50 text-indigo-800 border border-indigo-200"
                                          : "bg-slate-100 text-slate-600"
                                  }`}
                                >
                                  {(g.f30 ?? 0) >= 12 ? "F30 ≥ +12" : (g.f30 ?? 0) >= 8 ? "F30 ≥ +8" : `F30=${g.f30 ?? 0}`}
                                </span>
                              </td>
                            </>
                          ) : (
                            <>
                              <td className="p-2 whitespace-nowrap text-[10px] font-mono">
                                88 / {g.deg?.[1] ?? 0} / {g.deg?.[2] ?? 0}
                              </td>
                              <td className="p-2 whitespace-nowrap text-[10px] font-mono">
                                88 / {g.deg?.[3] ?? 0} / {g.deg?.[4] ?? 0}
                              </td>
                              <td className="p-2 font-bold text-sky-900">{g.f30 && g.f30 > 0 ? `+${g.f30}` : (g.f30 ?? 0)}</td>
                              <td className="p-2 whitespace-nowrap">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                    g.vip
                                      ? "bg-amber-100 text-amber-900 border border-amber-300"
                                      : g.f1
                                        ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                                        : g.a1_veto
                                          ? "bg-rose-100 text-rose-900 border border-rose-300"
                                          : "bg-slate-100 text-slate-600"
                                  }`}
                                >
                                  {g.vip ? "VIP Dual-88" : g.f1 ? "تلفیق ۱ ✓" : g.a1_veto ? "وتوی گارد ۸۸" : "رد فیلتر"}
                                </span>
                              </td>
                            </>
                          )}
                          <td className="p-2 font-bold text-slate-900">{pw}</td>
                          <td className="p-2 whitespace-nowrap text-[10px] text-slate-600">
                            {st === "PENDING" ? "Scheduled" : g.aw}
                          </td>
                          <td className="p-2">
                            {st === "WIN" ? (
                              <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold">WIN ✓</span>
                            ) : st === "LOSS" ? (
                              <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold">LOSS ✗</span>
                            ) : (
                              <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">PENDING</span>
                            )}
                          </td>
                        </tr>
                        {isExp && (
                          <tr key={`exp-${g.n}`} className="bg-sky-50/90 border-b border-sky-200">
                            <td colSpan={12} className="p-3.5">
                              <div className="text-xs font-bold text-sky-950 mb-2">
                                جزئیات کامل همزادهای المنتی (۲۰۱۰–۲۰۲۶)، ۵ روش تلفیقی و ۹ لایه عنصری بازی #{g.n} ({g.h} vs {g.a} • {g.sc})
                              </div>
                              {g.twPeers && g.twPeers.length > 0 && (
                                <div className="mb-3 p-3 rounded-lg bg-emerald-50/90 border border-emerald-300">
                                  <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                                    <div className="text-[11px] font-bold text-emerald-950">
                                      همزادهای استخراج‌شده از ۲۱٬۴۹۸ بازی تاریخی (۲۰۱۰–۲۰۲۶) • روش: {g.twMode} • رأی همزادها: {g.twVotes} ({g.twPct}) → {g.twWin}
                                    </div>
                                    <div className="text-[11px] font-mono font-bold text-amber-900 bg-amber-100 px-2.5 py-0.5 rounded border border-amber-300">
                                      Spread Targets: TP1 +{g.tp?.[0]} pts | TP2 +{g.tp?.[1]} pts | TP3 +{g.tp?.[2]} pts
                                    </div>
                                  </div>
                                  <div className="text-[11px] font-mono text-slate-700 mb-2 bg-white px-2.5 py-1 rounded border border-emerald-200">
                                    <b>Narrowing Path (ELE-P / ELE-FINAL / ELE-DYN):</b> {g.twPath}
                                  </div>
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                                    {g.twPeers.map((peerStr, pi) => (
                                      <div key={pi} className="text-[11px] font-mono bg-white px-2.5 py-1 rounded border border-emerald-200 text-slate-800">
                                        <b className="text-emerald-700">Twin #{pi + 1}:</b> {peerStr}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5 text-[11px]">
                                <div className="bg-white p-2.5 rounded border border-sky-300">
                                  <div className="font-bold text-sky-900 mb-1">5-Method Fusion Breakdown (30 Votes)</div>
                                  <div><b>Method A (3L+NewDEG3+UTC00):</b> {mv[0] > 0 ? `+${mv[0]}` : mv[0]}</div>
                                  <div><b>Method B (Full+NewDEG3+UTC00):</b> {mv[1] > 0 ? `+${mv[1]}` : mv[1]}</div>
                                  <div><b>Method C (3L+NewDEG3+Local):</b> {mv[2] > 0 ? `+${mv[2]}` : mv[2]}</div>
                                  <div><b>Method D (3L+OldDEG3+UTC00):</b> {mv[3] > 0 ? `+${mv[3]}` : mv[3]}</div>
                                  <div><b>Method E (115+Full+OldDEG3):</b> {mv[4] > 0 ? `+${mv[4]}` : mv[4]}</div>
                                  <div className="mt-1 pt-1 border-t border-slate-200 font-bold text-emerald-800">
                                    FUSION_30 = {f30 > 0 ? `+${f30}` : f30} | PURE_ASTRO_25 = {a25 > 0 ? `+${a25}` : a25} ({g.ag5 ?? 0}/5 Agree)
                                  </div>
                                </div>
                                <div className="bg-white p-2.5 rounded border border-sky-200">
                                  <div className="font-bold text-slate-700 mb-1">درجات سیستم جدید NBA (ATP: DEG1=121 [1° LEO] • WTA: DEG1=47 [17° TAURUS])</div>
                                  <div><b>میزبان ({g.hc}):</b> DEG1=53 | DEG2={g.deg?.[1]} | DEG3={g.deg?.[2]}</div>
                                  <div><b>میهمان ({g.ac}):</b> DEG1=53 | DEG2={g.deg?.[3]} | DEG3={g.deg?.[4]}</div>
                                  <div><b>استادیوم میزبان:</b> {g.venue}</div>
                                  <div><b>تاریخ شمسی:</b> {g.sh_d} ({g.sh_m})</div>
                                </div>
                                <div className="bg-white p-2.5 rounded border border-sky-200">
                                  <div className="font-bold text-slate-700 mb-1">درجات نگهبان سیستم اول ۸۸ (S_A1 Guard)</div>
                                  <div><b>میزبان ({g.hc}):</b> DEG1=53 | DEG2={g.deg?.[5]} | DEG3={g.deg?.[7]}</div>
                                  <div><b>میهمان ({g.ac}):</b> DEG1=53 | DEG2={g.deg?.[6]} | DEG3={g.deg?.[7]}</div>
                                  <div><b>وضعیت سیستم اول:</b> {g.s_a1 ? "تأیید میزبان ✓" : g.a1_veto ? "وتوی میهمان ⛔" : "آزاد (بدون وتو)"}</div>
                                </div>
                                <div className="bg-white p-2.5 rounded border border-sky-200">
                                  <div className="font-bold text-slate-700 mb-1">شکل رمل دوگانه (GEO-FIN & GEO-DYN)</div>
                                  <div><b>GEO-FIN میزبان/میهمان:</b> {g.h_geo} vs {g.a_geo}</div>
                                  <div><b>GEO-DYN میزبان/میهمان:</b> {g.h_geo_dyn} vs {g.a_geo_dyn}</div>
                                  <div><b>کانال منتخب:</b> {g.chan} | <b>تلفیق ۱:</b> {g.f1 ? "واجد شرایط ✓" : "رد فیلتر"}</div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="bg-slate-50 px-4 py-2.5 border-t border-slate-200 flex items-center justify-between text-xs font-mono">
              <span>
                Page {safePage} of {totalPages} (Click any row to inspect 2010–2026 Twins, 5-Method Fusion & 9 Layers)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={safePage <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={safePage >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

