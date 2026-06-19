# PARAM Hermes Core Patches

**Phase 6.3 deliverable — analysis of patches needed for PARAM-specific behavior.**

## Patch Inventory

### P1 — Skills Whitelist (`prompt_builder.py` + `skill_utils.py`)
- **Current**: All 67 skills loaded into every session
- **Fix**: Add `skills.include` config key (mirrors existing `skills.disabled`)
- **Files**: `agent/prompt_builder.py:build_skills_system_prompt()`, `agent/skill_utils.py`
- **Lines**: ~15 lines to add
- **Workaround**: Inverse whitelist via `skills.disabled` (already deployed)

### P2 — Container-Aware Paths (`hermes_constants.py`)
- **Current**: Some paths hardcoded for `~/.hermes/` which don't exist in Docker
- **Fix**: Use `HERMES_HOME` env var consistently for all path lookups
- **Files**: `hermes_constants.py`
- **Impact**: Makes param-status.sh and other scripts work in Docker

### P3 — TokenEye OpenAI-Compatible Routing
- **Current**: Model provider defaults may not route through OpenAI-compatible endpoints
- **Fix**: Ensure all model providers can use `base_url` override
- **Files**: Model provider plugins
- **Status**: Already working via config (opencode-go → TokenEye)

## Bind-Mount Patch System

```
docker-compose.yml:
  volumes:
    - ./patches/prompt_builder.py:/opt/hermes/agent/prompt_builder.py:ro
    - ./patches/skill_utils.py:/opt/hermes/agent/skill_utils.py:ro
```

Each patch is version-controlled in `deploy/nas/patches/`.
Survives Hermes Docker image updates.
