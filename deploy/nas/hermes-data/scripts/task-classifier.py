#!/usr/bin/env python3
"""
task-classifier.py — Classify kanban tasks as NAS_ONLY vs MACBOOK_REQUIRED.

Reads open tasks from the Hermes kanban board (SQLite at /opt/data/kanban/kanban.db,
or via `hermes kanban list --json` CLI fallback).

Output JSON to stdout:
{
  "nas_only": [{"id":..., "title":...}],
  "macbook_required": [{"id":..., "title":...}],
  "macbook_online": bool,
  "total_open": int
}
"""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

MACBOOK_STATE = "/opt/data/state/macbook-state.json"
KANBAN_DB_PATHS = [
    "/opt/data/kanban/kanban.db",
    "/opt/data/.hermes/kanban/kanban.db",
    "/opt/data/data/kanban/kanban.db",
]
HERMES_BIN = os.environ.get(
    "HERMES_BIN",
    next((p for p in ["/usr/local/bin/hermes", "/opt/hermes/bin/hermes"] if os.path.exists(p)), "hermes")
)

MACBOOK_KEYWORDS = frozenset([
    "code", "implement", "build", "refactor", "test", "debug",
    "write", "fix", "create", "develop", "pr", "commit", "deploy",
    "compile", "install", "configure", "migrate", "upgrade",
])

OPEN_STATUSES = {"todo", "ready", "in_progress", "running", "blocked"}


def read_macbook_state():
    try:
        return json.loads(Path(MACBOOK_STATE).read_text())
    except Exception:
        return {"online": False}


def _classify_task(title, description=""):
    text = f"{title} {description}".lower()
    return any(kw in text.split() or f" {kw} " in f" {text} " for kw in MACBOOK_KEYWORDS)


def fetch_tasks_from_db():
    for db_path in KANBAN_DB_PATHS:
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, title, description, status FROM tasks WHERE status IN ({})".format(
                    ",".join("?" * len(OPEN_STATUSES))
                ),
                list(OPEN_STATUSES),
            )
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception:
            continue
    return None


def fetch_tasks_from_cli():
    try:
        result = subprocess.run(
            [HERMES_BIN, "kanban", "list", "--json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        tasks = data if isinstance(data, list) else data.get("tasks", data.get("items", []))
        return [
            {"id": t.get("id", ""), "title": t.get("title", t.get("subject", "")),
             "description": t.get("description", t.get("body", "")), "status": t.get("status", "")}
            for t in tasks
            if t.get("status", "") in OPEN_STATUSES
        ]
    except Exception:
        return None


def main():
    tasks = fetch_tasks_from_db()
    if tasks is None:
        tasks = fetch_tasks_from_cli()
    if tasks is None:
        tasks = []

    macbook_state = read_macbook_state()
    macbook_online = bool(macbook_state.get("online", False))

    nas_only = []
    macbook_required = []

    for task in tasks:
        entry = {"id": task.get("id", ""), "title": task.get("title", task.get("subject", ""))}
        if _classify_task(task.get("title", ""), task.get("description", "")):
            macbook_required.append(entry)
        else:
            nas_only.append(entry)

    print(json.dumps({
        "nas_only": nas_only,
        "macbook_required": macbook_required,
        "macbook_online": macbook_online,
        "total_open": len(tasks),
    }))


if __name__ == "__main__":
    main()
