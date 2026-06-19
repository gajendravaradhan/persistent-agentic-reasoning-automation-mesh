# PARAM Notification & Escalation Protocol

**Phase 3 deliverable — designed locally, deployed on NAS**

---

## Notification Tiers

| Tier | Label | Trigger Examples | Response Time |
|------|-------|-----------------|---------------|
| **INFO** | Routine status | Cron job completion, memory consolidation, successful deploy | No alert needed |
| **WARNING** | Needs attention | TokenEye approaching rate limit, disk >80%, stale worker detected | Next check-in or 30min |
| **CRITICAL** | Immediate action | Gateway crashed, Telegram disconnected, TokenEye down, >3 consecutive task failures | Instant Telegram alert |

## Diff-Based Alerting (Reddit Pattern)

Consecutive identical status reports must NOT trigger duplicate Telegram messages. The notification system compares current state against last-reported state and only sends when something changed.

```yaml
# Notification state tracking
notify:
  last_state:
    gateway: healthy
    tokeneye: "197 records"
    cron: "5 active"
    disk: "42%"
  cooldown:
    warning: 30m    # minimum between WARNING alerts
    critical: 5m     # minimum between CRITICAL alerts (don't spam)
```

## Escalation Protocol

### WARNING → CRITICAL Escalation

| Warning Condition | Escalates to CRITICAL after | Escalation Action |
|------------------|----------------------------|-------------------|
| TokenEye rate-limited | 3 consecutive probes fail | Telegram: "TokenEye unavailable. Check opencode-go balance." |
| Disk >80% | >90% or 24h unresolved | Telegram: "NAS storage critical. Immediate cleanup needed." |
| Memory bloat (>3KB MEMORY.md) | 7 days unresolved | Telegram: "Memory needs consolidation. Stale entries accumulating." |
| Stale worker | >4h without heartbeat | Task re-queued. Telegram: "Worker X stalled, task reassigned." |

### CRITICAL Escalation Chain

1. **Immediate Telegram alert** with actionable details
2. **If unacknowledged in 15 minutes**: re-alert with escalation marker
3. **If unacknowledged in 1 hour**: alert includes direct action link (dashboard URL)
4. **Auto-recovery attempted**: gateway restart, TokenEye restart where possible

## Event-Driven Triggers

| Event | Source | Tier | Message |
|-------|--------|------|---------|
| `gateway.crash` | Docker healthcheck | CRITICAL | "PARAM gateway crashed. Restarting..." |
| `telegram.disconnected` | Gateway logs | CRITICAL | "Telegram connection lost. Reconnecting..." |
| `tokeneye.down` | Health probe | CRITICAL | "TokenEye unavailable. Models unreachable." |
| `kanban.stall` | Dispatcher hook | WARNING | "Kanban board stalled. X tasks waiting." |
| `memory.bloat` | Cron job | WARNING | "Memory approaching limit. Consider pruning." |
| `deploy.available` | Git SHA check | INFO | "New deploy available. Current: X, Latest: Y" |
| `token.threshold` | TokenEye metrics | WARNING | "Daily spend: $X. Threshold: $Y." |
| `provider.down` | Inference probe | WARNING | "Provider X failed health check. Falling back." |

## Implementation

These are config-level and cron-job-level changes. No core code modifications needed — all implemented through Hermes cron jobs with Telegram delivery.

### Cron Job: `notification-controller`

```
schedule: "*/5 * * * *"   # every 5 minutes
prompt: |
  Check notification state against current system state:
  - Gateway health (process alive, Telegram connected)
  - TokenEye health (responds, records incrementing)
  - Kanban board (stalled tasks, failure counts)
  - Memory usage (MEMORY.md size, Honcho health)
  - Provider health (last successful inference probe)
  
  Compare against last reported state. Only report deltas.
  Classify by tier. Apply cooldown rules.
  Deliver via Telegram if actionable.
```

### Integration with param-status.sh

Extend `param-status.sh` to output machine-parseable JSON alongside human-readable output for the notification controller to consume:

```bash
./param-status.sh --json  # outputs JSON for machine consumption
./param-status.sh          # human-readable dashboard
```
