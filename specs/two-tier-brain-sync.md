# PARAM Two-Tier Bidirectional Sync Specification

**Status:** DRAFT — Pending Implementation Approval  
**Architecture:** Two Agentic Systems, 1 Brain, Common Knowledge, 1 Set of Capabilities  
**Date:** 2026-06-28

---

## 1. Goal & Principles

**Goal:** Operate PARAM as two parallel execution surfaces (MacBook + NAS) that share a single, eventually-consistent brain.

**Principles:**
- **Both systems can write** — skills, memories, cron jobs created on either side propagate to the other
- **Idempotent merges** — re-running sync produces no new state if nothing changed
- **Conflict-safe** — concurrent edits to the same file use last-writer-wins with backup of the replaced version
- **No runtime coupling** — sync runs on a cron schedule, not inline with agent tool calls. Either side can be down without blocking the other.
- **Bidirectional** — Mac → NAS AND NAS → Mac, in each sync tick

---

## 2. What Gets Synced (and What Doesn't)

### ✅ Synced (Common Brain)

| Path | Mac | NAS | Notes |
|---|---|---|---|
| Memories | `~/.hermes/memories/MEMORY.md` | `/opt/data/memories/MEMORY.md` | Single file, most contentious |
| Memories | `~/.hermes/memories/USER.md` | `/opt/data/memories/USER.md` | User profile |
| Skills | `~/.hermes/skills/*` | `/opt/data/skills/*` | Directory tree — Unison excels here |
| Cron job definitions | `~/.hermes/cron/jobs.json` | `/opt/data/cron/jobs.json` | THE HARD PART — see Section 4 |

### ❌ NOT Synced (Platform-Specific State)

| Path | Reason |
|---|---|
| `~/.hermes/.tick.lock`, `.jobs.lock` | Per-host scheduler state |
| `~/.hermes/sessions/` on NAS | Different conversation histories — never merge |
| `~/.hermes/hermes-agent/` | The Hermes runtime binary itself — different versions per host |
| `~/.hermes/logs/` | Per-host logs |
| `~/.hermes/cache/` | Per-host cache |

---

## 3. Tool Selection: Rsync with Bidirectional Logic

Unison is the textbook tool but requires installation on both Mac and NAS, plus same version on both ends (notoriously finicky). For a 4-file/directory sync, a **rsync-based script with conflict detection** is simpler and uses tools already present.

### Script: `param-brain-sync.sh`

