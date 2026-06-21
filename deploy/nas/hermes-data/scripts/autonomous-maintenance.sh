#!/usr/bin/env bash
# autonomous-maintenance.sh — PARAM low-risk routine task execution
# Runs every 6 hours (no_agent=true). Produces output only when action taken.
# Safe operations only: health checks, log rotation, state cleanup.

LOG="/tmp/param-maintenance.log"
STATE="/opt/data/state/maintenance-state.json"
MAX_LOG_MB=50
MAX_STATE_DAYS=30
REPORT=""

_log() { echo "[$(date -Iseconds)] $*" >> "$LOG"; }
_report() { REPORT="$REPORT$*\n"; }

mkdir -p "$(dirname "$STATE")" "$(dirname "$LOG")"

_rotate_logs() {
    for logfile in /opt/data/logs/agent.log /opt/data/logs/errors.log; do
        [ -f "$logfile" ] || continue
        size_mb=$(du -m "$logfile" 2>/dev/null | cut -f1)
        if [ "${size_mb:-0}" -gt "$MAX_LOG_MB" ]; then
            mv "$logfile" "${logfile}.$(date +%Y%m%d-%H%M%S).bak"
            touch "$logfile"
            _log "Rotated $logfile (was ${size_mb}MB)"
            _report "LOG_ROTATED: $logfile was ${size_mb}MB"
        fi
    done
}

_prune_state_files() {
    pruned=0
    for f in /opt/data/state/*.json; do
        [ -f "$f" ] || continue
        mod=$(find "$f" -mtime "+${MAX_STATE_DAYS}" 2>/dev/null | wc -l)
        if [ "$mod" -gt 0 ]; then
            rm -f "$f"
            pruned=$((pruned + 1))
            _log "Pruned stale state: $f"
        fi
    done
    [ "$pruned" -gt 0 ] && _report "STATE_PRUNED: $pruned stale files removed"
}

_check_disk_space() {
    usage=$(df /opt/data 2>/dev/null | awk 'NR==2{print $5}' | tr -d '%')
    if [ "${usage:-0}" -gt 85 ]; then
        _report "DISK_WARNING: /opt/data at ${usage}% capacity"
        _log "Disk warning: ${usage}%"
    fi
}

_backup_audit_log() {
    audit="/opt/data/router/audit_log.jsonl"
    [ -f "$audit" ] || return
    size=$(wc -l < "$audit" 2>/dev/null)
    if [ "${size:-0}" -gt 10000 ]; then
        cp "$audit" "${audit}.$(date +%Y%m).bak"
        tail -1000 "$audit" > "${audit}.tmp" && mv "${audit}.tmp" "$audit"
        _log "Trimmed audit log from ${size} to 1000 lines"
        _report "AUDIT_TRIMMED: from ${size} lines to 1000"
    fi
}

_verify_skill_state() {
    metrics="/opt/data/state/skill-metrics.json"
    if [ ! -f "$metrics" ]; then
        echo '{"skills":{},"updated_at":null}' > "$metrics"
        _log "Initialized missing skill-metrics.json"
    fi
}

_verify_notify_state() {
    state_file="/opt/data/state/notify-state.json"
    if [ ! -f "$state_file" ]; then
        echo '{}' > "$state_file"
        _log "Initialized missing notify-state.json"
    fi
}

_rotate_logs
_prune_state_files
_check_disk_space
_backup_audit_log
_verify_skill_state
_verify_notify_state

if [ -n "$REPORT" ]; then
    printf "%b" "$REPORT"
fi
