#!/usr/bin/env python3
"""skill-failure-tracker.py — PARAM Phase 2 failure pattern detection.

Modes:
  --mode=scan       Scan logs for new error patterns, update state, print summary
  --mode=report     Print current failure patterns as JSON (no scanning)

Detects the same normalized error 3+ times across sessions.
Maps errors to active skill context (skill references within ±20 log lines).
Proposes pitfall text for skill patching.

State: /opt/data/state/failure-patterns.json
"""

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

FAILURE_THRESHOLD = 3
CONTEXT_WINDOW = 20

BASE = Path(os.environ.get("HERMES_DATA", "/opt/data"))
STATE_FILE = BASE / "state" / "failure-patterns.json"
LOG_FILE = BASE / "logs" / "agent.log"
ERROR_LOG = BASE / "logs" / "errors.log"

if not BASE.exists():
    BASE = Path.home() / ".hermes"
    STATE_FILE = BASE / "state" / "failure-patterns.json"
    LOG_FILE = BASE / "logs" / "agent.log"
    ERROR_LOG = BASE / "logs" / "errors.log"

ERROR_LINE_RE = re.compile(r'\b(ERROR|FATAL|CRITICAL)\b', re.IGNORECASE)
SKILL_REF_RE = re.compile(
    r'(?:skill_view|skill_manage|Loaded skill|skill name)[^\n]*?["\']([a-z][a-z0-9_-]{2,40})["\']',
    re.IGNORECASE,
)

_STRIP_PATTERNS = [
    re.compile(r'\b[0-9a-f]{8,}\b'),
    re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*'),
    re.compile(r'\b\d+\.\d+\.\d+\.\d+\b'),
    re.compile(r'/[^\s:,\])"]+'),
    re.compile(r'\[\d+\]'),
    re.compile(r'\s+', re.MULTILINE),
]


def _normalize_error(msg: str) -> str:
    text = msg
    for pat in _STRIP_PATTERNS:
        text = pat.sub(" ", text)
    return text.strip().lower()[:200]


def _fingerprint(normalized: str) -> str:
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"patterns": {}, "updated_at": None}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _read_log_lines() -> list:
    lines: list = []
    for log_path in [LOG_FILE, ERROR_LOG]:
        if log_path.exists():
            try:
                lines.extend(log_path.read_text(errors="ignore").splitlines())
            except Exception:
                pass
    return lines


def _find_skill_context(lines: list, error_idx: int) -> str | None:
    start = max(0, error_idx - CONTEXT_WINDOW)
    end = min(len(lines), error_idx + CONTEXT_WINDOW)
    context_block = "\n".join(lines[start:end])
    m = SKILL_REF_RE.search(context_block)
    return m.group(1) if m else None


def _generate_pitfall(error_msg: str, skill: str | None) -> str:
    short = error_msg[:120].strip()
    skill_part = f" when using the '{skill}' skill" if skill else ""
    return (
        f"**Pitfall detected{skill_part}:** The following error pattern has occurred "
        f"3+ times: `{short}...`. "
        "Ensure prerequisites are met and inputs are validated before proceeding."
    )


def scan() -> None:
    state = _load_state()
    lines = _read_log_lines()

    raw_errors: dict = {}
    for idx, line in enumerate(lines):
        if not ERROR_LINE_RE.search(line):
            continue
        normalized = _normalize_error(line)
        if len(normalized) < 10:
            continue
        fp = _fingerprint(normalized)
        skill_ctx = _find_skill_context(lines, idx)
        if fp not in raw_errors:
            raw_errors[fp] = {
                "normalized_msg": normalized,
                "raw_sample": line[:200],
                "count": 0,
                "skill_context": skill_ctx,
            }
        raw_errors[fp]["count"] += 1
        if skill_ctx and not raw_errors[fp]["skill_context"]:
            raw_errors[fp]["skill_context"] = skill_ctx

    patterns = state.get("patterns", {})
    for fp, info in raw_errors.items():
        if fp not in patterns:
            patterns[fp] = {
                "fingerprint": fp,
                "normalized_msg": info["normalized_msg"],
                "raw_sample": info["raw_sample"],
                "count": info["count"],
                "skill_context": info["skill_context"],
                "proposed_pitfall": _generate_pitfall(info["normalized_msg"], info["skill_context"]),
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "resolved": False,
            }
        else:
            patterns[fp]["count"] = max(patterns[fp]["count"], info["count"])
            patterns[fp]["last_seen"] = datetime.now(timezone.utc).isoformat()
            if info["skill_context"] and not patterns[fp].get("skill_context"):
                patterns[fp]["skill_context"] = info["skill_context"]

    state["patterns"] = patterns
    _save_state(state)

    active = [p for p in patterns.values() if p["count"] >= FAILURE_THRESHOLD and not p.get("resolved")]
    print(json.dumps({
        "active_patterns": len(active),
        "total_patterns": len(patterns),
        "threshold": FAILURE_THRESHOLD,
        "patterns": active,
        "scanned_lines": len(lines),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


def report() -> None:
    state = _load_state()
    patterns = state.get("patterns", {})
    active = [p for p in patterns.values() if p["count"] >= FAILURE_THRESHOLD and not p.get("resolved")]
    print(json.dumps({
        "active_patterns": len(active),
        "total_patterns": len(patterns),
        "threshold": FAILURE_THRESHOLD,
        "patterns": active,
        "updated_at": state.get("updated_at"),
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="PARAM skill failure pattern tracker")
    parser.add_argument("--mode", required=True, choices=["scan", "report"])
    args = parser.parse_args()
    if args.mode == "scan":
        scan()
    else:
        report()


if __name__ == "__main__":
    main()
