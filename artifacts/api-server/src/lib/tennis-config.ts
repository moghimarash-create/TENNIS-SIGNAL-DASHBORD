/**
 * Authoritative Astro-Gematria & Isolation Configuration for the 2-App Tennis System
 * (TENNIS-SIGNAL-DASHBORD & TENNIS-FUSION-SIGNAL).
 *
 * STRICT ARCHITECTURAL INVARIANTS:
 * - 100% Astro-Gematria (EnglishGem Name Gematria + pyswisseph Match Sky + Fixed Tour DEG1).
 * - ZERO Player Birthdates (BIRTHDATE_USED = false).
 * - ATP: EnglishGem("ATP") = 481 -> 481 mod 360 = 121 -> DEG1 = 121 (1° LEO • FIRE • KXATPMATCH)
 * - WTA: EnglishGem("WTA") = 407 -> 407 mod 360 = 47  -> DEG1 = 47  (17° TAURUS • EARTH • KXWTAMATCH)
 * - 100% isolated from NBA-PLAYERS-GEOMANTIC-INPUT, NBA-FUSION-CALCULATION, and all NBA/NHL sheets.
 */

export type TennisTour = "ATP" | "WTA";
export type TennisTourScope = "ATP" | "WTA" | "ALL";
export type Deg3OptionKey = "opt1" | "opt2" | "opt3";

export const ARCHITECTURE_MODE = "ASTRO_GEMATRIA_NAME_AND_MATCH_SKY" as const;
export const BIRTHDATE_USED = false as const;
export const TENNIS_SHEETS_WRITE_ENABLED = false as const;

export const ENGLISH_GEM_MAP: Readonly<Record<string, number>> = {
  A: 1,
  B: 2,
  G: 3,
  D: 4,
  E: 5,
  U: 6,
  V: 6,
  W: 6,
  Z: 7,
  H: 8,
  I: 10,
  J: 10,
  Y: 10,
  C: 20,
  K: 20,
  L: 30,
  M: 40,
  N: 50,
  S: 60,
  O: 70,
  X: 70,
  F: 80,
  P: 80,
  Q: 100,
  R: 200,
  T: 400,
};

export function cleanAscii(raw?: string | null): string {
  return String(raw ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}

export function englishGem(raw?: string | null): number {
  const clean = cleanAscii(raw).toUpperCase();
  let sum = 0;
  for (let i = 0; i < clean.length; i++) {
    sum += ENGLISH_GEM_MAP[clean[i]] ?? 0;
  }
  return sum;
}

export function degFromName(raw?: string | null): number {
  return englishGem(raw) % 360;
}

if (englishGem("ATP") !== 481 || degFromName("ATP") !== 121) {
  throw new Error("EnglishGem('ATP') self-check failed: expected 481 -> 121");
}
if (englishGem("WTA") !== 407 || degFromName("WTA") !== 47) {
  throw new Error("EnglishGem('WTA') self-check failed: expected 407 -> 47");
}
if (englishGem("123 !@# -_.") !== 0) {
  throw new Error("EnglishGem non-alpha self-check failed: expected 0");
}

export interface TennisTourProfile {
  tour: TennisTour;
  labelFa: string;
  gematria: number;
  deg1: number;
  zodiac: string;
  zodiacDisplay: string;
  signFa: string;
  houseIndex0: number;
  signNumber1: number;
  element: "FIRE" | "EARTH";
  kalshiSeries: "KXATPMATCH" | "KXWTAMATCH";
}

export const TENNIS_TOURS: Record<TennisTour, TennisTourProfile> = {
  ATP: {
    tour: "ATP",
    labelFa: "تور مردان ATP",
    gematria: 481,
    deg1: 121,
    zodiac: "1 LEO",
    zodiacDisplay: "1° LEO",
    signFa: "برج شیر (LEO)",
    houseIndex0: 4,
    signNumber1: 5,
    element: "FIRE",
    kalshiSeries: "KXATPMATCH",
  },
  WTA: {
    tour: "WTA",
    labelFa: "تور زنان WTA",
    gematria: 407,
    deg1: 47,
    zodiac: "17 TAURUS",
    zodiacDisplay: "17° TAURUS",
    signFa: "برج ثور (TAURUS)",
    houseIndex0: 1,
    signNumber1: 2,
    element: "EARTH",
    kalshiSeries: "KXWTAMATCH",
  },
};

export const DEG3_OPTIONS: Record<
  Deg3OptionKey,
  { key: Deg3OptionKey; code: string; shortFa: string; formulaEn: string }
> = {
  opt1: {
    key: "opt1",
    code: "CITY_PLUS_TOURNAMENT",
    shortFa: "آپشن ۱: شهر + نام تورنمنت (CITY_PLUS_TOURNAMENT)",
    formulaEn: "DEG3 = MOD(EnglishGem(Tournament_City), 360) + MOD(EnglishGem(Tournament_Name), 360)",
  },
  opt2: {
    key: "opt2",
    code: "TOURNAMENT_ONLY",
    shortFa: "آپشن ۲: فقط نام تورنمنت (TOURNAMENT_ONLY)",
    formulaEn: "DEG3 = MOD(EnglishGem(Tournament_Name), 360)",
  },
  opt3: {
    key: "opt3",
    code: "CITY_ONLY",
    shortFa: "آپشن ۳: فقط شهر تورنمنت (CITY_ONLY)",
    formulaEn: "DEG3 = MOD(EnglishGem(Tournament_City), 360)",
  },
};

export function normalizeTennisTour(raw?: string | null): TennisTour {
  return String(raw ?? "ATP").trim().toUpperCase() === "WTA" ? "WTA" : "ATP";
}

export function getTennisTourProfile(raw?: string | null): TennisTourProfile {
  return TENNIS_TOURS[normalizeTennisTour(raw)];
}
