# GENERIC-PARAM-SPEC — Config-Driven Installation Wizard

**Status**: Draft — implementation-ready spec  
**Date**: June 22, 2026  
**Purpose**: Enable any user to install PARAM with their own choices via an interactive wizard, not manual file editing.

---

## Executive Summary

PARAM today ships with `INSTALL.md` (a human-readable guide) and static template files. A new user must manually translate every configuration choice into file edits across 4-5 files. This spec defines a **Python installation wizard** (`param_install.py`) that interviews the user, validates constraints, generates all config files, and verifies the result.

The spec covers three dimensions:

1. **Feasibility analysis** — which combinations of choices are viable, degraded, or infeasible
2. **Installer architecture** — module structure, data model, interview flow, config generators, constraint rules, verification
3. **Testing pyramid** — unit, functional, integration, and E2E tests per canonical profile

**Scope**: ~1,400 lines of Python (installer) + ~3,200 lines of tests. No external dependencies beyond PyYAML.

---

# Part I — Feasibility Analysis

## Decision Dimensions

The installer presents 9 decision dimensions. Each dimension has 2-7 options.

| Dim | Name | Options | Gates |
|-----|------|---------|-------|
| **A** | Deployment mode | `local`, `nas`, `cloud-vm` | A gates H; A1 gates Docker-dependent options |
| **B** | LLM provider | `opencode-go`, `anthropic`, `openai`, `openrouter`, `ollama` | B gates C |
| **C** | TokenEye mode | `1key`, `2key`, `3plus`, `none` | C gates F4 |
| **D** | Memory layer | `memory-md`, `honcho-self`, `honcho-cloud`, `mem0`, `honcho-self+mem0`, `hindsight`, `three-layer` | D2/D5/D6/D7 require Docker |
| **E** | Messaging | `none`, `telegram`, `discord`, `telegram+discord`, `telegram+webhook`, `all` | E5/E6 require public ingress |
| **F** | Observability | `none`, `langfuse-cloud`, `langfuse-self`, `tokeneye-only` | F3 requires Docker + 2GB RAM; F4 requires C≠none |
| **G** | Secrets | `env-file`, `vaultwarden`, `external` | G2 requires Docker |
| **H** | Remote access | `n/a`, `lan-only`, `cloudflare`, `tailscale`, `direct-tls` | H only shown if A≠local; H2 requires CF domain |
| **I** | Search backend | `public`, `websurfx`, `searxng` | I2/I3 require Docker; I3 blocked on UGREEN NAS |

## Forcing Constraints (Hard Eliminations)

These constraints eliminate infeasible combinations before the user sees them.

### C1: Docker-Dependent Options vs. Local Deployment

`D2` (Honcho self-hosted), `D6` (Hindsight), `D7` (three-layer), `F3` (Langfuse self-hosted), `G2` (Vaultwarden), `I2` (Websurfx), `I3` (SearXNG) all require a running Docker daemon.

- With `A1` (local-only) and no Docker Desktop: these options are **INFEASIBLE** (hidden from interview).
- With `A1` and Docker Desktop installed: these options are **VIABLE** but heavyweight.
- With `A2`/`A3`: Docker is assumed available; these options are **VIABLE**.

### C2: TokenEye Value Proposition by Provider

- `C1` (TokenEye) was built for opencode-go's managed auth model. For `B1` (opencode-go): full load balancing + failover + cost tracking.
- For `B3`/`B4`/`B5` (Anthropic, OpenAI, OpenRouter): TokenEye works as passthrough proxy, providing cost tracking but **no load balancing benefit**. `B3+C1(2key)` = **DEGRADED** (warning: passthrough only).
- For `B6` (Ollama): TokenEye adds **zero value** — local inference has no API keys to balance and no cost to track. `B6+C1` = **DEGRADED** (auto-fix to `C2=none`).

### C3: Memory Provider Exclusivity

Hermes supports exactly one active `memory.provider` at runtime.

- `D5` (Honcho self + Mem0): Honcho is primary; Mem0 runs as auxiliary knowledge graph. **VIABLE** but requires understanding that Hermes only queries Honcho directly.
- `D7` (three-layer): Honcho primary + Hindsight semantic search + Obsidian vault. **VIABLE** for power users; requires local Obsidian + vault sync workflow.

### C4: 24/7 Messaging Requires 24/7 Runtime

- `E2`-`E6` (any messaging channel) with `A1` (local-only): **DEGRADED** — Telegram/Discord long-polling stops when the MacBook sleeps. The bot becomes unresponsive.
- For true 24/7 messaging: `A2` or `A3` is required.
- `E5`/`E6` (webhook channels) with `A1`: **INFEASIBLE** — webhooks require a public endpoint.

### C5: Remote Access Scope

- `H` only applies when `A2` or `A3`. With `A1`, `H2`/`H3`/`H4` are **INFEASIBLE** (no always-on service to tunnel to).
- `H2` (Cloudflare Tunnel) requires: CF account + registered domain + `cloudflared` installed. Most setup-intensive but most reliable.
- `H3` (Tailscale) requires: Tailscale account. Easiest for personal use. **Cannot receive public GitHub/CI webhooks.**
- `H4` (Direct TLS) requires: public IP + TLS certificate. Most control, most complex.

### C6: Langfuse Self-Hosted Resource Cost

- `F3` (Langfuse self-hosted) requires ClickHouse → ~1-2GB RAM minimum.
- On a resource-constrained NAS (4GB total, shared with 15+ containers): **DEGRADED** — risk of destabilizing other containers.
- `F3` is **VIABLE** only with `A3` (cloud VM, typically 4-8GB dedicated) or a high-RAM NAS.
- `F2` (cloud, free tier) is the correct choice for most `A2` users.

### C7: SearXNG on UGREEN NAS

- `I3` is confirmed **INFEASIBLE** on UGREEN NAS (Docker image kernel incompatibility, documented in ROADMAP.md task 6.1.1).
- For `A2` on UGREEN: `I3` hidden from interview.
- For `A2` on other NAS hardware or `A3`: `I3` is **VIABLE**.

### C8: Secrets Vault Without Docker

- `G2` (Vaultwarden) is a Docker container.
- With `A1` and no Docker Desktop: **INFEASIBLE**.
- With Docker Desktop on Mac: **VIABLE** but heavyweight.
- For `A2`/`A3`: **VIABLE**, natural fit.

### C9: Webhook Requirements

- `E5` (Telegram + webhook) and `E6` (all channels) require public ingress.
- With `H1` (LAN only) or `H3` (Tailscale) or `H=n/a`: **INFEASIBLE** — no public endpoint for webhook delivery.
- Webhooks require `H2` (Cloudflare) or `H4` (Direct TLS).

## Canonical Profiles

Six viable profiles survive the constraint analysis. Each is a pre-set that skips the full interview.

| Profile | A | B | C | D | E | F | G | H | I | Verdict |
|---------|---|---|---|---|---|---|---|---|---|---------|
| **Minimal-Local** | local | anthropic/openai | none | memory-md | none | none | env-file | n/a | public | VIABLE-DEGRADED (no 24/7, no persistence) |
| **Developer-Local** | local | opencode-go | 2key | honcho-cloud | telegram | langfuse-cloud | env-file | n/a | public | VIABLE (full dev experience) |
| **Full-NAS** | nas | opencode-go | 2key | honcho-self | telegram+discord | langfuse-cloud | vaultwarden | cloudflare | websurfx | VIABLE (reference PARAM) |
| **Cloud-VM-Budget** | cloud-vm | openrouter | none | honcho-cloud | telegram | langfuse-cloud | env-file | tailscale | public | VIABLE (low-cost always-on) |
| **Cloud-VM-Full** | cloud-vm | opencode-go | 3plus | three-layer | all | langfuse-cloud | vaultwarden | cloudflare | websurfx | VIABLE (maximum power) |
| **Offline-Dev** | local | ollama | none | memory-md | none | none | env-file | n/a | public | VIABLE-DEGRADED (no cost tracking, no memory persistence, no remote) |

