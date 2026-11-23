"""Shared Google Sheets client for TENNIS-* apps with strict NBA/NHL Sheet Isolation."""
import hashlib
import json
import os
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from _lib.tennis_config import (
    FORBIDDEN_SHEET_NAME_TOKENS,
    TENNIS_SHEETS_WRITE_ENABLED,
    assert_isolated_tennis_sheet,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# SHA-256 hashes of live NBA/NHL Google Spreadsheet IDs so we can block them
# at runtime without storing raw NBA Spreadsheet IDs in the Tennis repositories!
_FORBIDDEN_SHEET_ID_SHA256 = {
    "7fb4c9e18b7c35a50a72b3159f33220bd816dc796931793fe69fb7a4d8ce4b17",
    "558ed1e130673457b43639a0eab521997af4c32b7693e04eaac078e97e3c8462",
    "684fc97d1fb3d0fa4c7bf8fbc98f05513d67e834c028b25b6b651a402491bd35",
    "845085885f2f8c7753afa67196f5b2f890e24beeed72c72f029c273d57c0809e",
    "bdd6796030b2f542e183b9e2b6fef1459dba2340c721bb74598f0a673691b5c0",
    "9dcaad6a7b316ac7a942ac1c1518c496f215cfee7e7f6678ea7d9c2250f0904a",
    "a752e09aa78b75f3f3f2592cb54d3418457cdeba4c7b82fbe6f0791d868bc87d",
    "74b570d2019735765e530a9460f05e1c9cdcba908aa500a22fe5778baeb8a7c4",
    "93f9ac0be60dc19768c8960af82caabf656f1a33dd183675ac64b0c2a6774834",
    "d4958caab4b13885c20f69da7cbb8c9584120c78cc2264effb9e86fe9f683943",
    "3879953b981f5ccc4c5f80b4f212e42d66c604a35ccad8b49d4da777e4d605e8",
    "98b8710e3766f068685fbe33acda7162b01cfa51c1f1420df5ce1a93258b0f01",
    "9209874dc0e43854315ee3e32755f4782220e5e483527a436bfa653c7a8a94fc",
    "6cd11ebcf623e9805b1d2f0a8cccb4a30626e5981615daf12aa0723e04d0cd1b",
    "a0cfad3247028274a19984cdd19e32db78e02b727f8d16d3fe0a6ec4b758380f",
}


def _load_service_account_info() -> dict[str, Any]:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON secret is not set in this project."
        )
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON: {e}."
        ) from e


_client: gspread.Client | None = None


def get_client() -> gspread.Client:
    global _client
    if _client is None:
        info = _load_service_account_info()
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        _client = gspread.authorize(creds)
    return _client


def open_sheet(spreadsheet_id: str) -> gspread.Spreadsheet:
    if not TENNIS_SHEETS_WRITE_ENABLED:
        raise RuntimeError(
            "TENNIS SHEET ISOLATION: Google Sheets auto-sync/write is disabled "
            "(TENNIS_SHEETS_WRITE_ENABLED=0). Live NBA & NHL sheets are 100% untouched."
        )
    sid = assert_isolated_tennis_sheet(spreadsheet_id)
    sid_hash = hashlib.sha256(sid.encode("utf-8")).hexdigest()
    if sid_hash in _FORBIDDEN_SHEET_ID_SHA256:
        raise RuntimeError(
            "TENNIS SHEET ISOLATION VIOLATION: Attempted access to a live NBA/NHL Google Sheet ID is strictly blocked."
        )
    ss = get_client().open_by_key(sid)
    title_upper = (ss.title or "").upper()
    if any(tok in title_upper for tok in FORBIDDEN_SHEET_NAME_TOKENS):
        raise RuntimeError(
            f"TENNIS SHEET ISOLATION VIOLATION: Spreadsheet '{ss.title}' belongs to NBA/NHL and is blocked."
        )
    return ss
