"""Helpers for step scripts to emit structured progress/result lines.

The orchestrator parses the LAST line that starts with `__RESULT__ ` as JSON
and treats every other stdout/stderr line as log output.
"""
import json
import sys
import time
from typing import Any


def log(message: str) -> None:
    print(message, flush=True)


def emit_result(
    *,
    ok: bool,
    rows_written: int | None = None,
    message: str | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "ok": ok,
        "rowsWritten": rows_written,
        "message": message,
        "error": error,
        "ts": time.time(),
    }
    if extra:
        payload.update(extra)
    print("__RESULT__ " + json.dumps(payload), flush=True)


def fail_not_implemented(step_name: str, source_project: str) -> None:
    msg = (
        f"{step_name} is not implemented yet. "
        f"Paste the source code from the '{source_project}' Replit project "
        "into the chat so the exact logic can be ported."
    )
    log("ERROR: " + msg)
    emit_result(ok=False, message=msg, error="NOT_IMPLEMENTED")
    sys.exit(2)