### Eliminated Combinations (Non-Exhaustive)

| Combination | Reason | Verdict |
|-------------|--------|---------|
| A1 + H2/H3/H4 | No always-on service to tunnel to | INFEASIBLE |
| A1 (no Docker) + D2/D6/D7 | Docker-dependent memory | INFEASIBLE |
| A1 (no Docker) + G2 | Vaultwarden requires Docker | INFEASIBLE |
| A1 (no Docker) + F3 | Self-hosted Langfuse requires Docker | INFEASIBLE |
| A2 (UGREEN) + I3 | SearXNG kernel incompatibility | INFEASIBLE |
| B6 + C1 | TokenEye useless for local Ollama | DEGRADED (auto-fix to C=none) |
| B3/B4/B5 + C1(2key/3plus) | TokenEye LB only for opencode-go | DEGRADED (passthrough only) |
| E5/E6 + H1/H3/n/a | Webhooks need public ingress | INFEASIBLE |
| F3 + RAM<2GB | ClickHouse needs 2GB minimum | INFEASIBLE |
| F3 + RAM<4GB | ClickHouse may destabilize other containers | DEGRADED (warning) |
| F4 + C=none | TokenEye dashboard needs TokenEye | INFEASIBLE |

---

# Part II — Installer Architecture

## Module Structure

```
scripts/
  param_install.py              # Entry point (~80 lines)
  installer/
    __init__.py
    models.py                   # InstallConfig dataclass (~120 lines)
    interview.py                # Question engine (~180 lines)
    constraints.py              # Rule checker (~160 lines)
    backup.py                   # Backup/idempotency (~80 lines)
    verifier.py                 # Post-generation checks (~120 lines)
    generators/
      __init__.py               # Generator orchestrator (~60 lines)
      env_generator.py          # ~/.hermes/.env (~100 lines)
      config_generator.py       # ~/.hermes/config.yaml (~140 lines)
      mcp_generator.py          # ~/.mcp.json (~80 lines)
      tokeneye_generator.py     # tokeneye config (~70 lines)
      docker_generator.py       # docker-compose.override.yml (~150 lines)
      skills_generator.py       # per-agent skill configs (~60 lines)
```

**Total**: ~1,400 lines. No external dependencies beyond PyYAML (already in the project venv).

## InstallConfig Data Model

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

DeploymentMode  = Literal["local", "nas", "cloud-vm"]
LLMProvider     = Literal["opencode-go", "anthropic", "openai", "openrouter", "ollama"]
TokenEyeMode    = Literal["1key", "2key", "3plus", "none"]
MemoryMode      = Literal["memory-md", "honcho-self", "honcho-cloud",
                          "mem0", "honcho-self+mem0", "hindsight", "three-layer"]
MessagingMode   = Literal["none", "telegram", "discord",
                          "telegram+discord", "telegram+webhook", "all"]
ObsMode         = Literal["none", "langfuse-cloud", "langfuse-self", "tokeneye-only"]
SecretsMode     = Literal["env-file", "vaultwarden", "external"]
RemoteMode      = Literal["n/a", "lan-only", "cloudflare", "tailscale", "direct-tls"]
SearchMode      = Literal["public", "websurfx", "searxng"]

@dataclass
class InstallConfig:
    # ── Core 9 dimensions ──────────────────────────────────────────────────
    deployment:    DeploymentMode
    provider:      LLMProvider
    tokeneye:      TokenEyeMode
    memory:        MemoryMode
    messaging:     MessagingMode
    observability: ObsMode
    secrets:       SecretsMode
    remote:        RemoteMode
    search:        SearchMode

    # ── Provider credentials ────────────────────────────────────────────────
    opencode_keys:       list[str]          = field(default_factory=list)  # 1-3 items
    anthropic_key:       Optional[str]      = None
    openai_key:          Optional[str]      = None
    openrouter_key:      Optional[str]      = None
    ollama_base_url:     str                = "http://localhost:11434"
    primary_model:       str                = "kimi-k2.5"

    # ── Messaging credentials ───────────────────────────────────────────────
    telegram_token:      Optional[str]      = None
    telegram_user_ids:   list[str]          = field(default_factory=list)
    discord_token:       Optional[str]      = None
    webhook_secret:      Optional[str]      = None

    # ── Memory credentials / URLs ───────────────────────────────────────────
    honcho_api_key:      Optional[str]      = None   # cloud only
    honcho_url:          str                = "http://localhost:8000"
    mem0_api_key:        Optional[str]      = None

    # ── Observability ────────────────────────────────────────────────────────
    langfuse_public_key: Optional[str]      = None
    langfuse_secret_key: Optional[str]      = None
    langfuse_host:       str                = "https://cloud.langfuse.com"

    # ── Remote access ────────────────────────────────────────────────────────
    cloudflare_tunnel_name: Optional[str]   = None
    cloudflare_domain:      Optional[str]   = None

    # ── Paths (resolved at interview time) ──────────────────────────────────
    repo_root:       Path = field(default_factory=Path.cwd)
    hermes_home:     Path = field(default_factory=lambda: Path.home() / ".hermes")
    mcp_json_path:   Path = field(default_factory=lambda: Path.home() / ".mcp.json")
    venv_python:     Optional[Path] = None  # resolved by find_venv_python()

    # ── Computed / derived (populated by constraints.py) ────────────────────
    requires_docker:    bool        = False
    docker_services:    list[str]   = field(default_factory=list)
    degraded_warnings:  list[str]   = field(default_factory=list)
    docker_available:   bool        = False
    nas_hardware:       Optional[str] = None  # "ugreen" | "synology" | "generic" | None
    host_ram_gb:        Optional[int] = None

    # ── Install metadata ────────────────────────────────────────────────────
    profile_name:    Optional[str]  = None   # "laptop-lite" etc if using preset
    upgrade_mode:    bool           = False
    backup_dir:      Optional[Path] = None
```

## Interview Engine — Full Question Flow

```
Q1:  Deployment mode?
     [1] local  — MacBook/desktop, interactive sessions only
     [2] nas    — NAS/home server with Docker, always-on
     [3] cloud-vm — VPS/cloud VM with Docker, always-on
     → always shown first; gates H dimension

Q2:  Is Docker available on this host?
     [y/n]
     → shown if Q1=local (needed to unlock Docker-dependent options)
     → assumed yes if Q1=nas|cloud-vm (abort if Docker check fails)

Q3:  NAS hardware type?  (Q1=nas only)
     [1] UGREEN
     [2] Synology
     [3] Other (generic Docker host)
     → gates I3 (SearXNG blocked on UGREEN)

Q4:  Approximate available RAM for new containers? (GB)
     [free-form integer]
     → shown if Q1=nas|cloud-vm
     → gates F3 (warn if <4GB, hard error if <2GB)

Q5:  LLM provider?
     [1] opencode-go  — managed auth, 20 models, load-balanceable  [recommended]
     [2] anthropic    — Claude direct API key
     [3] openai       — GPT direct API key
     [4] openrouter   — aggregator, hundreds of models
     [5] ollama       — local self-hosted, zero cost, offline
     → gates C dimension

Q6:  Number of opencode-go API keys?  (Q5=opencode-go only)
     [1] One key (cost tracking only, no failover)
     [2] Two keys (full load balancing + failover)  [recommended]
     [3] Three or more keys (maximum failover depth)
     → determines TokenEye mode

Q7:  Enter opencode-go API key(s):  (Q5=opencode-go only)
     → prompted N times based on Q6
     → validated: must start with "sk-" + non-empty

