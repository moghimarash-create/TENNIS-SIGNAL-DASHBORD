"""Authoritative Astro-Gematria & Isolation Configuration for the 3-App Tennis System.

STRICT ARCHITECTURAL INVARIANT:
- 100% Astro-Gematria (Player Name / Tournament + City + Venue Name Gematria
  + pyswisseph planetary positions at match timestamp & venue coordinates + fixed tour DEG1).
- ZERO dependency on player birthdates (BIRTHDATE_USED = False).
- 100% isolated from live NBA and NHL Google Sheets & state files.
"""
from __future__ import annotations

import os
import unicodedata
from typing import Any, Final

ARCHITECTURE_MODE: Final[str] = "ASTRO_GEMATRIA_NAME_AND_MATCH_SKY"
BIRTHDATE_USED: Final[bool] = False

EGEM_MAP: Final[dict[str, int]] = {
    "A": 1, "B": 2, "C": 20, "D": 4, "E": 5, "F": 80, "G": 3, "H": 8,
    "I": 10, "J": 10, "K": 20, "L": 30, "M": 40, "N": 50, "O": 70, "P": 80,
    "Q": 100, "R": 200, "S": 60, "T": 400, "U": 6, "V": 6, "W": 6, "X": 70,
    "Y": 10, "Z": 7,
}

ZODIAC_SIGNS_12: Final[tuple[str, ...]] = (
    "ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO",
    "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES",
)

SIGN_ELEMENTS: Final[dict[str, str]] = {
    "ARIES": "FIRE", "LEO": "FIRE", "SAGITTARIUS": "FIRE",
    "TAURUS": "EARTH", "VIRGO": "EARTH", "CAPRICORN": "EARTH",
    "GEMINI": "AIR", "LIBRA": "AIR", "AQUARIUS": "AIR",
    "CANCER": "WATER", "SCORPIO": "WATER", "PISCES": "WATER",
}


def clean_ascii(text: str | None) -> str:
    norm = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in norm if not unicodedata.combining(ch)).strip()


def egem(text: str | None) -> int:
    return sum(EGEM_MAP.get(ch, 0) for ch in clean_ascii(text).upper())


def deg_from_name(text: str | None) -> int:
    return egem(text) % 360


def zodiac_from_deg(deg: int) -> tuple[str, str, int]:
    d = int(deg) % 360
    house_idx = d // 30
    within_deg = d % 30
    sign = ZODIAC_SIGNS_12[house_idx]
    return f"{within_deg} {sign}", SIGN_ELEMENTS[sign], house_idx


# ---------------------------------------------------------------------------
# FIXED TOUR ASTRO-GEMATRIA CONSTANTS (ATP & WTA)
# ---------------------------------------------------------------------------
# ATP: A(1) + T(400) + P(80) = 481 -> 481 - 360 = 121 -> 1° LEO (FIRE, house 4 from 0 / 5th sign)
ATP_GEMATRIA: Final[int] = 481
ATP_DEG1: Final[int] = 121
ATP_ZODIAC: Final[str] = "1 LEO"
ATP_ZODIAC_DISPLAY: Final[str] = "1° LEO"
ATP_HOUSE_INDEX_0: Final[int] = 4
ATP_ELEMENT: Final[str] = "FIRE"
ATP_KALSHI_SERIES: Final[str] = "KXATPMATCH"

# WTA: W(6) + T(400) + A(1) = 407 -> 407 - 360 = 47 -> 17° TAURUS (EARTH, house 1 from 0 / 2nd sign)
WTA_GEMATRIA: Final[int] = 407
WTA_DEG1: Final[int] = 47
WTA_ZODIAC: Final[str] = "17 TAURUS"
WTA_ZODIAC_DISPLAY: Final[str] = "17° TAURUS"
WTA_HOUSE_INDEX_0: Final[int] = 1
WTA_ELEMENT: Final[str] = "EARTH"
WTA_KALSHI_SERIES: Final[str] = "KXWTAMATCH"

assert egem("ATP") == ATP_GEMATRIA and (ATP_GEMATRIA % 360) == ATP_DEG1
assert egem("WTA") == WTA_GEMATRIA and (WTA_GEMATRIA % 360) == WTA_DEG1
assert zodiac_from_deg(ATP_DEG1) == (ATP_ZODIAC, ATP_ELEMENT, ATP_HOUSE_INDEX_0)
assert zodiac_from_deg(WTA_DEG1) == (WTA_ZODIAC, WTA_ELEMENT, WTA_HOUSE_INDEX_0)

