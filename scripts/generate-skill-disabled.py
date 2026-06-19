#!/usr/bin/env python3
"""Generate per-agent skills.disabled lists from skill-whitelist.yaml.

Uses Hermes's existing skills.disabled mechanism as an inverse whitelist.
Each agent gets a config that disables ALL skills except the whitelisted ones.
"""
import yaml, os, sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WHITELIST_PATH = os.path.join(PROJECT_ROOT, "configs", "skill-whitelist.yaml")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "configs", "skills-disabled")

# All known Hermes skills
ALL_SKILLS = {
    "airtable", "apple-notes", "apple-reminders", "architecture-diagram",
    "arxiv", "ascii-art", "ascii-video", "baoyu-infographic", "blogwatcher",
    "claude-code", "claude-design", "codebase-inspection", "codex", "comfyui",
    "design-md", "dogfood", "excalidraw", "findmy", "gif-search",
    "github-auth", "github-code-review", "github-issues", "github-pr-workflow",
    "github-repo-management", "google-workspace", "heartmula", "hermes-agent",
    "hermes-agent-skill-authoring", "himalaya", "huggingface-hub", "humanizer",
    "imessage", "jupyter-live-kernel", "kanban-orchestrator", "kanban-worker",
    "llm-wiki", "macos-computer-use", "manim-video", "maps", "nano-pdf",
    "node-inspect-debugger", "notion", "obsidian", "ocr-and-documents",
    "opencode", "openhue", "p5js", "plan", "polymarket", "popular-web-designs",
    "powerpoint", "pretext", "python-debugpy", "requesting-code-review",
    "research-paper-writing", "simplify-code", "sketch", "songsee",
    "songwriting-and-ai-music", "spike", "systematic-debugging",
    "teams-meeting-pipeline", "test-driven-development", "touchdesigner-mcp",
    "xurl", "youtube-content", "yuanbao",
}

with open(WHITELIST_PATH) as f:
    raw = f.read()

# Parse the YAML-ish format (it's not strict YAML due to comments)
agents = {}
current_agent = None
for line in raw.split("\n"):
    line = line.strip()
    if line.startswith("#") or not line:
        continue
    if ":" in line and not line.startswith("-"):
        # New agent section
        current_agent = line.split(":")[0].strip()
        agents[current_agent] = []
    elif line.startswith("-") and current_agent:
        skill = line[1:].strip()
        agents[current_agent].append(skill)

os.makedirs(OUTPUT_DIR, exist_ok=True)

for agent, whitelist in agents.items():
    if agent in ("visual-engineering", "ultrabrain", "deep", "quick", "writing"):
        # Category-level — skip for now, agents are the priority
        continue
    if not whitelist:
        continue
    
    disabled = sorted(ALL_SKILLS - set(whitelist))
    whitelist_count = len(whitelist)
    disabled_count = len(disabled)
    savings = f"{disabled_count}/{len(ALL_SKILLS)} skills disabled ({disabled_count/len(ALL_SKILLS)*100:.0f}% reduction)"
    
    output = {
        "skills": {
            "disabled": disabled
        }
    }
    
    out_path = os.path.join(OUTPUT_DIR, f"{agent}.yaml")
    with open(out_path, "w") as f:
        yaml.dump(output, f, default_flow_style=False)
    
    print(f"{agent}: {whitelist_count} included, {disabled_count} disabled — {savings}")

print(f"\nGenerated {len([a for a in agents if a not in ('visual-engineering','ultrabrain','deep','quick','writing')])} agent configs in {OUTPUT_DIR}")