Q8:  Use TokenEye proxy?  (Q5=anthropic|openai|openrouter only)
     [1] Yes — cost tracking via TokenEye passthrough
     [2] No  — direct API calls  [recommended]
     → note shown: "TokenEye adds cost visibility but not load balancing for this provider"

Q9:  Enter [provider] API key:  (Q5=anthropic|openai|openrouter)
     → validated per provider:
       anthropic: starts with "sk-ant-"
       openai:    starts with "sk-"
       openrouter: starts with "sk-or-"

Q10: Memory layer?
     [1] MEMORY.md only    — flat file, no external service  [simplest]
     [2] Honcho cloud      — dialectic memory, API key required
     [3] Honcho self-hosted — Docker sidecar, best for NAS/VM
     [4] Mem0 cloud        — knowledge graph, API key required
     [5] Honcho self + Mem0 — two-layer (Honcho primary, Mem0 auxiliary)
     [6] Hindsight/pgvector — semantic search, Docker sidecar
     [7] Full three-layer  — Honcho + Hindsight + Obsidian vault  [power users]
     → D2/D5/D6/D7 hidden if Docker unavailable
     → D7 shown only if Q1=local with Docker, or Q1=nas|cloud-vm

Q11: Messaging channels?
     [1] None — interactive OpenCode sessions only
     [2] Telegram
     [3] Discord
     [4] Telegram + Discord
     [5] Telegram + Webhook
     [6] All three
     → E5/E6 shown only if Q1=nas|cloud-vm AND Q14 will be cloudflare|direct-tls
     → if Q1=local: show warning "Messaging stops when your machine sleeps"

Q12: Enter Telegram bot token:  (E2/E4/E5/E6 selected)
     → validated: matches \d+:[A-Za-z0-9_-]{35}

Q13: Enter your Telegram user ID(s):  (E2/E4/E5/E6 selected)
     → validated: numeric

Q14: Remote access?  (Q1=nas|cloud-vm only)
     [1] LAN only — no external access
     [2] Cloudflare Tunnel — requires CF account + domain  [recommended for webhooks]
     [3] Tailscale — private mesh VPN, easy setup, no public webhooks
     [4] Direct TLS — public IP + cert, most control, most complex
     → note for H3: "Tailscale cannot receive public GitHub/CI webhooks"

Q15: Observability?
     [1] None
     [2] Langfuse cloud — free tier 50K events/month  [recommended]
     [3] Langfuse self-hosted — requires Docker + ClickHouse, ~2GB extra RAM
     [4] TokenEye dashboard only  (shown only if TokenEye selected)
     → F3 hidden if Docker unavailable or RAM <4GB

Q16: Secrets management?
     [1] .env file (chmod 600)  [default]
     [2] Vaultwarden self-hosted — Docker, Bitwarden-compatible
     [3] External (HashiCorp Vault, AWS SSM — bring your own)
     → G2 hidden if Docker unavailable

Q17: Search backend?
     [1] Public APIs  [default, zero setup]
     [2] Websurfx — private, Rust, Docker sidecar
     [3] SearXNG — Docker, not available on UGREEN NAS
     → I2/I3 hidden if Docker unavailable
     → I3 hidden if Q3=ugreen

Q18: Persona callsign?  (optional)
     [default: Jarvis]
     → free text, used in SOUL.md + AGENTS.md

Q19: Review and confirm:
     → prints full summary of all selections + derived docker services
     → shows degraded warnings inline
     → [y] to proceed, [n] to restart
```

**Non-interactive mode**: `python param_install.py --config answers.yaml` reads all answers from YAML, validates, skips all prompts, runs constraints + generation + verification. YAML keys map 1:1 to InstallConfig field names. Missing required fields = HARD ERROR with field name listed.

## Config Generation — Exact Mappings Per File

### `~/.mcp.json` — always generated

```python
def generate_mcp_json(config: InstallConfig) -> dict:
    bridge_path = config.repo_root / "param_hermes_mcp.py"
    venv_python = config.venv_python or config.repo_root / ".venv" / "bin" / "python"

    servers = {
        "hermes": {
            "type": "stdio",
            "command": str(venv_python),   # ABSOLUTE path always
            "args": [str(bridge_path)],    # ABSOLUTE path always
            "env": {}
        }
    }
    # Huly added if HULY_API_TOKEN provided
    # No Node.js entry ever generated
    return {"mcpServers": servers}
