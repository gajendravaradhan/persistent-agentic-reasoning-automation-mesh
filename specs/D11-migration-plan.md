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

# ADD to EACH of these services: api, deriver, database, redis
# (after their existing config, before the next service):
    networks:
      - default
      - param-net
```

### 4. Cloudflare tunnel config: `/home/Nasama-Pochu/.cloudflared/config.yml`
```
# NO CHANGES NEEDED — cloudflared stays in host mode, uses localhost
```

## Deploy Sequence
1. `docker network create param-net` on NAS
2. `docker compose -f /home/Nasama-Pochu/param/honcho/docker-compose.yml down && up -d`
3. Edit hermes config.yaml → restart Hermes container
4. Edit websurfx config.lua → restart Websurfx
5. Replace nginx.conf on NAS → restart nginx
6. `docker compose -f deploy/nas/docker-compose.yml down && up -d` (PARAM services)

## Rollback
If anything fails: restore original docker-compose (network_mode: host for all), restore nginx.conf (127.0.0.1), `docker compose up -d`