```bash
#!/usr/bin/env bash
# param-brain-sync.sh — bidirectional sync of PARAM's "brain" between Mac and NAS
# Runs via launchd every 5 minutes. Safe to run concurrently — uses flock.
# Conflict policy: last-writer-wins, with .conflict-<timestamp> backup of the losing side

set -euo pipefail

# Config
NAS_HOST="Nasama-Pochu@192.168.1.167"
NAS_HERMES_ROOT="/home/Nasama-Pochu/.hermes"  # Path on NAS (assuming same layout)
MAC_HERMES_ROOT="$HOME/.hermes"
LOCK_FILE="/tmp/param-brain-sync.lock"
LOG_FILE="$HOME/.hermes/logs/brain-sync.log"
TS=$(date +%Y%m%d-%H%M%S)

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$TS: another sync is running — skipping" >> "$LOG_FILE"
  exit 0
fi

mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "$TS: $*" >> "$LOG_FILE"; }

log "=== starting bidirectional brain sync ==="

# Files to sync (relative to HERMES_ROOT)
SYNC_PATHS=(
  "memories/MEMORY.md"
  "memories/USER.md"
  "cron/jobs.json"
)
# Synced directories
SYNC_DIRS=(
  "skills"
)

# Conflict detection: if both sides changed since last sync, the .last-sync-hash file tells us
LAST_SYNC_STATE="$MAC_HERMES_ROOT/.brain-sync-state.json"

# Helper: get SHA256 of a file (empty string if missing)
file_hash() {
  if [ -f "$1" ]; then
    shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1
  else
    echo "MISSING"
  fi
}

# Per-file bidirectional sync with conflict detection
sync_file() {
  local rel="$1"
  local mac_file="$MAC_HERMES_ROOT/$rel"
  local nas_file="$NAS_HERMES_ROOT/$rel"
  
  # Pull NAS version to a temp file for comparison
  local tmp_nas="/tmp/.param-sync-nas-$TS-$(echo "$rel" | tr / _)"
  if ! scp -q -o ConnectTimeout=5 "$NAS_HOST:$nas_file" "$tmp_nas" 2>/dev/null; then
    log "WARN: could not fetch NAS:$nas_file — skipping $rel"
    return 0
  fi
  
  local mac_hash=$(file_hash "$mac_file" 2>/dev/null || echo "MISSING")
  local nas_hash=$(shasum -a 256 "$tmp_nas" 2>/dev/null | cut -d' ' -f1)
  
  if [ "$mac_hash" = "$nas_hash" ]; then
    log "OK: $rel in sync"
    rm -f "$tmp_nas"
    return 0
  fi
  
  # Conflict detection via last-sync hash
  local last_hash=$(python3 -c "
import json, os
state = json.load(open('$LAST_SYNC_STATE')) if os.path.exists('$LAST_SYNC_STATE') else {}
print(state.get('$rel', 'NONE'))
" 2>/dev/null || echo "NONE")
  
  if [ "$mac_hash" = "$last_hash" ]; then
    # Only NAS changed → pull NAS → Mac
    log "PULL: $rel changed on NAS only → updating Mac"
    mkdir -p "$(dirname "$mac_file")"
    cp "$tmp_nas" "$mac_file"
  elif [ "$nas_hash" = "$last_hash" ]; then
    # Only Mac changed → push Mac → NAS
    log "PUSH: $rel changed on Mac only → updating NAS"
    ssh -o ConnectTimeout=5 "$NAS_HOST" "mkdir -p \"\$(dirname $nas_file)\""
    scp -q "$mac_file" "$NAS_HOST:$nas_file"
  else
    # Both changed → conflict, last-writer-wins by mtime
    local mac_mtime=$(stat -f %m "$mac_file" 2>/dev/null || echo 0)
    local nas_mtime=$(ssh -o ConnectTimeout=5 "$NAS_HOST" "stat -c %Y $nas_file" 2>/dev/null || echo 0)
    
    if [ "$mac_mtime" -gt "$nas_mtime" ]; then
      log "CONFLICT: $rel changed on both — Mac is newer (last-writer-wins)"
      ssh -o ConnectTimeout=5 "$NAS_HOST" "cp $nas_file $nas_file.conflict-$TS 2>/dev/null || true"
      scp -q "$mac_file" "$NAS_HOST:$nas_file"
    else
      log "CONFLICT: $rel changed on both — NAS is newer (last-writer-wins)"
      cp "$mac_file" "$mac_file.conflict-$TS" 2>/dev/null || true
      cp "$tmp_nas" "$mac_file"
    fi
  fi
  
  rm -f "$tmp_nas"
}

# Directory sync (skills/) — uses rsync --delete with backup of replaced files
sync_dir() {
  local rel="$1"
  local mac_dir="$MAC_HERMES_ROOT/$rel"
  local nas_dir="$NAS_HERMES_ROOT/$rel"
  
  log "SYNC DIR: $rel (bidirectional with --delete + backup)"
  
  # Mac → NAS (with --backup to preserve any NAS-only files being deleted)
  rsync -avz --delete --backup --backup-dir="/tmp/.param-sync-backup-nas-$TS" \
    -e "ssh -o ConnectTimeout=5" \
    "$mac_dir/" "$NAS_HOST:$nas_dir/" 2>>"$LOG_FILE" || log "WARN: Mac→NAS sync of $rel had errors"
  
  # NAS → Mac (with --delete --backup for any Mac-only files)
  rsync -avz --delete --backup --backup-dir="/tmp/.param-sync-backup-mac-$TS" \
    -e "ssh -o ConnectTimeout=5" \
    "$NAS_HOST:$nas_dir/" "$mac_dir/" 2>>"$LOG_FILE" || log "WARN: NAS→Mac sync of $rel had errors"
}

# Run syncs
for path in "${SYNC_PATHS[@]}"; do
  sync_file "$path"
done

for dir in "${SYNC_DIRS[@]}"; do
  sync_dir "$dir"
done

# Update last-sync state file with current hashes
python3 << PY >> "$LOG_FILE" 2>&1
import json, os, hashlib
state = {}
for rel in ["memories/MEMORY.md", "memories/USER.md", "cron/jobs.json"]:
    p = os.path.expanduser("~/.hermes/" + rel)
    if os.path.exists(p):
        state[rel] = hashlib.sha256(open(p,'rb').read()).hexdigest()
os.makedirs(os.path.dirname("$LAST_SYNC_STATE"), exist_ok=True)
with open("$LAST_SYNC_STATE","w") as f:
    json.dump(state, f, indent=2)
PY

log "=== sync complete ==="
flock -u 9
```

---

## 4. The Cron Jobs Sync — Hard Part

`cron/jobs.json` is a single file listing jobs. Two-way sync is dangerous: jobs fire on BOTH systems if synced verbatim. That would double-execute every job.

### Resolution: Cron Job Namespacing