```

### `~/.hermes/config.yaml` — memory section mapping

```python
MEMORY_CONFIGS = {
    "memory-md":       {"local": {"enabled": True},  "honcho": {"enabled": False}, "mem0": {"enabled": False}},
    "honcho-self":     {"local": {"enabled": True},  "honcho": {"enabled": True,  "base_url": "{honcho_url}"}, "mem0": {"enabled": False}},
    "honcho-cloud":    {"local": {"enabled": True},  "honcho": {"enabled": True,  "base_url": "https://api.honcho.dev"}, "mem0": {"enabled": False}},
    "mem0":            {"local": {"enabled": True},  "honcho": {"enabled": False}, "mem0": {"enabled": True}},
    "honcho-self+mem0":{"local": {"enabled": True},  "honcho": {"enabled": True,  "base_url": "{honcho_url}"}, "mem0": {"enabled": True, "_note": "mem0 is auxiliary only; honcho is primary Hermes provider"}},
    "hindsight":       {"local": {"enabled": True},  "honcho": {"enabled": False}, "mem0": {"enabled": False}, "hindsight": {"enabled": True}},
    "three-layer":     {"local": {"enabled": True},  "honcho": {"enabled": True,  "base_url": "{honcho_url}"}, "mem0": {"enabled": False}, "hindsight": {"enabled": True}},
}
# NOTE: honcho_url = "http://honcho-api:8000" when deployment=nas|cloud-vm (Docker DNS)
#                   "http://localhost:8000"    when deployment=local
```

### `docker-compose.override.yml` — conditional services

```python
CONDITIONAL_SERVICES = {
    "honcho-self":      ["honcho-api", "honcho-deriver", "honcho-db", "honcho-redis"],
    "honcho-self+mem0": ["honcho-api", "honcho-deriver", "honcho-db", "honcho-redis"],
    "three-layer":      ["honcho-api", "honcho-deriver", "honcho-db", "honcho-redis", "hindsight", "pgvector"],
    "hindsight":        ["hindsight", "pgvector"],
    "langfuse-self":    ["langfuse", "clickhouse"],
    "vaultwarden":      ["vaultwarden"],
    "websurfx":         ["websurfx", "redis-ws"],
    "searxng":          ["searxng"],
    "cloudflare":       ["cloudflared"],
}
# All services get:
#   restart: unless-stopped
#   networks: [param-net]
# Network defined: param-net (bridge)
# All inter-service references use Docker service names, never localhost/127.0.0.1
```

## Constraint Rules — Complete Set

21 rules operationalized from the feasibility analysis. Enforced by `constraints.py` after interview, before file generation.

```
RULE-01: deployment=local AND remote != n/a                → HARD ERROR  "Remote access requires always-on deployment (nas or cloud-vm)"
RULE-02: deployment=local AND messaging in [telegram+webhook, all] AND no public ingress  → HARD ERROR  "Webhooks require always-on public ingress"
RULE-03: deployment=local AND messaging != none            → WARN  "Messaging stops when your machine sleeps. Consider nas/cloud-vm for 24/7."
RULE-04: docker_available=False AND memory in [honcho-self, hindsight, three-layer, honcho-self+mem0]  → HARD ERROR  "Selected memory backend requires Docker"
RULE-05: docker_available=False AND secrets=vaultwarden    → HARD ERROR  "Vaultwarden requires Docker"
RULE-06: docker_available=False AND observability=langfuse-self  → HARD ERROR  "Self-hosted Langfuse requires Docker"
RULE-07: docker_available=False AND search in [websurfx, searxng]  → HARD ERROR  "Self-hosted search requires Docker"
RULE-08: nas_hardware=ugreen AND search=searxng            → HARD ERROR  "SearXNG is incompatible with UGREEN NAS kernel"
RULE-09: host_ram_gb < 2 AND observability=langfuse-self   → HARD ERROR  "Langfuse self-hosted requires at minimum 2GB available RAM for ClickHouse"
RULE-10: host_ram_gb < 4 AND observability=langfuse-self   → WARN  "Langfuse self-hosted + ClickHouse may destabilize other containers at <4GB RAM"
RULE-11: provider=ollama AND tokeneye != none              → WARN (auto-fix to none)  "TokenEye adds no value for local Ollama. Setting tokeneye=none."
RULE-12: observability=tokeneye-only AND tokeneye=none     → HARD ERROR  "TokenEye dashboard requires TokenEye to be enabled"
RULE-13: provider in [anthropic, openai, openrouter] AND tokeneye in [2key, 3plus]  → WARN  "TokenEye load balancing only works with opencode-go managed auth. Using passthrough cost-tracking mode only."
RULE-14: messaging in [telegram+webhook, all] AND remote in [lan-only, tailscale, n/a]  → HARD ERROR  "Webhooks require public ingress (cloudflare or direct-tls)"
RULE-15: memory=three-layer AND deployment=cloud-vm        → WARN  "Three-layer memory requires Obsidian installed locally. Verify local Obsidian + vault sync workflow exists."
RULE-16: tokeneye=2key AND len(opencode_keys) < 2         → HARD ERROR  "Two-key TokenEye requires exactly 2 opencode-go API keys"
RULE-17: tokeneye=3plus AND len(opencode_keys) < 3        → HARD ERROR  "Three-plus key TokenEye requires at least 3 opencode-go API keys"
RULE-18: memory in [honcho-self+mem0, three-layer] → INFO  "Hermes supports one active memory.provider. Honcho is primary. Mem0/Hindsight run as auxiliary/sync layers."
RULE-19: venv_python is None OR not venv_python.exists()  → HARD ERROR  "Python venv not found at {repo_root}/.venv. Run: python -m venv .venv && source .venv/bin/activate && pip install mcp pyyaml"
RULE-20: not (repo_root / "param_hermes_mcp.py").exists() → HARD ERROR  "MCP bridge not found. Are you running this from the PARAM repo root?"
RULE-21: python version < (3, 11)                         → HARD ERROR  "Python 3.11+ required"
```

## Idempotency

**Detection**: check for existence of `~/.hermes/config.yaml`, `~/.hermes/.env`, `~/.mcp.json`. If all three exist → existing install detected.

**Modes**:
- **Default**: detect existing install → prompt "Existing installation found. [u]pgrade / [r]epair / [f]resh / [q]uit?"
- `--upgrade`: add newly selected components, preserve existing credentials
- `--repair`: re-generate files from last saved `~/.hermes/param-install-answers.yaml` without re-interviewing
- `--fresh`: overwrite everything, requires explicit confirmation
- `--profile <name>`: apply a canonical profile without full interview

**Backup**: before any write, copy existing file to `~/.hermes/backups/YYYY-MM-DDTHH-MM-SS/`. Keep last 5 backups, prune older.

**Last answers** saved to `~/.hermes/param-install-answers.yaml` after every successful install — enables `--repair`.

## Verification Pass (Post-Generation)

15 checks run after all files are generated. Network checks skipped with `--offline` flag.

```
CHECK-01: YAML syntax — config.yaml parseable                   no-network, 0s    FAIL=abort
CHECK-02: JSON syntax — mcp.json parseable                      no-network, 0s    FAIL=abort
CHECK-03: Python syntax — param_hermes_mcp.py compiles          no-network, 1s    FAIL=abort
CHECK-04: MCP bridge paths — command and args are absolute, exist no-network, 0s  FAIL=abort
CHECK-05: .env permissions — chmod 600                          no-network, 0s    FAIL=warn
CHECK-06: No placeholder values in .env ("your-api-key" etc)    no-network, 0s    FAIL=abort
CHECK-07: No localhost in docker-compose service URLs (if A2/A3) no-network, 0s   FAIL=warn
CHECK-08: Port 8787 available (if TokenEye selected)            no-network, 1s    FAIL=warn
CHECK-09: Docker daemon reachable (if docker_available needed)  no-network, 2s    FAIL=abort
CHECK-10: Hermes binary/module importable                       no-network, 3s    FAIL=warn
CHECK-11: API key format regex (offline)                        no-network, 0s    FAIL=warn
CHECK-12: LLM provider live probe — GET /models or equivalent   network, 5s       FAIL=warn "Install continues but provider may be misconfigured"
CHECK-13: Telegram token validation — GET /bot{token}/getMe    network, 5s       FAIL=warn
CHECK-14: Honcho cloud health — GET {honcho_url}/health         network, 5s       FAIL=warn
CHECK-15: Langfuse cloud reachable — GET langfuse_host          network, 3s       FAIL=warn
```

All network checks are skipped if `--offline` flag passed. Timeout failures produce WARN not ABORT.

---

# Part III — Testing Pyramid

## Test Infrastructure

```
tests/
  installer/
    __init__.py
    conftest.py                    # Shared fixtures: temp dirs, mock configs, sample profiles
    unit/
      test_models.py               # InstallConfig construction, defaults, validation
      test_constraints.py          # RULE-01 through RULE-21 (one test per rule)
      test_env_generator.py        # .env generation per provider/memory/messaging combo
      test_config_generator.py     # config.yaml generation per memory mode
      test_mcp_generator.py        # mcp.json generation (paths, no node stubs)
      test_tokeneye_generator.py   # tokeneye config for 1key/2key/3plus
      test_docker_generator.py     # docker-compose service list per combo
      test_skills_generator.py     # skill whitelist generation
      test_backup.py               # backup creation, pruning, restore
      test_verifier.py             # CHECK-01 through CHECK-15
    functional/
      test_interview.py            # Question flow, input validation, skip logic
      test_constraint_engine.py    # Full constraint check on config objects
      test_generator_pipeline.py   # End-to-end file generation per profile
      test_verifier_functional.py  # Post-generation verification with real temp files
    integration/
      test_full_pipeline.py        # Interview → constraints → generators → verifier
      test_noninteractive_mode.py  # YAML config → constraints → generators → verifier
      test_upgrade_mode.py         # Existing install → backup → regenerate
      test_repair_mode.py          # Saved answers → regenerate without interview
      test_profile_presets.py      # --profile flag for each canonical profile
    e2e/
      test_profile_minimal_local.py
      test_profile_developer_local.py
      test_profile_full_nas.py
      test_profile_cloud_vm_budget.py
      test_profile_cloud_vm_full.py
      test_profile_offline_dev.py
  fixtures/
    profiles/                      # YAML answer files for each canonical profile
      minimal-local.yaml
      developer-local.yaml
      full-nas.yaml
      cloud-vm-budget.yaml
      cloud-vm-full.yaml
      offline-dev.yaml
    expected/                      # Expected output files for each profile
      minimal-local/
        .env
        config.yaml
        mcp.json
      developer-local/
        .env
        config.yaml
        mcp.json
        tokeneye-config.json
      ...
