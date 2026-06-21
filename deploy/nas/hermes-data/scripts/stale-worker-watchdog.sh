#!/usr/bin/env bash
# stale-worker-watchdog.sh — Reap tasks stuck in 'running' with no heartbeat >15 min.
# no_agent=true, runs every 15 min. Emits one line per stale task found; silent otherwise.

HERMES_BIN="${HERMES_BIN:-$(command -v hermes 2>/dev/null || echo /usr/local/bin/hermes)}"
STALE_SECONDS=900

if ! command -v python3 >/dev/null 2>&1; then
    exit 0
fi

running_json=$("$HERMES_BIN" kanban list --status running --json 2>/dev/null)
if [ -z "$running_json" ]; then
    exit 0
fi

now_epoch=$(date +%s)

stale_ids=$(python3 - "$running_json" "$now_epoch" "$STALE_SECONDS" << 'PYEOF'
import json, sys, datetime

raw = sys.argv[1]
now = int(sys.argv[2])
threshold = int(sys.argv[3])

try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

tasks = data if isinstance(data, list) else data.get("tasks", data.get("items", []))

for t in tasks:
    updated = t.get("updatedAt") or t.get("updated_at") or t.get("last_heartbeat")
    if not updated:
        continue
    try:
        if updated.endswith("Z"):
            updated = updated[:-1] + "+00:00"
        ts = datetime.datetime.fromisoformat(updated)
        if ts.tzinfo is None:
            import datetime as dt
            ts = ts.replace(tzinfo=dt.timezone.utc)
        age = now - int(ts.timestamp())
        if age > threshold:
            print(t.get("id", ""))
    except Exception:
        continue
PYEOF
)

if [ -z "$stale_ids" ]; then
    exit 0
fi

while IFS= read -r task_id; do
    [ -z "$task_id" ] && continue
    "$HERMES_BIN" kanban update --id "$task_id" --status blocked \
        --note "stale_worker_timeout: no heartbeat for >15 min" 2>/dev/null
    echo "STALE_REAPED: task $task_id blocked (stale_worker_timeout)"
done <<< "$stale_ids"
