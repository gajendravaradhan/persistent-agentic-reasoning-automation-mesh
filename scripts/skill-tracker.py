#!/usr/bin/env python3
"""
PARAM Skill Tracker — Phase 2.4.1

Modes:
  --mode=scan-log [--lines=N]          Incremental scan of agent.log for skill events
  --mode=record-invocation --skill=X   Record a direct invocation for skill X
  --mode=record-error --skill=X        Record a direct error for skill X
  --mode=report                         Output all metrics as JSON
  --mode=stale-report [--days=N]        Skills unused for N days (default 60)

State file: /opt/data/state/skill-metrics.json
Log file:   /opt/data/logs/agent.log
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths (container-relative; override via env for local dev) ──────────────
LOG_FILE   = os.environ.get("PARAM_LOG",    "/opt/data/logs/agent.log")
STATE_FILE = os.environ.get("PARAM_STATE",  "/opt/data/state/skill-metrics.json")
SKILLS_DIR = os.environ.get("PARAM_SKILLS", "/opt/data/skills")

SCHEMA_VERSION = 1

_SKILL_NAME = r"([a-zA-Z0-9][a-zA-Z0-9_-]{1,63})"

INVOCATION_PATTERNS = [
    # skill_view name=git-master  or  skill_view {"name": "git-master"}
    re.compile(
        r"skill_view.*?(?:name\s*=\s*['\"]?|\"name\"\s*:\s*['\"])" + _SKILL_NAME,
        re.IGNORECASE,
    ),
    # Skill loaded: git-master (2048 chars)
    re.compile(r"[Ss]kill\s+loaded[:\s]+" + _SKILL_NAME, re.IGNORECASE),
    # Loading skill: git-master
    re.compile(r"[Ll]oading\s+skill[:\s]+" + _SKILL_NAME, re.IGNORECASE),
    # skill_manage action=create name=new-skill
    re.compile(
        r"skill_manage.*?(?:action\s*=\s*(?:create|patch)).*?(?:name\s*=\s*['\"]?)" + _SKILL_NAME,
        re.IGNORECASE,
    ),
]

ERROR_PATTERNS = [
    # Skill 'bad-skill' not found
    re.compile(r"[Ss]kill\s+['\"]?" + _SKILL_NAME + r"['\"]?\s+not\s+found", re.IGNORECASE),
    # ERROR ... skill_view ... bad-skill ... error/failed
    re.compile(
        r"skill_view.*?" + _SKILL_NAME + r".*?(?:error|failed|exception)",
        re.IGNORECASE,
    ),
    # skill_manage error for skill-name
    re.compile(r"skill_manage.*?(?:error|failed).*?" + _SKILL_NAME, re.IGNORECASE),
]

LOG_TS_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\d+\s+(INFO|WARNING|ERROR|DEBUG|CRITICAL)"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_state() -> dict:
    p = Path(STATE_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "_meta": {
            "schema_version": SCHEMA_VERSION,
            "last_updated": _now_iso(),
            "log_position": 0,
        },
        "skills": {},
    }


def _save_state(state: dict) -> None:
    p = Path(STATE_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["_meta"]["last_updated"] = _now_iso()
    p.write_text(json.dumps(state, indent=2))


def _ensure_skill(state: dict, name: str) -> None:
    if name not in state["skills"]:
        state["skills"][name] = {
            "invocations": 0,
            "errors": 0,
            "last_used": None,
            "first_seen": _now_iso(),
            "success_rate": 1.0,
        }


def _update_success_rate(entry: dict) -> None:
    total = entry["invocations"] + entry["errors"]
    entry["success_rate"] = round(entry["invocations"] / total, 4) if total > 0 else 1.0


def _extract_skill_from_line(line: str, patterns: list) -> str | None:
    for pat in patterns:
        m = pat.search(line)
        if m:
            name = m.group(1)
            # Filter out obvious false positives (single chars, pure numbers)
            if len(name) >= 2 and not name.isdigit():
                return name
    return None


def _parse_line_timestamp(line: str) -> datetime | None:
    m = LOG_TS_RE.match(line)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def scan_log(state: dict, max_lines: int | None = None) -> dict:
    log_path = Path(LOG_FILE)
    if not log_path.exists():
        return {"invocations_added": 0, "errors_added": 0, "lines_scanned": 0,
                "warning": f"Log file not found: {LOG_FILE}"}

    start_pos = state["_meta"].get("log_position", 0)
    inv_added = 0
    err_added = 0
    lines_scanned = 0

    with open(log_path, "r", errors="replace") as fh:
        fh.seek(start_pos)
        for line in fh:
            if max_lines is not None and lines_scanned >= max_lines:
                break
            lines_scanned += 1
            line = line.rstrip()

            m = LOG_TS_RE.match(line)
            level = m.group(2) if m else ""
            ts = _parse_line_timestamp(line)
            ts_iso = ts.isoformat(timespec="seconds") if ts else _now_iso()

            if level in ("INFO", "DEBUG") and "skill" in line.lower():
                skill = _extract_skill_from_line(line, INVOCATION_PATTERNS)
                if skill:
                    _ensure_skill(state, skill)
                    state["skills"][skill]["invocations"] += 1
                    state["skills"][skill]["last_used"] = ts_iso
                    _update_success_rate(state["skills"][skill])
                    inv_added += 1

            elif level == "ERROR" and "skill" in line.lower():
                skill = _extract_skill_from_line(line, ERROR_PATTERNS)
                if skill:
                    _ensure_skill(state, skill)
                    state["skills"][skill]["errors"] += 1
                    _update_success_rate(state["skills"][skill])
                    err_added += 1

        state["_meta"]["log_position"] = fh.tell()

    return {
        "invocations_added": inv_added,
        "errors_added": err_added,
        "lines_scanned": lines_scanned,
    }


def mode_scan_log(args) -> None:
    state = _load_state()
    result = scan_log(state, max_lines=args.lines)
    _save_state(state)
    print(json.dumps(result))


def mode_record_invocation(args) -> None:
    if not args.skill:
        print(json.dumps({"error": "--skill is required for record-invocation"}))
        sys.exit(1)
    state = _load_state()
    _ensure_skill(state, args.skill)
    state["skills"][args.skill]["invocations"] += 1
    state["skills"][args.skill]["last_used"] = _now_iso()
    _update_success_rate(state["skills"][args.skill])
    _save_state(state)
    print(json.dumps({"recorded": "invocation", "skill": args.skill,
                      "total": state["skills"][args.skill]["invocations"]}))


def mode_record_error(args) -> None:
    if not args.skill:
        print(json.dumps({"error": "--skill is required for record-error"}))
        sys.exit(1)
    state = _load_state()
    _ensure_skill(state, args.skill)
    state["skills"][args.skill]["errors"] += 1
    _update_success_rate(state["skills"][args.skill])
    _save_state(state)
    print(json.dumps({"recorded": "error", "skill": args.skill,
                      "total_errors": state["skills"][args.skill]["errors"]}))


def mode_report(args) -> None:
    state = _load_state()
    skills_dir = Path(SKILLS_DIR)
    if skills_dir.exists():
        for skill_file in skills_dir.glob("*/SKILL.md"):
            skill_name = skill_file.parent.name
            if skill_name not in state["skills"]:
                _ensure_skill(state, skill_name)
        for skill_file in skills_dir.glob("*.md"):
            skill_name = skill_file.stem
            if skill_name not in state["skills"]:
                _ensure_skill(state, skill_name)
    print(json.dumps(state, indent=2))


def mode_stale_report(args) -> None:
    state = _load_state()
    threshold_days = args.days
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)

    stale = []
    active = []

    for name, entry in state["skills"].items():
        last_used = entry.get("last_used")
        if last_used is None:
            first_seen_str = entry.get("first_seen", _now_iso())
            try:
                first_seen = datetime.fromisoformat(first_seen_str)
                if first_seen < cutoff:
                    stale.append((name, entry, "never used"))
            except ValueError:
                stale.append((name, entry, "never used"))
        else:
            try:
                last_dt = datetime.fromisoformat(last_used)
                if last_dt < cutoff:
                    days_ago = (datetime.now(timezone.utc) - last_dt).days
                    stale.append((name, entry, f"last used {days_ago}d ago"))
                else:
                    active.append((name, entry))
            except ValueError:
                stale.append((name, entry, "unknown last_used"))

    # Human-readable output
    lines = [
        f"📊 Skill Stale Report — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f"Threshold: {args.days} days",
        "",
    ]

    if stale:
        lines.append(f"⚠️  Stale skills ({len(stale)}):")
        for name, entry, reason in sorted(stale, key=lambda x: x[0]):
            inv = entry.get("invocations", 0)
            lines.append(f"  • {name}  [{reason}]  invocations={inv}")
    else:
        lines.append("✅ No stale skills found.")

    lines.append("")
    if active:
        top5 = sorted(active, key=lambda x: x[1].get("invocations", 0), reverse=True)[:5]
        lines.append("🔥 Most active (top 5):")
        for name, entry in top5:
            inv = entry.get("invocations", 0)
            last = entry.get("last_used", "?")[:10]
            lines.append(f"  • {name}  invocations={inv}  last={last}")

    lines.append("")
    lines.append(f"Total tracked: {len(state['skills'])}  |  Stale: {len(stale)}  |  Active: {len(active)}")

    print("\n".join(lines))


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PARAM Skill Tracker")
    parser.add_argument(
        "--mode",
        choices=["scan-log", "record-invocation", "record-error", "report", "stale-report"],
        required=True,
    )
    parser.add_argument("--skill", help="Skill name (for record-* modes)")
    parser.add_argument("--lines", type=int, default=None,
                        help="Max lines to scan in scan-log mode")
    parser.add_argument("--days", type=int, default=60,
                        help="Stale threshold in days (default 60)")
    args = parser.parse_args()

    dispatch = {
        "scan-log":           mode_scan_log,
        "record-invocation":  mode_record_invocation,
        "record-error":       mode_record_error,
        "report":             mode_report,
        "stale-report":       mode_stale_report,
    }
    dispatch[args.mode](args)


if __name__ == "__main__":
    main()
