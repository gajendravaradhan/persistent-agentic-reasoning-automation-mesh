"""Skill tracker hook — records skill invocations for the self-evolving skills pipeline.

On agent:end: parses the agent response for skill names that were used during
the session, then calls skill-tracker.py --mode=record-invocation for each.

Skill names are detected by:
1. Scanning the response text for skill_load/skill_view/skills_list tool calls
2. Matching skill names from the installed skills directory

This enables the self-evolving skills system to track which skills are actually
used, surfacing stale skills (>60 days unused) and feeding the novel-workflow
detector with usage data.
"""

import asyncio
import json
import os
import re
import subprocess
from pathlib import Path

SCRIPT_PATH = Path(os.environ.get("HERMES_DATA", "/opt/data")) / "scripts" / "skill-tracker.py"
SKILLS_DIR = Path(os.environ.get("HERMES_DATA", "/opt/data")) / "skills"


def _discover_installed_skills() -> set:
    """Return set of installed skill directory names."""
    skills = set()
    if SKILLS_DIR.exists():
        for entry in SKILLS_DIR.rglob("SKILL.md"):
            skills.add(entry.parent.name)
    return skills


def _extract_skill_names_from_response(response: str) -> set:
    """Extract skill names referenced in the agent response.

    Looks for patterns like:
    - skill_load(name="X")
    - skill_view(name="X")
    - "skill": "X"
    - skill_manage(action='create', name='X')
    """
    names = set()

    # Match skill_load(name="X") or skill_view(name="X") patterns
    skill_tool_re = re.compile(
        r'skill_(?:load|view|manage)\s*\(\s*[^)]*?name\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    for match in skill_tool_re.finditer(response):
        names.add(match.group(1))

    # Match "skill": "X" or "skill_name": "X" patterns
    skill_json_re = re.compile(r'"skill(?:_name)?"\s*:\s*"([^"]+)"', re.IGNORECASE)
    for match in skill_json_re.finditer(response):
        names.add(match.group(1))

    # Match skill_load or skill_view in tool call results
    tool_call_re = re.compile(r'"name"\s*:\s*"(skill_load|skill_view|skills_list)"', re.IGNORECASE)
    if tool_call_re.search(response):
        # The response contains skill tool calls — extract the skill name argument
        arg_re = re.compile(r'"(?:skill|name)"\s*:\s*"([^"]+)"', re.IGNORECASE)
        for match in arg_re.finditer(response):
            if match.group(1) not in ("skill_load", "skill_view", "skills_list"):
                names.add(match.group(1))

    return names


def _extract_skill_names_from_message(message: str) -> set:
    """Extract skill names that the user explicitly requested."""
    installed = _discover_installed_skills()
    names = set()
    msg_lower = message.lower()
    for skill_name in installed:
        if skill_name.lower() in msg_lower:
            names.add(skill_name)
    return names


async def handle(event_type: str, context: dict) -> None:
    """Handle hook events for skill tracking.

    Args:
        event_type: The hook event (agent:start or agent:end)
        context: Event context with platform, user_id, message, response, etc.
    """
    if not SCRIPT_PATH.exists():
        return

    if event_type == "agent:end":
        response = context.get("response", "")
        message = context.get("message", "")

        # Extract skill names from both the user message and agent response
        from_response = _extract_skill_names_from_response(response)
        from_message = _extract_skill_names_from_message(message)
        skill_names = from_response | from_message

        if not skill_names:
            return

        # Record each skill invocation
        for skill_name in skill_names:
            try:
                result = subprocess.run(
                    ["python3", str(SCRIPT_PATH), "--mode=record-invocation", skill_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    print(f"[skill-tracker-hook] Failed to record {skill_name}: {result.stderr.strip()}", flush=True)
                else:
                    print(f"[skill-tracker-hook] Recorded invocation: {skill_name}", flush=True)
            except subprocess.TimeoutExpired:
                print(f"[skill-tracker-hook] Timeout recording {skill_name}", flush=True)
            except Exception as e:
                print(f"[skill-tracker-hook] Error recording {skill_name}: {e}", flush=True)