TENNIS_TOURS: Final[dict[str, dict[str, Any]]] = {
    "ATP": {
        "tour": "ATP",
        "gematria": ATP_GEMATRIA,
        "deg1": ATP_DEG1,
        "zodiac": ATP_ZODIAC,
        "zodiac_display": ATP_ZODIAC_DISPLAY,
        "house_index_0": ATP_HOUSE_INDEX_0,
        "sign_number_1": 5,
        "element": ATP_ELEMENT,
        "kalshi_series": ATP_KALSHI_SERIES,
        "birthdate_used": False,
    },
    "WTA": {
        "tour": "WTA",
        "gematria": WTA_GEMATRIA,
        "deg1": WTA_DEG1,
        "zodiac": WTA_ZODIAC,
        "zodiac_display": WTA_ZODIAC_DISPLAY,
        "house_index_0": WTA_HOUSE_INDEX_0,
        "sign_number_1": 2,
        "element": WTA_ELEMENT,
        "kalshi_series": WTA_KALSHI_SERIES,
        "birthdate_used": False,
    },
}

DEFAULT_TOUR: Final[str] = os.environ.get("TENNIS_DEFAULT_TOUR", "ATP").strip().upper() or "ATP"


def normalize_tour(tour: str | None) -> str:
    t = str(tour or DEFAULT_TOUR).strip().upper()
    return "WTA" if t == "WTA" else "ATP"


def get_tour_deg1(tour: str | None = None) -> int:
    return WTA_DEG1 if normalize_tour(tour) == "WTA" else ATP_DEG1


def get_tour_kalshi_series(tour: str | None = None) -> str:
    return WTA_KALSHI_SERIES if normalize_tour(tour) == "WTA" else ATP_KALSHI_SERIES


# ---------------------------------------------------------------------------
# GOOGLE SHEETS ISOLATION & AUTO-WRITE PROTECTION
# ---------------------------------------------------------------------------
# Auto-writing to Google Sheets is strictly DISABLED by default so no NBA/NHL
# or unconfigured external sheet is ever modified automatically.
TENNIS_SHEETS_WRITE_ENABLED: Final[bool] = (
    os.environ.get("TENNIS_SHEETS_WRITE_ENABLED", "0").strip() == "1"
)

# Dedicated optional Tennis Spreadsheet IDs (empty by default until explicitly created)
TENNIS_DASHBORD_INPUT_SHEET_ID: Final[str] = os.environ.get("TENNIS_DASHBORD_INPUT_SHEET_ID", "").strip()
TENNIS_ASTRO_INPUT_SHEET_ID: Final[str] = os.environ.get("TENNIS_ASTRO_INPUT_SHEET_ID", "").strip()
TENNIS_ASTRO_HEADER_SHEET_ID: Final[str] = os.environ.get("TENNIS_ASTRO_HEADER_SHEET_ID", "").strip()
TENNIS_ASTRO_ASPECTS_SHEET_ID: Final[str] = os.environ.get("TENNIS_ASTRO_ASPECTS_SHEET_ID", "").strip()
TENNIS_RESULT_DEGREE_SHEET_ID: Final[str] = os.environ.get("TENNIS_RESULT_DEGREE_SHEET_ID", "").strip()
TENNIS_CALC_SHEET_ID: Final[str] = os.environ.get("TENNIS_CALC_SHEET_ID", "").strip()

TENNIS_PLAYERS_INPUT_SHEET_ID: Final[str] = os.environ.get("TENNIS_PLAYERS_INPUT_SHEET_ID", "").strip()
TENNIS_PLAYERS_CALC_SHEET_ID: Final[str] = os.environ.get("TENNIS_PLAYERS_CALC_SHEET_ID", "").strip()

TENNIS_FUSION_INPUT_SHEET_ID: Final[str] = os.environ.get("TENNIS_FUSION_INPUT_SHEET_ID", "").strip()
TENNIS_FUSION_CALC_SHEET_ID: Final[str] = os.environ.get("TENNIS_FUSION_CALC_SHEET_ID", "").strip()

# Hard blocklist of known NBA/NHL/Legacy Google Sheet prefixes or names
FORBIDDEN_SHEET_NAME_TOKENS: Final[tuple[str, ...]] = (
    "NBA-PLAYERS-GEOMANTIC-INPUT",
    "NBA-FUSION-CALCULATION",
    "NBA-FUSION-INPUT",
    "NBA-PLAYERS-CALCULATION",
    "NHL-",
)


def assert_isolated_tennis_sheet(spreadsheet_id: str | None) -> str:
    sid = str(spreadsheet_id or "").strip()
    if not sid or sid.startswith("TENNIS_ISOLATED_"):
        raise RuntimeError(
            "TENNIS SHEET ISOLATION: Dedicated Tennis Google Sheet ID is not configured yet "
            "(all NBA/NHL sheets such as NBA-PLAYERS-GEOMANTIC-INPUT and NBA-FUSION-CALCULATION "
            "are 100% isolated and disabled)."
        )
    return sid