```

**Total**: ~3,200 lines of tests across 22 test files.

## Layer 1 — Unit Tests (~1,200 lines, ~120 tests)

Unit tests verify individual functions in isolation. No file I/O, no network, no subprocess. Each test runs in <100ms.

### `test_models.py` (~15 tests)

| Test | What it verifies |
|------|-----------------|
| `test_default_config` | InstallConfig with all defaults: deployment=local, provider=opencode-go, etc. |
| `test_all_dimensions_set` | InstallConfig with every dimension explicitly set |
| `test_invalid_deployment_mode` | Setting deployment="raspberry-pi" raises TypeError (Literal enforcement) |
| `test_invalid_provider` | Setting provider="groq" raises TypeError |
| `test_opencode_keys_empty_default` | opencode_keys defaults to empty list |
| `test_paths_default_to_home` | hermes_home defaults to ~/.hermes, mcp_json_path to ~/.mcp.json |
| `test_computed_fields_default_false` | requires_docker, docker_available default to False |
| `test_config_from_dict` | InstallConfig constructed from flat dict (YAML loading) |
| `test_config_to_dict` | InstallConfig serialized to flat dict (YAML saving) |
| `test_config_roundtrip` | config → dict → config produces identical object |
| `test_optional_fields_none` | All Optional[str] fields default to None |
| `test_list_fields_factory` | list fields use default_factory (no mutable default bug) |
| `test_path_fields_are_pathlib` | repo_root, hermes_home etc. are Path objects |
| `test_profile_name_optional` | profile_name defaults to None (no preset) |
| `test_upgrade_mode_default_false` | upgrade_mode defaults to False |

### `test_constraints.py` (~25 tests, one per rule + edge cases)

| Test | What it verifies |
|------|-----------------|
| `test_rule_01_local_with_remote` | deployment=local + remote=cloudflare → HARD ERROR |
| `test_rule_01_local_with_na_remote` | deployment=local + remote=n/a → no error |
| `test_rule_02_local_webhook_no_ingress` | deployment=local + messaging=all → HARD ERROR |
| `test_rule_03_local_messaging_warning` | deployment=local + messaging=telegram → WARN (not error) |
| `test_rule_04_no_docker_honcho_self` | docker_available=False + memory=honcho-self → HARD ERROR |
| `test_rule_04_no_docker_memory_md` | docker_available=False + memory=memory-md → no error |
| `test_rule_05_no_docker_vaultwarden` | docker_available=False + secrets=vaultwarden → HARD ERROR |
| `test_rule_06_no_docker_langfuse_self` | docker_available=False + observability=langfuse-self → HARD ERROR |
| `test_rule_07_no_docker_websurfx` | docker_available=False + search=websurfx → HARD ERROR |
| `test_rule_08_ugreen_searxng` | nas_hardware=ugreen + search=searxng → HARD ERROR |
| `test_rule_08_synology_searxng` | nas_hardware=synology + search=searxng → no error |
| `test_rule_09_low_ram_langfuse` | host_ram_gb=1 + observability=langfuse-self → HARD ERROR |
| `test_rule_10_warn_ram_langfuse` | host_ram_gb=3 + observability=langfuse-self → WARN |
| `test_rule_11_ollama_tokeneye_autofix` | provider=ollama + tokeneye=1key → WARN + auto-fix to none |
| `test_rule_12_tokeneye_dashboard_no_tokeneye` | observability=tokeneye-only + tokeneye=none → HARD ERROR |
| `test_rule_13_anthropic_2key_warn` | provider=anthropic + tokeneye=2key → WARN |
| `test_rule_14_webhook_lan_only` | messaging=all + remote=lan-only → HARD ERROR |
| `test_rule_14_webhook_cloudflare` | messaging=all + remote=cloudflare → no error |
| `test_rule_15_three_layer_cloud_vm` | memory=three-layer + deployment=cloud-vm → WARN |
| `test_rule_16_2key_one_key` | tokeneye=2key + opencode_keys=["sk-1"] → HARD ERROR |
| `test_rule_17_3plus_two_keys` | tokeneye=3plus + opencode_keys=["sk-1","sk-2"] → HARD ERROR |
| `test_rule_18_multi_memory_info` | memory=honcho-self+mem0 → INFO message |
| `test_rule_19_no_venv` | venv_python=None → HARD ERROR |
| `test_rule_20_no_bridge` | repo_root has no param_hermes_mcp.py → HARD ERROR |
| `test_rule_21_old_python` | python version (3,10,0) → HARD ERROR |

### `test_env_generator.py` (~12 tests)

| Test | What it verifies |
|------|-----------------|
| `test_env_opencode_go` | .env has OPENCODE_API_KEY, no ANTHROPIC/OPENAI keys |
| `test_env_anthropic` | .env has ANTHROPIC_API_KEY, no OPENCODE/OPENAI keys |
| `test_env_openai` | .env has OPENAI_API_KEY |
| `test_env_openrouter` | .env has OPENROUTER_API_KEY |
| `test_env_ollama` | .env has OLLAMA_BASE_URL, no API keys |
| `test_env_telegram` | .env has TELEGRAM_BOT_TOKEN + TELEGRAM_ALLOWED_USERS |
| `test_env_no_telegram` | .env has no TELEGRAM_* vars |
| `test_env_discord` | .env has DISCORD_BOT_TOKEN |
| `test_env_langfuse` | .env has LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY |
| `test_env_honcho_cloud` | .env has HONCHO_API_KEY |
| `test_env_chmod_600_note` | .env output includes chmod 600 instruction |
| `test_env_no_placeholder_values` | No "your-api-key" or "XXX" in generated .env |

### `test_config_generator.py` (~10 tests)

| Test | What it verifies |
|------|-----------------|
| `test_config_memory_md` | config.yaml has memory.local.enabled=True, honcho.enabled=False |
| `test_config_honcho_self_local` | honcho.base_url=http://localhost:8000 |
| `test_config_honcho_self_nas` | honcho.base_url=http://honcho-api:8000 (Docker DNS) |
| `test_config_honcho_cloud` | honcho.base_url=https://api.honcho.dev |
| `test_config_mem0` | mem0.enabled=True, honcho.enabled=False |
| `test_config_honcho_plus_mem0` | Both enabled, honcho is primary |
| `test_config_three_layer` | honcho + hindsight enabled |
| `test_config_provider_opencode_go` | model.base_url points to TokenEye or opencode.ai |
| `test_config_messaging_telegram` | gateway.platforms.telegram.enabled=True |
| `test_config_yaml_parseable` | Generated YAML is valid (yaml.safe_load succeeds) |

### `test_mcp_generator.py` (~6 tests)

| Test | What it verifies |
|------|-----------------|
| `test_mcp_hermes_server` | mcp.json has "hermes" server with type=stdio |
| `test_mcp_absolute_paths` | command and args are absolute paths (no ~, no relative) |
| `test_mcp_no_node_stubs` | No reference to node/hermes-server/build/index.js |
| `test_mcp_python_command` | command points to .venv/bin/python |
| `test_mcp_bridge_path` | args[0] is param_hermes_mcp.py absolute path |
| `test_mcp_json_parseable` | Generated JSON is valid (json.loads succeeds) |

### `test_tokeneye_generator.py` (~5 tests)

| Test | What it verifies |
|------|-----------------|
| `test_tokeneye_1key` | config has 1 provider entry, stripBasePath=true |
| `test_tokeneye_2key` | config has 2 provider entries for load balancing |
| `test_tokeneye_3plus` | config has 3+ provider entries |
| `test_tokeneye_none` | No tokeneye config file generated |
| `test_tokeneye_stripbasepath_false` | opencode-go entry has stripBasePath=false |

### `test_docker_generator.py` (~8 tests)

| Test | What it verifies |
|------|-----------------|
| `test_docker_honcho_self` | Services: honcho-api, honcho-deriver, honcho-db, honcho-redis |
| `test_docker_three_layer` | Services: honcho-* + hindsight + pgvector |
| `test_docker_langfuse_self` | Services: langfuse + clickhouse |
| `test_docker_vaultwarden` | Services: vaultwarden |
| `test_docker_websurfx` | Services: websurfx + redis-ws |
| `test_docker_network` | All services on param-net bridge network |
| `test_docker_no_localhost_urls` | Inter-service URLs use Docker DNS, not localhost |
| `test_docker_local_deployment` | No docker-compose generated when deployment=local |

### `test_backup.py` (~6 tests)

| Test | What it verifies |
|------|-----------------|
| `test_backup_creation` | Existing files copied to timestamped backup dir |
| `test_backup_pruning` | Old backups (>5) are deleted |
| `test_backup_no_existing` | No backup created when no existing files |
| `test_backup_partial` | Only existing files backed up (missing files skipped) |
| `test_backup_dir_structure` | Backup dir is ~/.hermes/backups/YYYY-MM-DDTHH-MM-SS/ |
| `test_restore_from_backup` | Files restored from backup match originals |

### `test_verifier.py` (~15 tests)

| Test | What it verifies |
|------|-----------------|
| `test_check_01_yaml_valid` | Valid YAML → CHECK-01 passes |
| `test_check_01_yaml_invalid` | Invalid YAML → CHECK-01 fails (abort) |
| `test_check_02_json_valid` | Valid JSON → CHECK-02 passes |
| `test_check_03_python_compiles` | param_hermes_mcp.py compiles → CHECK-03 passes |
| `test_check_04_absolute_paths` | Paths are absolute and exist → CHECK-04 passes |
| `test_check_04_relative_path` | Relative path in mcp.json → CHECK-04 fails |
| `test_check_05_env_permissions` | .env has chmod 600 → CHECK-05 passes |
| `test_check_06_no_placeholders` | No placeholder values → CHECK-06 passes |
| `test_check_06_placeholder_found` | "your-api-key" in .env → CHECK-06 fails |
| `test_check_07_no_localhost_docker` | No localhost in docker-compose URLs → CHECK-07 passes |
| `test_check_09_docker_reachable` | Docker daemon socket exists → CHECK-09 passes |
| `test_check_11_api_key_format` | API key matches expected regex → CHECK-11 passes |
| `test_check_11_bad_api_key` | API key doesn't match regex → CHECK-11 warns |
| `test_check_offline_skip` | --offline flag skips all network checks |
| `test_check_timeout_warns` | Network check timeout → WARN (not abort) |

## Layer 2 — Functional Tests (~700 lines, ~40 tests)

Functional tests verify module behavior with real file I/O in temporary directories. No network. Each test runs in <500ms.

### `test_interview.py` (~15 tests)

| Test | What it verifies |
|------|-----------------|
| `test_interview_minimal_local` | Q1-Q19 flow for Minimal-Local profile via stdin |
| `test_interview_developer_local` | Q1-Q19 flow for Developer-Local profile |
| `test_interview_full_nas` | Q1-Q19 flow for Full-NAS profile |
| `test_interview_q3_nas_only` | Q3 (NAS hardware) only shown when Q1=nas |
| `test_interview_q6_opencode_only` | Q6 (key count) only shown when Q5=opencode-go |
| `test_interview_q8_non_opencode` | Q8 (TokenEye passthrough) only for non-opencode providers |
| `test_interview_q14_remote_only` | Q14 (remote access) only when Q1=nas|cloud-vm |
| `test_interview_skip_docker_options` | Docker-dependent options hidden when Q2=n |
| `test_interview_q12_telegram_validation` | Invalid token format → re-prompt |
| `test_interview_q13_user_id_numeric` | Non-numeric user ID → re-prompt |
| `test_interview_q19_confirm` | Review summary shows all selections + warnings |
| `test_interview_q19_restart` | [n] at Q19 restarts interview from Q1 |
| `test_interview_q18_custom_callsign` | Custom callsign propagates to SOUL.md/AGENTS.md |
| `test_interview_q18_default_callsign` | Default "Jarvis" used when blank |
| `test_interview_warning_display` | Degraded warnings shown inline at Q19 |

### `test_constraint_engine.py` (~10 tests)

| Test | What it verifies |
|------|-----------------|
| `test_constraints_all_pass` | Valid config → no errors, no warnings |
| `test_constraints_hard_error_aborts` | RULE-01 violation → raises ConstraintError |
| `test_constraints_warning_continues` | RULE-03 warning → adds to degraded_warnings, continues |
| `test_constraints_autofix_applied` | RULE-11 auto-fix → tokeneye changed to none |
| `test_constraints_info_logged` | RULE-18 info → logged but no behavior change |
| `test_constraints_multiple_errors` | Multiple HARD ERRORs → all collected and reported |
| `test_constraints_multiple_warnings` | Multiple WARNs → all collected, install continues |
| `test_constraints_computed_fields` | After constraints: requires_docker, docker_services populated |
| `test_constraints_docker_services_list` | Correct service list derived from memory + obs + search + secrets |
| `test_constraints_no_docker_no_docker_services` | docker_available=False → docker_services empty |

### `test_generator_pipeline.py` (~10 tests)

| Test | What it verifies |
|------|-----------------|
| `test_generate_minimal_local` | Generates .env + config.yaml + mcp.json for Minimal-Local |
| `test_generate_developer_local` | Generates .env + config.yaml + mcp.json + tokeneye config |
| `test_generate_full_nas` | Generates all files + docker-compose.override.yml |
| `test_generate_offline_dev` | Generates minimal .env (no API keys) + config.yaml |
| `test_generate_files_exist` | All expected output files created in temp dir |
| `test_generate_no_orphan_files` | No unexpected files generated |
| `test_generate_file_permissions` | .env has 0600 permissions |
| `test_generate_config_yaml_valid` | Generated config.yaml parses as valid YAML |
| `test_generate_mcp_json_valid` | Generated mcp.json parses as valid JSON |
| `test_generate_answers_saved` | param-install-answers.yaml saved with all selections |

### `test_verifier_functional.py` (~5 tests)

| Test | What it verifies |
|------|-----------------|
| `test_verifier_all_pass_minimal` | All 15 checks pass for Minimal-Local profile |
| `test_verifier_all_pass_full_nas` | All 15 checks pass for Full-NAS profile |
| `test_verifier_offline_mode` | --offline skips CHECK-12/13/14/15 |
| `test_verifier_aborts_on_critical` | CHECK-01 failure → aborts generation |
| `test_verifier_warns_on_non_critical` | CHECK-05 failure → warns but continues |

## Layer 3 — Integration Tests (~600 lines, ~20 tests)

Integration tests verify cross-module interactions. Real file I/O in temp dirs. No network (mocked). Each test runs in <2s.

### `test_full_pipeline.py` (~6 tests)

| Test | What it verifies |
|------|-----------------|
| `test_pipeline_interactive_minimal` | stdin answers → interview → constraints → generators → verifier |
| `test_pipeline_interactive_full_nas` | Full NAS profile through complete pipeline |
| `test_pipeline_all_profiles` | Parametrized: all 6 profiles through complete pipeline |
| `test_pipeline_constraint_failure_aborts` | Constraint HARD ERROR → pipeline aborts before generation |
| `test_pipeline_verifier_failure_aborts` | Verifier CHECK-01 failure → pipeline reports error |
| `test_pipeline_backup_before_overwrite` | Existing files backed up before new files written |

### `test_noninteractive_mode.py` (~5 tests)

| Test | What it verifies |
|------|-----------------|
| `test_yaml_config_minimal` | --config minimal-local.yaml → full pipeline, no prompts |
| `test_yaml_config_full_nas` | --config full-nas.yaml → full pipeline, no prompts |
| `test_yaml_missing_required_field` | YAML missing "provider" → HARD ERROR with field name |
| `test_yaml_invalid_value` | YAML with provider="groq" → HARD ERROR |
| `test_yaml_all_profiles` | Parametrized: all 6 profile YAMLs through pipeline |

### `test_upgrade_mode.py` (~4 tests)

| Test | What it verifies |
|------|-----------------|
| `test_upgrade_adds_component` | Existing minimal install + upgrade to add TokenEye |
| `test_upgrade_preserves_credentials` | Existing API keys preserved during upgrade |
| `test_upgrade_backup_created` | Upgrade creates backup before writing |
| `test_upgrade_answers_updated` | param-install-answers.yaml reflects new selections |

### `test_repair_mode.py` (~3 tests)

| Test | What it verifies |
|------|-----------------|
| `test_repair_from_saved_answers` | --repair reads saved answers, regenerates all files |
| `test_repair_no_interview` | --repair does not prompt any questions |
| `test_repair_missing_answers` | --repair with no saved answers → HARD ERROR |

### `test_profile_presets.py` (~6 tests)

| Test | What it verifies |
|------|-----------------|
| `test_profile_minimal_local` | --profile minimal-local → correct InstallConfig |
| `test_profile_developer_local` | --profile developer-local → correct InstallConfig |
| `test_profile_full_nas` | --profile full-nas → correct InstallConfig |
| `test_profile_cloud_vm_budget` | --profile cloud-vm-budget → correct InstallConfig |
| `test_profile_cloud_vm_full` | --profile cloud-vm-full → correct InstallConfig |
| `test_profile_offline_dev` | --profile offline-dev → correct InstallConfig |

## Layer 4 — E2E Tests (~700 lines, ~18 tests)

E2E tests verify the full installer workflow end-to-end per canonical profile. Each test runs `param_install.py` as a subprocess with a profile YAML, then validates every generated file against expected output. Each test runs in <5s.

### `test_profile_minimal_local.py` (~3 tests)

| Test | What it verifies |
|------|-----------------|
| `test_e2e_minimal_local_files` | Generated files match expected/ minimal-local/ fixtures |
| `test_e2e_minimal_local_no_docker` | No docker-compose.override.yml generated |
| `test_e2e_minimal_local_no_tokeneye` | No tokeneye-config.json generated |

### `test_profile_developer_local.py` (~3 tests)

| Test | What it verifies |
|------|-----------------|
| `test_e2e_developer_local_files` | Generated files match expected/ developer-local/ fixtures |
| `test_e2e_developer_local_tokeneye` | tokeneye-config.json has 2 API keys |
| `test_e2e_developer_local_honcho_cloud` | config.yaml has honcho.base_url=api.honcho.dev |

### `test_profile_full_nas.py` (~4 tests)

| Test | What it verifies |
|------|-----------------|
| `test_e2e_full_nas_files` | Generated files match expected/ full-nas/ fixtures |
| `test_e2e_full_nas_docker_services` | docker-compose has honcho-* + vaultwarden + websurfx + cloudflared |
| `test_e2e_full_nas_docker_dns` | No localhost in docker-compose service URLs |
| `test_e2e_full_nas_cloudflare_config` | cloudflared config references correct tunnel name + domain |

### `test_profile_cloud_vm_budget.py` (~3 tests)

| Test | What it verifies |
|------|-----------------|
| `test_e2e_cloud_vm_budget_files` | Generated files match expected/ cloud-vm-budget/ fixtures |
| `test_e2e_cloud_vm_budget_tailscale` | No cloudflared service in docker-compose |
| `test_e2e_cloud_vm_budget_openrouter` | .env has OPENROUTER_API_KEY, no OPENCODE/ANTHROPIC |

### `test_profile_cloud_vm_full.py` (~3 tests)

| Test | What it verifies |
|------|-----------------|
| `test_e2e_cloud_vm_full_files` | Generated files match expected/ cloud-vm-full/ fixtures |
| `test_e2e_cloud_vm_full_three_layer` | docker-compose has honcho-* + hindsight + pgvector |
| `test_e2e_cloud_vm_full_3key_tokeneye` | tokeneye-config.json has 3 API keys |

### `test_profile_offline_dev.py` (~2 tests)

| Test | What it verifies |
|------|-----------------|
| `test_e2e_offline_dev_files` | Generated files match expected/ offline-dev/ fixtures |
| `test_e2e_offline_dev_no_api_keys` | .env has no API key variables (Ollama is local) |

## CI Matrix

### GitHub Actions Workflow

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-latest, macos-latest]
    python-version: ["3.11", "3.12", "3.13"]
    profile:
      - minimal-local
      - developer-local
      - full-nas
      - cloud-vm-budget
      - cloud-vm-full
      - offline-dev

jobs:
  unit-tests:
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install pyyaml pytest pytest-cov
      - run: python -m pytest tests/installer/unit/ -v --cov=installer --cov-report=xml

  functional-tests:
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install pyyaml pytest
      - run: python -m pytest tests/installer/functional/ -v

  integration-tests:
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install pyyaml pytest
      - run: python -m pytest tests/installer/integration/ -v

  e2e-tests:
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install pyyaml pytest
      - run: python -m pytest tests/installer/e2e/test_profile_${{ matrix.profile }}.py -v
```

