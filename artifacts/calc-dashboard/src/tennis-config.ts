/**
 * Authoritative Astro-Gematria & Isolation Configuration for the 3-App Tennis System.
 *
 * STRICT ARCHITECTURAL RULE:
 * - 100% Astro-Gematria (Name Gematria + pyswisseph Match Sky + Fixed Tour DEG1).
 * - ZERO Player Birthdates (BIRTHDATE_USED = false).
 * - ATP: Gematria 481 -> 481 - 360 = 121 -> DEG1 = 121 (1° LEO • FIRE • Kalshi KXATPMATCH)
 * - WTA: Gematria 407 -> 407 - 360 = 47  -> DEG1 = 47  (17° TAURUS • EARTH • Kalshi KXWTAMATCH)
 * - 100% isolated from NBA-PLAYERS-GEOMANTIC-INPUT, NBA-FUSION-CALCULATION, and all NBA/NHL sheets.
 */

export type TennisTour = "ATP" | "WTA";

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

export const ARCHITECTURE_MODE = "ASTRO_GEMATRIA_NAME_AND_MATCH_SKY" as const;
export const BIRTHDATE_USED = false as const;
export const TENNIS_SHEETS_WRITE_ENABLED = false as const;

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

export function normalizeTennisTour(raw?: string | null): TennisTour {
  return String(raw ?? "ATP").trim().toUpperCase() === "WTA" ? "WTA" : "ATP";
}

export function getTennisTourProfile(raw?: string | null): TennisTourProfile {
  return TENNIS_TOURS[normalizeTennisTour(raw)];
}
