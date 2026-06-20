# D11 — Docker Bridge Network Migration Plan
# Status: PREPARED (awaiting deploy approval)

## Approach
- `param-net` bridge network in PARAM docker-compose
- Honcho joins `param-net` as external network
- Cloudflared stays `network_mode: host` (needs localhost access to Honcho + Nginx)
- All other services use bridge + Docker DNS

## Files Already Prepared (local)
- ✅ deploy/nas/docker-compose.yml — bridge network, port mappings, redis container
- ✅ deploy/nas/pwa/nginx.conf — vaultwarden:8311, hermes:9119

## Files To Change on NAS (requires approval to deploy)

### 1. Hermes config: `/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml`
```yaml
# CHANGE:
  honcho:
    base_url: http://localhost:8000
  # TO:
  honcho:
    base_url: http://honcho-api:8000

# CHANGE:
  searxng_url: http://localhost:8989/search
  # TO:
  searxng_url: http://websurfx:8989/search

# CHANGE:
  model:
    base_url: http://127.0.0.1:8787/zen/go/v1
  # TO:
  model:
    base_url: http://tokeneye:8787/zen/go/v1
```

### 2. Websurfx config: `/home/Nasama-Pochu/param/deploy/nas/websurfx/config.lua`
```lua
# CHANGE:
redis_url = "redis://127.0.0.1:6382"
# TO:
redis_url = "redis://redis-ws:6382"
```

### 3. Honcho docker-compose: `/home/Nasama-Pochu/param/honcho/docker-compose.yml`
```yaml
# ADD after the top-level comment block:
networks:
  param-net:
    external: true

# ADD container_name to API service (for stable DNS on param-net):
#   api:
#     build: ...
#     container_name: honcho-api    ← ADD THIS LINE
#     entrypoint: ...

# ADD to EACH of these services: api, deriver, database, redis
# (after their existing config, before the next service):
    networks:
      - default
      - param-net
```

### 4. Cloudflare tunnel config: `/home/Nasama-Pochu/.cloudflared/config.yml`
```
# NO CHANGES NEEDED — cloudflared stays in host mode, uses localhost
# Note: cloudflared could use Docker DNS if moved to bridge, but host mode
# avoids config.yml changes and ensures outbound tunnel stability.
```

## Deploy Sequence (REVISED — avoids broken intermediary state)
1. `docker network create param-net` on NAS
2. Edit all config files (hermes config.yaml, websurfx config.lua, nginx.conf) — **DO NOT RESTART YET**
3. Edit Honcho docker-compose: add `param-net` external network + `container_name: honcho-api`
4. `docker compose -f /home/Nasama-Pochu/param/honcho/docker-compose.yml down && up -d`
5. `docker compose -f deploy/nas/docker-compose.yml down && up -d` (PARAM services pick up new configs)

## Rollback
If anything fails:
1. `docker compose -f deploy/nas/docker-compose.yml down`
2. Restore original docker-compose (network_mode: host for all non-cloudflared)
3. Restore nginx.conf (127.0.0.1 references)
4. Restore hermes config.yaml (localhost:8000 for honcho, 127.0.0.1:8787 for model)
5. Restore websurfx config.lua (127.0.0.1:6382)
6. Remove `param-net` from Honcho compose, remove `container_name: honcho-api`
7. `docker compose -f honcho/docker-compose.yml down && up -d`
8. `docker compose -f deploy/nas/docker-compose.yml up -d`
9. `docker network rm param-net` (cleanup)
