#!/usr/bin/env python3
"""skill-novel-detector.py — PARAM Phase 2 novel workflow detection.

Scans recent session logs for multi-step workflows (5+ distinct tool calls)
that succeed with no close match in existing skills. Outputs candidate
skill proposals as JSON.

Output schema:
  {
    "candidates": [{title, trigger, steps, description, tool_sequence,
                    novelty_score, overlapping_skills}],
    "analyzed_at": "ISO timestamp",
    "sessions_scanned": N,
    "candidates_found": N
  }

State: /opt/data/state/novel-patterns.json  (dedup across runs)
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MIN_TOOL_CALLS = 5
NOVELTY_THRESHOLD = 0.6

BASE = Path(os.environ.get("HERMES_DATA", "/opt/data"))
STATE_FILE = BASE / "state" / "novel-patterns.json"
SESSIONS_DIR = BASE / "sessions"
SKILLS_DIR = BASE / "skills"

if not BASE.exists():
    BASE = Path.home() / ".hermes"
    STATE_FILE = BASE / "state" / "novel-patterns.json"
    SESSIONS_DIR = BASE / "sessions"
    SKILLS_DIR = BASE / "skills"

TOOL_CALL_RE = re.compile(
    r'"name"\s*:\s*"([a-z_][a-z0-9_]{2,40})"',
    re.IGNORECASE,
)

SKILL_KEYWORD_RE = re.compile(r'\b([a-z][a-z0-9_-]{3,30})\b', re.IGNORECASE)


def _load_dedup() -> set:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            return set(data.get("seen_fingerprints", []))
        except Exception:
            pass
    return set()


def _save_dedup(seen: set) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if STATE_FILE.exists():
        try:
            existing = json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    existing["seen_fingerprints"] = list(seen)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(existing, indent=2))


def _load_skill_keywords() -> set:
    keywords: set = set()
    if not SKILLS_DIR.exists():
        return keywords
    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        try:
            text = skill_md.read_text(errors="ignore")
            for m in SKILL_KEYWORD_RE.finditer(text):
                w = m.group(1).lower()
                if len(w) > 4:
                    keywords.add(w)
        except Exception:
            pass
    return keywords


def _session_files(limit: int = 100) -> list:
    if not SESSIONS_DIR.exists():
        return []
    files = sorted(SESSIONS_DIR.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def _extract_tools(session_path: Path) -> list:
    try:
        data = json.loads(session_path.read_text(errors="ignore"))
    except Exception:
        return []
    tools: list = []
    messages = data if isinstance(data, list) else data.get("messages", [])
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls", []) or []:
                name = (tc.get("function") or {}).get("name") or tc.get("name")
                if name and isinstance(name, str):
                    tools.append(name)
    if not tools:
        raw = session_path.read_text(errors="ignore")
        tools = TOOL_CALL_RE.findall(raw)
    return tools


def _novelty_score(tool_sequence: list, skill_keywords: set) -> float:
    if not tool_sequence:
        return 0.0
    tool_words = {t.lower().replace("hermes__", "").replace("_", " ").split()[0]
                  for t in tool_sequence}
    overlap = len(tool_words & skill_keywords)
    raw_score = 1.0 - min(overlap / max(len(tool_words), 1), 1.0)
    return round(raw_score, 3)


def _fingerprint(tools: list) -> str:
    unique_sorted = sorted(set(tools))
    return ",".join(unique_sorted)


def _build_proposal(tools: list, session_id: str, novelty: float) -> dict:
    unique_tools = list(dict.fromkeys(tools))
    domain_hints = {t for t in unique_tools if any(k in t for k in
                    ["terminal", "search", "browser", "file", "git", "deploy", "docker"])}
    if "terminal" in str(unique_tools):
        trigger = "When user asks to run a complex multi-step terminal workflow"
    elif "search" in str(unique_tools):
        trigger = "When user asks to research and synthesize information"
    elif "browser" in str(unique_tools):
        trigger = "When user asks to interact with a web application"
    else:
        trigger = f"When user asks to perform a workflow involving {', '.join(list(domain_hints)[:3]) or 'multiple tools'}"

    steps = [f"Step {i + 1}: Use {tool}" for i, tool in enumerate(unique_tools[:8])]

    return {
        "title": f"auto-detected-workflow-{session_id[-6:]}",
        "trigger": trigger,
        "steps": steps,
        "description": f"Multi-step workflow detected in session {session_id} using {len(unique_tools)} distinct tools.",
        "tool_sequence": unique_tools,
        "session_id": session_id,
        "novelty_score": novelty,
        "overlapping_skills": [],
    }


def main() -> None:
    skill_keywords = _load_skill_keywords()
    seen_fps = _load_dedup()

    session_files = _session_files(limit=200)
    candidates = []
    scanned = 0

    for sf in session_files:
        scanned += 1
        tools = _extract_tools(sf)
        unique_tools = list(dict.fromkeys(tools))
        if len(unique_tools) < MIN_TOOL_CALLS:
            continue
        fp = _fingerprint(tools)
        if fp in seen_fps:
            continue
        novelty = _novelty_score(unique_tools, skill_keywords)
        if novelty < NOVELTY_THRESHOLD:
            continue
        session_id = sf.stem
        candidates.append(_build_proposal(unique_tools, session_id, novelty))
        seen_fps.add(fp)

    _save_dedup(seen_fps)

    print(json.dumps({
        "candidates": candidates,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "sessions_scanned": scanned,
        "candidates_found": len(candidates),
    }, indent=2))


if __name__ == "__main__":
    main()