### Coverage Requirements

| Layer | Minimum Coverage |
|-------|-----------------|
| `models.py` | 100% |
| `constraints.py` | 100% (every RULE tested) |
| `generators/*.py` | 95% |
| `interview.py` | 90% (stdin mocking complexity) |
| `verifier.py` | 95% |
| `backup.py` | 100% |
| **Overall** | 95% |

### Test Execution Order

```
1. Unit tests (fastest, most specific)        ~120 tests, <30s total
2. Functional tests (real file I/O)            ~40 tests, <20s total
3. Integration tests (cross-module)            ~20 tests, <40s total
4. E2E tests (full pipeline per profile)       ~18 tests, <90s total
                                               ─────────────────────
                                               ~198 tests, <3min total
```

---

# Implementation Plan

## Build Order (Sequential — each step depends on the previous)

| Step | Module | Lines | Tests | Depends On |
|------|--------|-------|-------|------------|
| 1 | `models.py` | ~120 | `test_models.py` (~15 tests) | — |
| 2 | `constraints.py` | ~160 | `test_constraints.py` (~25 tests) | Step 1 |
| 3 | `generators/env_generator.py` | ~100 | `test_env_generator.py` (~12 tests) | Step 1 |
| 4 | `generators/config_generator.py` | ~140 | `test_config_generator.py` (~10 tests) | Step 1 |
| 5 | `generators/mcp_generator.py` | ~80 | `test_mcp_generator.py` (~6 tests) | Step 1 |
| 6 | `generators/tokeneye_generator.py` | ~70 | `test_tokeneye_generator.py` (~5 tests) | Step 1 |
| 7 | `generators/docker_generator.py` | ~150 | `test_docker_generator.py` (~8 tests) | Step 1 |
| 8 | `generators/skills_generator.py` | ~60 | `test_skills_generator.py` (~4 tests) | Step 1 |
| 9 | `backup.py` | ~80 | `test_backup.py` (~6 tests) | Step 1 |
| 10 | `verifier.py` | ~120 | `test_verifier.py` (~15 tests) | Steps 3-8 |
| 11 | `interview.py` | ~180 | `test_interview.py` (~15 tests) | Steps 1-2 |
| 12 | `generators/__init__.py` | ~60 | — | Steps 3-8 |
| 13 | `param_install.py` (entry point) | ~80 | — | Steps 1-12 |
| 14 | E2E tests + fixtures | ~700 | ~18 tests | Steps 1-13 |

