"""Step 5 - BTC ATR Google Sheets agent.

Updates today's UTC row in the summary sheet with:
  K = today open (Coinbase BTC-USD daily candle)
  L = ATR(14) computed from previous 14 daily candles
  I = +ATR / -ATR / 0 based on signal in column D (UP / DOWN / NEUTRAL)
  J = formula =K{row}+I{row}

Run with --dry-run to print planned writes without mutating the sheet.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Allow running as a script: ensure parent dir is on sys.path so `_lib` imports.
sys.path.insert(0, str(Path(__file__).parent))

from _lib.runner import emit_result, log  # noqa: E402

SHEET_ID = os.environ.get("TENNIS_AUX_SHEET_ID", "")
WORKSHEET_NAME = os.environ.get("STEP5_WORKSHEET_NAME", "Sheet1")
COINBASE_PRODUCT_ID = os.environ.get("COINBASE_PRODUCT_ID", "BTC-USD")
COINBASE_BASE_URL = os.environ.get(
    "COINBASE_BASE_URL", "https://api.exchange.coinbase.com/"
)
CANDLE_LOOKBACK_DAYS = int(os.environ.get("CANDLE_LOOKBACK_DAYS", "45"))
ATR_PERIOD = int(os.environ.get("ATR_PERIOD", "14"))

# Column letters (1-indexed positions for value list access)
COL_DATE = 2  # B
COL_SIGNAL = 4  # D
COL_PRICE_CHANGE = 9  # I
COL_TARGET_PRICE = 10  # J
COL_OPEN_PRICE = 11  # K
COL_ATR = 12  # L


def fetch_candles() -> list[list[float]]:
    """Return Coinbase daily candles for the past CANDLE_LOOKBACK_DAYS days.

    Coinbase returns: [time, low, high, open, close, volume], newest first.
    """
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=CANDLE_LOOKBACK_DAYS)
    url = f"{COINBASE_BASE_URL.rstrip('/')}/products/{COINBASE_PRODUCT_ID}/candles"
    params = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "granularity": 86400,
    }
    log(f"Fetching candles: {url} params={params}")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected Coinbase response: {data!r}")
    return data


def compute_atr(candles_oldest_first: list[list[float]], period: int) -> float:
    """ATR over the previous `period` completed candles (excluding today).

    Each candle: [time, low, high, open, close, vol].
    The caller passes the full candle list; today's candle is dropped here so
    ATR reflects historical volatility prior to today's open.
    """
    if len(candles_oldest_first) < period + 2:
        raise RuntimeError(
            f"Need at least {period + 2} candles to compute ATR{period} on previous candles, "
            f"got {len(candles_oldest_first)}"
        )
    historical = candles_oldest_first[:-1]
    trs: list[float] = []
    prev_close = historical[0][4]
    for c in historical[1:]:
        _, low, high, _open, close, _vol = c
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = close
    window = trs[-period:]
    return sum(window) / period


def find_today_row(values: list[list[str]], today_iso: str) -> int | None:
    """Find 1-indexed row in the sheet whose B column matches today's date.

    Accepts YYYY-MM-DD, M/D/YYYY, MM/DD/YYYY.
    """
    target = dt.date.fromisoformat(today_iso)
    for idx, row in enumerate(values, start=1):
        if len(row) < COL_DATE:
            continue
        cell = (row[COL_DATE - 1] or "").strip()
        if not cell:
            continue
        parsed = _parse_date(cell)
        if parsed == target:
            return idx
    return None


def _parse_date(s: str) -> dt.date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%-m/%-d/%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Try Sheets serial number
    try:
        n = float(s)
        epoch = dt.date(1899, 12, 30)
        return epoch + dt.timedelta(days=int(n))
    except ValueError:
        return None


def col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def run(dry_run: bool = False) -> None:
    candles_newest_first = fetch_candles()
    if not candles_newest_first:
        raise RuntimeError("Coinbase returned no candles")

    candles_oldest_first = sorted(candles_newest_first, key=lambda c: c[0])
    today_candle = candles_oldest_first[-1]
    today_open = float(today_candle[3])
    atr = compute_atr(candles_oldest_first, ATR_PERIOD)
    today_iso = dt.datetime.fromtimestamp(
        today_candle[0], tz=dt.timezone.utc
    ).date().isoformat()

    log(f"Today UTC date: {today_iso} open={today_open} ATR{ATR_PERIOD}={atr:.4f}")

    if dry_run:
        log("--- DRY RUN: planned writes ---")
        log(f"  K{{row}} = {today_open}")
        log(f"  L{{row}} = {atr:.4f}")
        log("  I{row} = +ATR/-ATR/0 depending on signal in D")
        log("  J{row} = =K{row}+I{row}")
        emit_result(
            ok=True,
            rows_written=0,
            message=f"Dry run OK. open={today_open} atr={atr:.4f}",
        )
        return

    # Real write path: import only when needed so dry-run works without the secret.
    from _lib.sheets import open_sheet  # noqa: WPS433

    sh = open_sheet(SHEET_ID)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except Exception as e:  # gspread.WorksheetNotFound, etc.
        raise RuntimeError(
            f"Worksheet '{WORKSHEET_NAME}' not found in sheet {SHEET_ID}: {e}"
        ) from e

    values = ws.get_all_values()
    row = find_today_row(values, today_iso)
    if row is None:
        raise RuntimeError(
            f"Could not find a row in column B for today's UTC date {today_iso}. "
            "Make sure the sheet has a row for today."
        )

    signal = ""
    if len(values) >= row and len(values[row - 1]) >= COL_SIGNAL:
        signal = (values[row - 1][COL_SIGNAL - 1] or "").strip().upper()

    if signal == "UP":
        price_change: float = atr
    elif signal == "DOWN":
        price_change = -atr
    else:
        price_change = 0.0

    log(f"Row={row} signal={signal!r} price_change={price_change:.4f}")

    # Atomic single batch update for K, L, I, J (J as USER_ENTERED formula).
    formula = f"=K{row}+I{row}"
    body = [
        {"range": f"{col_letter(COL_OPEN_PRICE)}{row}", "values": [[today_open]]},
        {"range": f"{col_letter(COL_ATR)}{row}", "values": [[round(atr, 4)]]},
        {"range": f"{col_letter(COL_PRICE_CHANGE)}{row}", "values": [[round(price_change, 4)]]},
        {"range": f"{col_letter(COL_TARGET_PRICE)}{row}", "values": [[formula]]},
    ]
    ws.batch_update(body, value_input_option="USER_ENTERED")

    emit_result(
        ok=True,
        rows_written=1,
        message=f"Updated row {row} (date {today_iso}, signal {signal or 'NONE'})",
        extra={"row": row, "signal": signal, "open": today_open, "atr": atr},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    started = time.time()
    try:
        run(dry_run=args.dry_run)
    except Exception as e:
        log(f"ERROR: {e}")
        emit_result(ok=False, error=str(e), message="Step 5 failed")
        sys.exit(1)
    log(f"Completed in {time.time() - started:.2f}s")


if __name__ == "__main__":
    main()
