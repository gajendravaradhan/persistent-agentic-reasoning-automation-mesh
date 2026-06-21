#!/usr/bin/env python3
"""skill-tracker.py — PARAM Phase 2 skill lifecycle metrics.

Modes:
  --mode=record-invocation  SKILL_NAME  Record a skill was used
  --mode=record-error       SKILL_NAME  Record an error during skill use
  --mode=report             Print JSON summary of all skill metrics
  --mode=stale-report       Print skills unused for >60 days as JSON

State: /opt/data/state/skill-metrics.json
Log:   /opt/data/logs/agent.log
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STALE_DAYS = 60
BASE = Path(os.environ.get("HERMES_DATA", "/opt/data"))
STATE_FILE = BASE / "state" / "skill-metrics.json"
SKILLS_DIR = BASE / "skills"

if not BASE.exists():
    BASE = Path.home() / ".hermes"
    STATE_FILE = BASE / "state" / "skill-metrics.json"
    SKILLS_DIR = BASE / "skills"


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"skills": {}, "updated_at": None}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _discover_installed() -> set[str]:
    known: set[str] = set()
    if SKILLS_DIR.exists():
        for entry in SKILLS_DIR.rglob("SKILL.md"):
            known.add(entry.parent.name)
    return known


def _ensure_skill(state: dict, name: str) -> None:
    if name not in state["skills"]:
        state["skills"][name] = {
            "invocations": 0,
            "errors": 0,
            "last_used": None,
            "first_seen": datetime.now(timezone.utc).isoformat(),
        }


def record_invocation(name: str) -> None:
    state = _load_state()
    _ensure_skill(state, name)
    state["skills"][name]["invocations"] += 1
    state["skills"][name]["last_used"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)
    print(json.dumps({"ok": True, "skill": name, "action": "invocation_recorded"}))


def record_error(name: str) -> None:
    state = _load_state()
    _ensure_skill(state, name)
    state["skills"][name]["errors"] += 1
    _save_state(state)
    print(json.dumps({"ok": True, "skill": name, "action": "error_recorded"}))


def report() -> None:
    state = _load_state()
    installed = _discover_installed()
    for name in installed:
        _ensure_skill(state, name)
    out = {
        "total_skills": len(installed),
        "tracked_skills": len(state["skills"]),
        "skills": state["skills"],
        "updated_at": state.get("updated_at"),
    }
    print(json.dumps(out, indent=2))


def stale_report() -> None:
    state = _load_state()
    installed = _discover_installed()
    now = datetime.now(timezone.utc)
    stale = []
    for name in installed:
        entry = state["skills"].get(name, {})
        last_used_raw = entry.get("last_used")
        if last_used_raw is None:
            days_since = STALE_DAYS + 1
        else:
            last_used = datetime.fromisoformat(last_used_raw)
            if last_used.tzinfo is None:
                last_used = last_used.replace(tzinfo=timezone.utc)
            days_since = (now - last_used).days
        if days_since > STALE_DAYS:
            stale.append({
                "skill": name,
                "days_since_use": days_since,
                "invocations": entry.get("invocations", 0),
                "errors": entry.get("errors", 0),
                "last_used": last_used_raw,
            })
    stale.sort(key=lambda x: x["days_since_use"], reverse=True)
    print(json.dumps({
        "stale_count": len(stale),
        "threshold_days": STALE_DAYS,
        "stale_skills": stale,
        "generated_at": now.isoformat(),
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="PARAM skill lifecycle tracker")
    parser.add_argument("--mode", required=True,
                        choices=["record-invocation", "record-error", "report", "stale-report"])
    parser.add_argument("skill_name", nargs="?", help="Skill name (required for record-* modes)")
    args = parser.parse_args()

    if args.mode in ("record-invocation", "record-error") and not args.skill_name:
        print(json.dumps({"error": f"--mode={args.mode} requires a skill_name argument"}))
        sys.exit(1)

    if args.mode == "record-invocation":
        record_invocation(args.skill_name)
    elif args.mode == "record-error":
        record_error(args.skill_name)
    elif args.mode == "report":
        report()
    elif args.mode == "stale-report":
        stale_report()


if __name__ == "__main__":
    main()