## Parallelizable Work

Steps 3-9 can be built in parallel (all depend only on Step 1). Steps 10-11 can be built in parallel after Steps 2-9. This allows up to 7 parallel agents during the generator phase.

## Estimated Effort

| Phase | Effort | Parallelizable? |
|-------|--------|-----------------|
| Steps 1-2 (models + constraints) | 1 hour | No (sequential) |
| Steps 3-9 (7 generators + backup) | 3 hours (parallel: ~30min) | Yes (7 agents) |
| Steps 10-11 (verifier + interview) | 1.5 hours | Yes (2 agents) |
| Steps 12-13 (orchestrator + entry) | 1 hour | No |
| Step 14 (E2E + fixtures) | 2 hours | Partially (6 profile tests in parallel) |
| **Total (sequential)** | **~8.5 hours** | |
| **Total (max parallel)** | **~3 hours** | |

## Prerequisites for Building

1. The PARAM repo must be at the path where the installer will run (needs `param_hermes_mcp.py`)
2. Python 3.11+ with PyYAML installed
3. The 6 canonical profile YAML fixtures must be written first (they serve as both test inputs and documentation)
4. The expected output fixtures must be hand-verified for each profile before E2E tests can pass

## What This Spec Does NOT Cover (Out of Scope)

- **Actual NAS deployment execution** — the installer generates config files; it does not run `docker compose up`
- **Cloudflare tunnel setup** — the installer generates cloudflared config; the user runs `cloudflared tunnel login` manually
- **Obsidian vault creation** — for three-layer memory, the user must have Obsidian installed and a vault configured
- **Ollama model installation** — for offline-dev, the user must `ollama pull` models separately
- **Hermes binary installation** — the installer verifies Hermes exists but does not install it
- **OMO/opencode installation** — the installer verifies OMO exists but does not install it