**Convention:** Prefix every job with the originating system.
- Mac-created jobs: `mac-<name>`
- NAS-created jobs: `nas-<name>`
- Cross-system jobs (both should run): `shared-<name>`

**Sync behavior:**
- `cron/jobs.json` IS synced bidirectionally (so both sides KNOW about all jobs)
- Each side's scheduler only fires jobs whose prefix matches its role OR `shared-`
- This requires the Hermes scheduler to filter jobs by prefix — needs a small patch to the Hermes cron runner, OR a pre-filter script that strips non-matching jobs before loading.

**Simpler alternative (recommended for v1):** Don't sync `cron/jobs.json` at all. Cron jobs are platform-specific by nature (Mac-crons need Mac files; NAS-crons need NAS context). Document that cron jobs live on the side that created them.

---

## 5. Schedule

**Launchd plist:** `~/Library/LaunchAgents/ai.param.brain-sync.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>ai.param.brain-sync</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/scripts/param-brain-sync.sh</string>
  </array>
  <key>StartInterval</key>
  <integer>300</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/gajendra/.hermes/logs/brain-sync.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/gajendra/.hermes/logs/brain-sync.error.log</string>
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
```

NAS side: equivalent cron entry via `crontab -e` on the NAS host:
```
*/5 * * * * flock -n /tmp/param-brain-sync.lock /home/Nasama-Pochu/param/scripts/param-brain-sync.sh
```

---

## 6. Conflict Handling & Recovery

### Last-writer-wins with backup

When both sides modify the same file:
1. Detect divergence (neither hash matches `last-sync-state`)
2. Compare mtime
3. Newer side wins
4. The loser side gets a `.conflict-<timestamp>` backup for manual review
5. Log the conflict clearly

### Recovery from Bad Sync

If the sync messes something up:
- Backup files are in `/tmp/.param-sync-backup-<host>-<timestamp>/` (preserved for 7 days via separate cleanup cron)
- Last-sync state at `~/.hermes/.brain-sync-state.json` can be deleted to force full reconciliation
- Manual override: `cd ~/.hermes/memories && cp MEMORY.md.conflict-20260628-103000 MEMORY.md`

---

## 7. Verification Plan

After first sync run:
1. Check `~/.hermes/logs/brain-sync.log` — all paths show `OK`, `PULL`, `PUSH`, or `CONFLICT`
2. `diff <(ssh Nasama-Pochu@192.168.1.167 'cat /opt/data/memories/MEMORY.md') ~/.hermes/memories/MEMORY.md` — should match
3. `diff <(ssh ... 'ls /opt/data/skills/') <(ls ~/.hermes/skills/)` — should match
4. Create a test skill on Mac → verify it appears on NAS within 5 minutes via `ssh ... ls /opt/data/skills/`
5. Modify MEMORY.md on NAS (via Telegram-driven `hermes__memory`) → verify it appears on Mac within 5 minutes

---

## 8. What This Does NOT Solve

1. **Different model routing** — Mac uses GLM-5.2 (per `oh-my-openagent.json`), NAS uses kimi-k2.6. The "personality" still differs by entry point. Out of scope for sync — requires separate alignment of `oh-my-openagent.json` and NAS `config.yaml`.
2. **Session histories** — Telegram conversations live on NAS, opencode sessions live in Mac's `opencode.db`. These are NOT synced (different modalities, different schemas).
3. **Long-running tasks** — `terminal(background=true, notify_on_complete=true)` only works on Mac (no terminal tool on NAS Telegram path). NAS long-running work happens via cron, not background processes.
4. **Browser/computer_use** — Mac-only capability. NAS has no display.

---

## 9. Implementation Steps (Pending Approval)

1. ✅ Mac→NAS SSH already works with key auth (you set up `Nasama-Pochu@192.168.1.167`)
2. Copy `scripts/param-brain-sync.sh` to Mac + NAS
3. Create `~/Library/LaunchAgents/ai.param.brain-sync.plist` on Mac
4. Add the 5-minute cron entry on NAS
5. Run once manually to verify
6. Load the launchd job: `launchctl load ai.param.brain-sync.plist`
7. Watch the log for one full cycle (5 min)

---

## 10. Open Questions for User

1. **Cron job sync:** Skip entirely (recommended for v1) or implement namespacing convention?
2. **Model alignment:** Out of scope for sync, but do you want me to separately align the two configs (Mac's `oh-my-openagent.json` + NAS `config.yaml` to use the same model)?
3. **Conflict policy:** Last-writer-wins acceptable, or do you want manual review prompts before either side overwrites?

---

**Approval needed before implementing.** This is an infrastructure change (new launchd plist, new cron entry, new file writes on both Mac and NAS). Per governance gate, awaiting explicit "yes" before applying.