These are documented in `INSTALL.md` as manual prerequisites. The installer checks for them during verification (CHECK-09, CHECK-10) but does not perform the installation.

---

## Appendix A — Profile YAML Fixtures (Reference)

### `minimal-local.yaml`
```yaml
deployment: local
provider: anthropic
tokeneye: none
memory: memory-md
messaging: none
observability: none
secrets: env-file
remote: n/a
search: public
anthropic_key: sk-ant-test-key
primary_model: claude-sonnet-4-5
```

### `developer-local.yaml`
```yaml
deployment: local
provider: opencode-go
tokeneye: 2key
memory: honcho-cloud
messaging: telegram
observability: langfuse-cloud
secrets: env-file
remote: n/a
search: public
opencode_keys: ["sk-test-1", "sk-test-2"]
telegram_token: "123456789:AAEhBP0v-test-token-35-chars-long-x"
telegram_user_ids: ["123456789"]
honcho_api_key: "honcho-test-key"
langfuse_public_key: "pk-lf-test"
langfuse_secret_key: "sk-lf-test"
primary_model: kimi-k2.5
```

### `full-nas.yaml`
```yaml
deployment: nas
provider: opencode-go
tokeneye: 2key
memory: honcho-self
messaging: telegram+discord
observability: langfuse-cloud
secrets: vaultwarden
remote: cloudflare
search: websurfx
nas_hardware: generic
host_ram_gb: 8
opencode_keys: ["sk-test-1", "sk-test-2"]
telegram_token: "123456789:AAEhBP0v-test-token-35-chars-long-x"
telegram_user_ids: ["123456789"]
discord_token: "discord-test-token"
langfuse_public_key: "pk-lf-test"
langfuse_secret_key: "sk-lf-test"
cloudflare_tunnel_name: "param"
cloudflare_domain: "example.com"
primary_model: kimi-k2.5
```

### `cloud-vm-budget.yaml`
```yaml
deployment: cloud-vm
provider: openrouter
tokeneye: none
memory: honcho-cloud
messaging: telegram
observability: langfuse-cloud
secrets: env-file
remote: tailscale
search: public
host_ram_gb: 4
openrouter_key: "sk-or-test-key"
telegram_token: "123456789:AAEhBP0v-test-token-35-chars-long-x"
telegram_user_ids: ["123456789"]
honcho_api_key: "honcho-test-key"
langfuse_public_key: "pk-lf-test"
langfuse_secret_key: "sk-lf-test"
primary_model: anthropic/claude-sonnet-4.5
```

### `cloud-vm-full.yaml`
```yaml
deployment: cloud-vm
provider: opencode-go
tokeneye: 3plus
memory: three-layer
messaging: all
observability: langfuse-cloud
secrets: vaultwarden
remote: cloudflare
search: websurfx
host_ram_gb: 16
opencode_keys: ["sk-test-1", "sk-test-2", "sk-test-3"]
telegram_token: "123456789:AAEhBP0v-test-token-35-chars-long-x"
telegram_user_ids: ["123456789"]
discord_token: "discord-test-token"
webhook_secret: "webhook-test-secret"
langfuse_public_key: "pk-lf-test"
langfuse_secret_key: "sk-lf-test"
cloudflare_tunnel_name: "param"
cloudflare_domain: "example.com"
primary_model: kimi-k2.5
```

### `offline-dev.yaml`
```yaml
deployment: local
provider: ollama
tokeneye: none
memory: memory-md
messaging: none
observability: none
secrets: env-file
remote: n/a
search: public
ollama_base_url: "http://localhost:11434"
primary_model: llama3.2
```

---

## Appendix B — Constraint-to-Test Cross-Reference

| Constraint Rule | Unit Test | E2E Profile(s) that exercise it |
|-----------------|-----------|-------------------------------|
| RULE-01 (local + remote) | `test_rule_01_*` | Minimal-Local, Developer-Local, Offline-Dev (remote=n/a) |
| RULE-02 (local + webhook) | `test_rule_02_*` | Minimal-Local (messaging=none) |
| RULE-03 (local + messaging warn) | `test_rule_03_*` | Developer-Local (messaging=telegram) |
| RULE-04 (no Docker + memory) | `test_rule_04_*` | Minimal-Local, Offline-Dev (memory=memory-md) |
| RULE-05 (no Docker + vaultwarden) | `test_rule_05_*` | Minimal-Local (secrets=env-file) |
| RULE-06 (no Docker + langfuse-self) | `test_rule_06_*` | All profiles use langfuse-cloud or none |
| RULE-07 (no Docker + search) | `test_rule_07_*` | Minimal-Local (search=public) |
| RULE-08 (UGREEN + SearXNG) | `test_rule_08_*` | Full-NAS (nas_hardware=generic) |
| RULE-09 (RAM<2GB + langfuse-self) | `test_rule_09_*` | Not in profiles (all use cloud) |
| RULE-10 (RAM<4GB + langfuse-self) | `test_rule_10_*` | Not in profiles (all use cloud) |
| RULE-11 (ollama + tokeneye autofix) | `test_rule_11_*` | Offline-Dev (provider=ollama, tokeneye=none) |
| RULE-12 (tokeneye-only + no tokeneye) | `test_rule_12_*` | Minimal-Local (obs=none, tokeneye=none) |
| RULE-13 (non-opencode + 2key) | `test_rule_13_*` | Cloud-VM-Budget (provider=openrouter, tokeneye=none) |
| RULE-14 (webhook + no public ingress) | `test_rule_14_*` | Cloud-VM-Full (messaging=all, remote=cloudflare) |
| RULE-15 (three-layer + cloud-vm) | `test_rule_15_*` | Cloud-VM-Full (memory=three-layer) |
| RULE-16 (2key + <2 keys) | `test_rule_16_*` | Developer-Local, Full-NAS (2 keys provided) |
| RULE-17 (3plus + <3 keys) | `test_rule_17_*` | Cloud-VM-Full (3 keys provided) |
| RULE-18 (multi-memory info) | `test_rule_18_*` | Not in profiles (none use multi-memory) |
| RULE-19 (no venv) | `test_rule_19_*` | All profiles (venv exists in test env) |
| RULE-20 (no bridge) | `test_rule_20_*` | All profiles (bridge exists in repo) |
| RULE-21 (old Python) | `test_rule_21_*` | All profiles (Python 3.11+ in CI) |

---

*This spec is the cold-start context for the Generic-PARAM installer build session. No additional research is needed — implementation can begin immediately from Step 1 of the Implementation Plan.*
