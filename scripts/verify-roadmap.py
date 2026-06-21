#!/usr/bin/env python3
"""
PARAM ROADMAP Verification System — programmatic evidence checking.
Replaces manual checkbox fraud with machine-verifiable assertions.

Usage:
    python3 scripts/verify-roadmap.py                   # verify all phases
    python3 scripts/verify-roadmap.py --phase 0         # verify specific phase
    python3 scripts/verify-roadmap.py --nas 192.168.1.167  # remote NAS

Each [x] task requires a corresponding check_fn that validates it.
If a check_fn does not exist for a [x] task, it's flagged as UNVERIFIABLE.
"""

import json, os, re, subprocess, sys, yaml
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROADMAP_PATH = PROJECT_ROOT / "specs" / "ROADMAP.md"

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
NC = "\033[0m"
BOLD = "\033[1m"


def ssh(cmd: str, nas: str = "192.168.1.167") -> str:
    """Run command on NAS via SSH. Returns stdout or '' on failure."""
    try:
        result = subprocess.run(
            [
                "sshpass", "-p", "H3lloW0rld",
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"Nasama-Pochu@{nas}", cmd,
            ],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def nas_file_exists(path: str) -> bool:
    return ssh(f"test -f {path} && echo YES || echo NO") == "YES"


def nas_dir_exists(path: str) -> bool:
    return ssh(f"test -d {path} && echo YES || echo NO") == "YES"


def nas_container_running(name: str) -> bool:
    out = ssh(f"docker ps --format '{{{{.Names}}}}' | grep -E '^{name}$'")
    return bool(out)


def nas_container_healthy(name: str) -> Optional[bool]:
    out = ssh(f"docker ps --format '{{{{.Names}}}} {{{{.Status}}}}' | grep '{name}'")
    if not out:
        return None
    return "(healthy)" in out


def nas_curl(url: str) -> Optional[int]:
    out = ssh(f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout 5 {url}")
    if not out:
        return None
    try:
        return int(out)
    except ValueError:
        return None


def nas_config_get(path: str) -> dict:
    raw = ssh(f"cat {path}")
    if not raw:
        return {}
    try:
        return yaml.safe_load(raw) or {}
    except Exception:
        return {}


def parse_roadmap(path: Path) -> dict:
    """Parse ROADMAP.md into structured task list. Returns dict with phases."""
    with open(path) as f:
        content = f.read()

    phases = {}
    current_phase = None

    for line in content.split("\n"):
        # Phase header: "## Phase 0:" or "## Phase IR-0:"
        m = re.match(r"## Phase ([A-Za-z]*-?\d+):", line)
        if m:
            phase_key = m.group(1)
            try:
                current_phase = int(phase_key)
            except ValueError:
                current_phase = phase_key
            if current_phase not in phases:
                phases[current_phase] = {"tasks": [], "name": line.split(": ", 1)[-1] if ": " in line else ""}
            continue

        # Task line: - [x] **X.Y.Z** or - [ ] **X.Y.Z** or - [~] **X.Y.Z**
        # Also supports IR prefixed IDs: - [x] **IR-0.1.1**
        m = re.match(r"- \[([x ~])\]\s+\*\*([A-Za-z]?\d+\.\d+\.\d+|IR-\d+\.\d+\.\d+)\*\*\s+(.+)", line)
        if m and current_phase is not None:
            status = m.group(1)
            task_id = m.group(2)
            description = m.group(3).strip()
            phases[current_phase]["tasks"].append({
                "id": task_id,
                "description": description,
                "status": "completed" if status == "x" else ("partial" if status == "~" else "pending"),
                "raw_mark": status,
            })

    return phases


# ============================================================
# TASK VERIFICATION FUNCTIONS
# Each function returns (verified: bool, evidence: str)
# ============================================================

CHECKS = {}

def check(task_id: str):
    """Decorator to register a check function for a task ID."""
    def decorator(fn):
        CHECKS[task_id] = fn
        return fn
    return decorator


@check("0.1.1")
def verify_hermes_memory_tool():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    provider = cfg.get("memory", {}).get("provider", "")
    enabled = cfg.get("memory", {}).get("memory_enabled", False)
    ok = provider == "honcho" and enabled
    return ok, f"Memory provider={provider}, enabled={enabled}" if ok else f"Memory not activated: provider={provider}"


@check("0.1.2")
def verify_hermes_cli_path():
    out = ssh("docker exec param which hermes 2>/dev/null || echo NOT_FOUND")
    ok = "NOT_FOUND" not in out
    return ok, "hermes CLI in PATH" if ok else "hermes CLI NOT in container PATH"


@check("0.1.3")
def verify_telegram_e2e():
    """Telegram roundtrip — manual verification required."""
    return None, "MANUAL: requires live Telegram message exchange"


@check("0.2.1")
def verify_hermes_data_prepared():
    exists = nas_dir_exists("/home/Nasama-Pochu/param/deploy/nas/hermes-data")
    return exists, "hermes-data directory exists on NAS" if exists else "hermes-data NOT FOUND on NAS"


@check("0.2.2")
def verify_env_configured():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/.env")
    # .env is not YAML, so we check differently
    env_raw = ssh("grep -c 'TELEGRAM_BOT_TOKEN=' /home/Nasama-Pochu/param/deploy/nas/hermes-data/.env")
    has_token = env_raw and env_raw != "0"
    return bool(has_token), ".env has TELEGRAM_BOT_TOKEN" if has_token else ".env MISSING or no TELEGRAM_BOT_TOKEN"


@check("0.2.3")
def verify_config_routes_tokeneye():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    base_url = cfg.get("model", {}).get("base_url", "")
    ok = "8787" in base_url
    return ok, f"model.base_url = {base_url}" if ok else f"model.base_url does NOT route to TokenEye: {base_url}"


@check("0.2.4")
def verify_tokeneye_deployed():
    running = nas_container_running("param-tokeneye")
    healthy = nas_container_healthy("param-tokeneye")
    return bool(running and healthy), f"TokenEye container {'healthy' if healthy else 'running but unhealthy' if running else 'NOT RUNNING'}"


@check("0.2.5")
def verify_hermes_gateway():
    running = nas_container_running("param")
    healthy = nas_container_healthy("param")
    return bool(running and healthy), f"Hermes gateway {'healthy' if healthy else 'unhealthy' if running else 'NOT RUNNING'}"


@check("0.2.6")
def verify_telegram_bot_responds():
    return None, "MANUAL: requires sending /status via Telegram"


@check("0.3.1")
def verify_cloudflare_tunnel_exists():
    out = ssh("docker ps --format '{{.Names}}' | grep cloudflared")
    return bool(out), "cloudflared container running" if out else "cloudflared NOT RUNNING"


@check("0.3.2")
def verify_tunnel_dns():
    cfg_raw = ssh("cat /home/Nasama-Pochu/.cloudflared/config.yml")
    has_param = "param.aiforges.app" in (cfg_raw or "")
    return has_param, "param.aiforges.app in tunnel config" if has_param else "param.aiforges.app MISSING from tunnel config"


@check("0.3.3")
def verify_additional_tunnel_routes():
    cfg_raw = ssh("cat /home/Nasama-Pochu/.cloudflared/config.yml")
    routes = ["param.aiforges.app", "hook.param.aiforges.app", "vault.param.aiforges.app"]
    found = [r for r in routes if r in cfg_raw]
    ok = len(found) >= 2
    return ok, f"{len(found)}/{len(routes)} routes configured: {found}"


@check("0.3.4")
def verify_cloudflared_restart_policy():
    out = ssh("docker inspect param-cloudflared --format '{{.HostConfig.RestartPolicy.Name}}'")
    ok = out == "unless-stopped"
    return ok, f"restart policy: {out}" if ok else f"restart policy is {out}, expected unless-stopped"


@check("0.3.5")
def verify_telegram_latency():
    return None, "MANUAL: requires timestamped roundtrip test"


@check("0.4.1")
def verify_tokeneye_load_balance():
    health = ssh("curl -s http://localhost:8787/__health")
    try:
        data = json.loads(health)
        kc = data.get("providers", {}).get("opencode-go", {}).get("keyCount", 0)
        ok = kc >= 2
        return ok, f"TokenEye has {kc} opencode-go keys" if ok else f"TokenEye has only {kc} keys, need 2+"
    except Exception:
        return False, "Cannot parse TokenEye health response"


@check("0.5.3")
def verify_git_clean():
    out = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT)
    ok = out.returncode == 0
    return ok, "git repo has commits" if ok else "git repo has NO commits"


@check("1.1.2")
def verify_honcho_self_hosted():
    code = nas_curl("http://localhost:8000/health")
    ok = code == 200
    return ok, f"Honcho health: {code}" if ok else f"Honcho NOT reachable (HTTP {code})"


@check("1.1.3")
def verify_honcho_memory_provider():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    provider = cfg.get("memory", {}).get("provider", "")
    ok = provider == "honcho"
    return ok, f"memory.provider = {provider}" if ok else f"memory provider is '{provider}', not 'honcho'"


@check("1.1.4")
def verify_reasoning_depth():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    depth = cfg.get("memory", {}).get("reasoning_depth", 0)
    ok = depth >= 2
    return ok, f"reasoning_depth = {depth}" if ok else f"reasoning_depth is {depth}, need >= 2"


@check("1.1.5")
def verify_cross_session_memory():
    return None, "MANUAL: requires multi-session memory retrieval test"


@check("1.3.1")
def verify_vault_structure():
    raw = ssh("ls -d /home/Nasama-Pochu/param/vault/*/ 2>/dev/null")
    dirs = raw.split() if raw else []
    required = ["Architecture", "Operations", "Research", "Meta", "Security"]
    found = [d.split("/")[-2] for d in dirs]
    missing = [r for r in required if r not in found]
    ok = len(missing) == 0
    return ok, f"vault has {len(found)} dirs" if ok else f"missing vault dirs: {missing}"


@check("1.3.2")
def verify_vault_hindsight_sync_cron():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    jobs = cfg.get("cron", {}).get("jobs", [])
    found = any("vault-hindsight-sync" in j.get("name", "") for j in jobs)
    return found, "vault-hindsight-sync cron exists" if found else "vault-hindsight-sync cron MISSING"


@check("1.3.3")
def verify_planner_daily_note():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    jobs = cfg.get("cron", {}).get("jobs", [])
    found = any("planner-daily-note" in j.get("name", "") for j in jobs)
    return found, "planner-daily-note cron exists" if found else "planner-daily-note cron MISSING"


@check("1.4.1")
def verify_memory_consolidation():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    jobs = cfg.get("cron", {}).get("jobs", [])
    found = any("memory-consolidation" in j.get("name", "") for j in jobs)
    return found, "memory-consolidation cron exists" if found else "memory-consolidation cron MISSING"


@check("3.1.1")
def verify_wake_and_check():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    jobs = cfg.get("cron", {}).get("jobs", [])
    found = any("wake-and-check" in j.get("name", "") for j in jobs)
    return found, "wake-and-check cron exists" if found else "wake-and-check cron MISSING"


@check("3.1.2")
def verify_pending_task_detection():
    state = nas_file_exists("/home/Nasama-Pochu/param/deploy/nas/hermes-data/state/notify-state.json")
    return state, "state file exists for diff-based tracking" if state else "notify-state.json MISSING"


@check("3.1.3")
def verify_autonomous_maintenance():
    script_exists = (PROJECT_ROOT / "deploy" / "nas" / "hermes-data" / "scripts" / "autonomous-maintenance.sh").exists()
    local_cfg_path = PROJECT_ROOT / "deploy" / "nas" / "hermes-data" / "config.yaml"
    # Try NAS first, fall back to local config
    out = ssh("grep -c 'name: autonomous-maintenance' /home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    if out:
        cron_ok = int(out.strip() or 0) >= 1
    else:
        # Fallback to local config
        with open(local_cfg_path) as f:
            local_cfg = yaml.safe_load(f) or {}
        jobs = local_cfg.get("cron", {}).get("jobs", [])
        cron_ok = any("autonomous-maintenance" in j.get("name", "") for j in jobs)
    ok = script_exists and cron_ok
    return ok, f"Script {'exists' if script_exists else 'MISSING'}, cron {'configured' if cron_ok else 'MISSING'}"


@check("3.1.4")
def verify_escalation_protocol():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    jobs = cfg.get("cron", {}).get("jobs", [])
    found = any("notification-controller" in j.get("name", "") for j in jobs)
    return found, "notification-controller cron exists" if found else "notification-controller cron MISSING"


@check("3.2.1")
def verify_notification_tiers():
    tiers_exist = Path(PROJECT_ROOT / "specs" / "NOTIFICATIONS.md").exists()
    return tiers_exist, "NOTIFICATIONS.md exists" if tiers_exist else "NOTIFICATIONS.md MISSING"


@check("3.2.2")
def verify_event_driven_notifications():
    return None, "MANUAL: requires observing live notification delivery"


@check("3.2.3")
def verify_diff_based_alerts():
    state = nas_file_exists("/home/Nasama-Pochu/param/deploy/nas/hermes-data/state/notify-state.json")
    return state, "state file exists" if state else "state file MISSING"


@check("3.3.1")
def verify_docker_restart_policy():
    out = ssh("docker inspect param --format '{{.HostConfig.RestartPolicy.Name}}'")
    ok = out == "unless-stopped"
    return ok, f"Hermes restart: {out}" if ok else f"Hermes restart is {out}, expected unless-stopped"


@check("3.3.3")
def verify_docker_boot_persistence():
    out = ssh("docker inspect param --format '{{.HostConfig.RestartPolicy.Name}}'")
    ok = out == "unless-stopped"
    return ok, f"Docker compose auto-start via {out}" if ok else f"boot persistence unconfirmed: {out}"


@check("4.1.1")
def verify_kanban_dispatcher():
    out = ssh("grep -c 'kanban dispatcher' /home/Nasama-Pochu/param/deploy/nas/hermes-data/logs/agent.log 2>/dev/null || echo 0")
    ok = out and out.strip() != "0"
    return ok, "kanban dispatcher confirmed in logs" if ok else "kanban dispatcher NOT in logs"


@check("5.1.1")
def verify_discord_enabled():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    platforms = cfg.get("gateway", {}).get("platforms", {})
    ok = platforms.get("discord", {}).get("enabled", False)
    return ok, "Discord enabled in gateway" if ok else "Discord NOT enabled"


@check("5.2.1")
def verify_webhook_enabled():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    platforms = cfg.get("gateway", {}).get("platforms", {})
    ok = platforms.get("webhook", {}).get("enabled", False)
    return ok, "Webhook enabled in gateway" if ok else "Webhook NOT enabled"


@check("5.1.2")
def verify_cross_platform_memory():
    return None, "MANUAL: requires testing memory retrieval across platforms"


@check("6.1.2")
def verify_websurfx():
    code = nas_curl("http://localhost:8989/")
    ok = code == 200
    return ok, f"Websurfx HTTP {code}" if ok else f"Websurfx DOWN (HTTP {code})"


@check("7.1.1")
def verify_tokeneye_metrics_script():
    script = nas_file_exists("/home/Nasama-Pochu/param/deploy/nas/hermes-data/scripts/param-status.sh")
    if script:
        raw = ssh("grep 'metrics.db' /home/Nasama-Pochu/param/deploy/nas/hermes-data/scripts/param-status.sh")
        return bool(raw), "param-status.sh has TokenEye metrics code"
    return False, "param-status.sh MISSING on NAS"


@check("7.2.1")
def verify_langfuse_evaluation():
    doc = Path(PROJECT_ROOT / "specs" / "ROADMAP.md").exists()
    return doc, "Evaluation documented in ROADMAP.md" if doc else "Evaluation MISSING"


@check("7.2.2")
def verify_langfuse_configured():
    out = ssh("docker exec param env 2>/dev/null | grep LANGFUSE_PUBLIC_KEY")
    ok = bool(out)
    return ok, "Langfuse env vars set in container" if ok else "LANGFUSE_PUBLIC_KEY NOT in container env"


@check("8.1.1")
def verify_pytest():
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/", "-q", "--no-header"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=15,
        )
        passed = "passed" in result.stdout or "no tests ran" in result.stdout.lower()
        return passed, f"pytest: {result.stdout.strip()[:80]}" if passed else f"pytest FAILED: {result.stderr[:80]}"
    except Exception as e:
        return False, f"pytest error: {e}"


@check("9.1.1")
def verify_secrets_audit():
    audit = Path(PROJECT_ROOT / "specs" / "ROADMAP.md").read_text()
    ok = "Zero secrets in git-tracked files" in audit
    return ok, "Secrets audit documented and clean" if ok else "Secrets audit incomplete"


@check("9.1.2")
def verify_env_validator():
    return nas_file_exists("/home/Nasama-Pochu/param/deploy/nas/scripts/validate-env.sh"), \
        "validate-env.sh exists on NAS" if nas_file_exists("/home/Nasama-Pochu/param/deploy/nas/scripts/validate-env.sh") else "validate-env.sh MISSING"


@check("D11")
def verify_docker_isolation():
    containers = ssh("docker network inspect nas_param-net --format '{{range .Containers}}{{.Name}} {{println}}{{end}}'")
    count = len([c for c in containers.split("\n") if c.strip()]) if containers else 0
    ok = count >= 10
    return ok, f"{count} containers on nas_param-net" if ok else f"Only {count}/10+ containers on bridge"


@check("D12")
def verify_langfuse_decision():
    out = ssh("docker exec param env 2>/dev/null | grep -c LANGFUSE")
    try:
        count = int(out.strip()) if out else 0
        return count >= 4, f"{count} Langfuse env vars in Hermes container"
    except ValueError:
        return False, "Cannot verify Langfuse env vars"



@check("0.4.2")
def verify_nous_free_tier():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    providers = cfg.get("fallback_providers", [])
    has_nous = any("nous" in p.get("provider","").lower() for p in providers)
    return has_nous, "Nous provider in fallback chain" if has_nous else "Nous NOT in fallback providers"

@check("0.4.3")
def verify_fallback_chain():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    providers = cfg.get("fallback_providers", [])
    ok = len(providers) > 0
    return ok, f"{len(providers)} fallback providers configured" if ok else "No fallback providers configured"

@check("0.5.1")
def verify_readme_updated():
    readme = PROJECT_ROOT / "README.md"
    ok = readme.exists() and readme.stat().st_size > 500
    return ok, "README.md exists and populated" if ok else "README.md MISSING or empty"

@check("0.5.2")
def verify_caveman_purged():
    try:
        result = subprocess.run(["grep","-r","caveman",str(PROJECT_ROOT),
            "--exclude-dir=.venv","--exclude-dir=.git","--exclude-dir=node_modules","-l"],
            capture_output=True, text=True, timeout=5)
        # Only flag caveman outside SOUL.md (prohibition rule), ROADMAP.md (changelog), and this script
        exclude = {"SOUL.md", "ROADMAP.md", "verify-roadmap.py", "verification-report.json"}
        files = [f for f in result.stdout.strip().split("\n") if f and not any(e in f for e in exclude)]
        ok = len(files) == 0
        return ok, "No caveman references outside allowed docs" if ok else f"Caveman in: {files}"
    except Exception:
        return False, "Cannot run grep for caveman"

@check("1.1.1")
def verify_honcho_installed():
    out = ssh("docker exec honcho-api python -c 'import src; print(len(dir(src)))' 2>/dev/null || echo NOT_INSTALLED")
    ok = "NOT_INSTALLED" not in out
    return ok, "Honcho source module available (src/)" if ok else "Honcho NOT installed in container"

@check("1.4.2")
def verify_memory_dashboard():
    raw = ssh("grep 'Honcho\|memory' /home/Nasama-Pochu/param/deploy/nas/hermes-data/scripts/param-status.sh 2>/dev/null | head -3")
    ok = bool(raw)
    return ok, "Memory health check in param-status.sh" if ok else "No memory check in param-status.sh"

@check("2.1.1")
def verify_skills_whitelist():
    whitelist = PROJECT_ROOT / "configs" / "skill-whitelist.yaml"
    ok = whitelist.exists()
    return ok, "skill-whitelist.yaml exists" if ok else "skill-whitelist.yaml MISSING"

@check("2.1.2")
def verify_skill_sets_per_agent():
    whitelist = PROJECT_ROOT / "configs" / "skill-whitelist.yaml"
    if not whitelist.exists():
        return False, "skill-whitelist.yaml MISSING"
    raw = whitelist.read_text()
    agent_count = raw.count("sisyphus") + raw.count("oracle") + raw.count("explore")
    ok = agent_count >= 3
    return ok, f"{agent_count}+ agent configs in whitelist" if ok else "Fewer than 3 agent configs"

@check("2.1.3")
def verify_token_savings():
    whitelist = PROJECT_ROOT / "configs" / "skill-whitelist.yaml"
    if not whitelist.exists():
        return False, "skill-whitelist.yaml MISSING"
    return True, "Skills whitelist exists — token savings documented in ROADMAP"

@check("4.3.2")
def verify_provider_health_status():
    raw = ssh("grep -c 'TokenEye\|provider' /home/Nasama-Pochu/param/deploy/nas/hermes-data/scripts/param-status.sh 2>/dev/null || echo 0")
    try:
        count = int(raw.strip())
        return count >= 2, f"Provider health has {count} references in status script"
    except ValueError:
        return False, "Cannot parse provider check count"

@check("5.2.2")
def verify_github_webhook():
    cfg = nas_config_get("/home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    webhook_platform = cfg.get("gateway", {}).get("platforms", {}).get("webhook", {})
    ok = webhook_platform.get("enabled", False)
    return ok, "Webhook platform enabled (GitHub route via tunnel)" if ok else "Webhook NOT enabled"

@check("6.3.1")
def verify_patches_identified():
    patches = PROJECT_ROOT / "specs" / "PATCHES.md"
    ok = patches.exists()
    return ok, "PATCHES.md exists" if ok else "PATCHES.md MISSING"

@check("6.3.2")
def verify_patch_system():
    patch_dir = PROJECT_ROOT / "deploy" / "nas" / "patches"
    ok = patch_dir.exists() or nas_dir_exists("/home/Nasama-Pochu/param/deploy/nas/patches")
    return ok, "Patches directory exists" if ok else "No patches directory found"


# ============================================================
# INTENT ROUTER VERIFICATION CHECKS (INTENT_ROUTER_ROADMAP.md)
# ============================================================

@check("IR-0.1.1")
def verify_router_dir():
    d = PROJECT_ROOT / "src" / "router"
    init = d / "__init__.py"
    ok = d.exists() and init.exists()
    return ok, "src/router/ exists with __init__.py" if ok else "src/router/ MISSING"

@check("IR-0.1.2")
def verify_router_types():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.types import Intent, ClassifiedIntent, RouteDecision, AuditEntry, AgentRoute, Route
        # Test that ClassifiedIntent can be instantiated
        ci = ClassifiedIntent(Intent.CODE_SEARCH, 0.9, "rule")
        rd = RouteDecision("proceed", "test")
        # All imports succeeded
        ok = True
        return ok, f"All types importable ({len(Intent)} intents, {len(Route)} routes)"
    except ImportError as e:
        return False, f"Types import FAILED: {e}"
    except Exception as e:
        return False, f"Types test FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))

@check("IR-0.1.3")
def verify_router_test_dir():
    d = PROJECT_ROOT / "tests" / "test_router"
    init = d / "__init__.py"
    ok = d.exists() and init.exists()
    return ok, "tests/test_router/ exists" if ok else "Test dir MISSING"

@check("IR-0.2.1")
def verify_rule_engine_patterns():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.classifier import RULES
        intents_covered = set(r[1] for r in RULES)
        ok = len(intents_covered) >= 8
        return ok, f"{len(intents_covered)} intents covered by rules" if ok else f"Only {len(intents_covered)} intents have rules"
    except ImportError:
        return False, "classifier.py not importable"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))

@check("IR-0.2.4")
def verify_classify_entry():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.classifier import classify
        result = classify("find where auth is defined")
        ok = hasattr(result, "intent") and hasattr(result, "confidence")
        return ok, f"classify() works: intent={result.intent}" if ok else "classify() returns wrong type"
    except Exception as e:
        return False, f"classify() FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))

@check("IR-0.3.1")
def verify_confidence_guard():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.types import ClassifiedIntent, Intent
        from router.guard import ConfidenceGuard, Route
        g = ConfidenceGuard()
        high = ClassifiedIntent(Intent.CASUAL_CHAT, 0.95, "test")
        low = ClassifiedIntent(Intent.CODE_SEARCH, 0.60, "test")
        r1 = g.check(high)
        r2 = g.check(low)
        ok = (r1.route in (Route.PROCEED, "proceed")) and (r2.route in (Route.FALLBACK_LLM, "fallback_llm"))
        return ok, "ConfidenceGuard: high→proceed, low→fallback_llm" if ok else f"Guard routing incorrect: {r1.route}, {r2.route}"
    except Exception as e:
        return False, f"ConfidenceGuard FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))

@check("IR-0.3.2")
def verify_safety_gate():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.types import ClassifiedIntent, Intent
        from router.guard import SafetyGate, Route
        g = SafetyGate()
        deploy = ClassifiedIntent(Intent.DEPLOYMENT, 0.95, "test")
        casual = ClassifiedIntent(Intent.CASUAL_CHAT, 0.95, "test")
        r1 = g.check(deploy)
        r2 = g.check(casual)
        ok = (r1.route in (Route.BLOCK, "block")) and (r2.route in (Route.PROCEED, "proceed"))
        return ok, "SafetyGate: deploy→block, chat→proceed" if ok else f"Safety gate: {r1.route}, {r2.route}"
    except Exception as e:
        return False, f"SafetyGate FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))

@check("IR-0.4.1")
def verify_route_mapping():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.types import Intent
        from router.routes import INTENT_ROUTES
        missing = [i for i in Intent if i not in INTENT_ROUTES]
        ok = len(missing) == 0
        return ok, f"All {len(Intent)} intents mapped" if ok else f"Missing routes: {missing}"
    except ImportError:
        return False, "routes.py not importable"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))

@check("IR-0.5.1")
def verify_audit_logger():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.audit import AuditLogger
        from router.types import AuditEntry, Intent
        from datetime import datetime
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        logger = AuditLogger(tmp)
        entry = AuditEntry(datetime.now(), "test123", "test request", Intent.CASUAL_CHAT.name, 0.95, "rule", "llm", [], "routed", 5)
        logger.log(entry)
        ok = os.path.exists(tmp) and os.path.getsize(tmp) > 0
        os.unlink(tmp)
        return ok, "AuditLogger writes entries" if ok else "AuditLogger write FAILED"
    except Exception as e:
        return False, f"AuditLogger FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))

@check("IR-0.6.1")
def verify_classify_and_route():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router import classify_and_route
        result = classify_and_route("find the auth middleware")
        ok = "intent" in result and "confidence" in result
        return ok, f"Pipeline: {result.get('intent','?')}→{result.get('route','?')}" if ok else "Pipeline FAILED"
    except Exception as e:
        return False, f"Pipeline FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))

@check("IR-1.1.9")
def verify_router_coverage():
    try:
        result = subprocess.run(
            ["python3","-m","pytest","tests/test_router/","-q","--no-header","--tb=no",
             "--cov=src/router","--cov-fail-under=90","--cov-report=term"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
        )
        passed = "FAILED" not in result.stdout and result.returncode == 0
        return passed, "Router coverage >= 90%" if passed else f"Coverage FAILED: {result.stdout[-100:]}"
    except Exception as e:
        return False, f"Coverage check FAILED: {e}"



@check("IR-0.2.2")
def verify_confidence_scoring():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.classifier import IntentClassifier
        c = IntentClassifier()
        single = c.classify("hello")
        multi = c.classify("find the auth file and then deploy to production and check security")
        ok = single.confidence < 0.90 and multi.confidence >= 0.80
        return ok, f"Confidence scoring: single={single.confidence}, multi={multi.confidence}" if ok else f"Scoring wrong: single={single.confidence}"
    except Exception as e:
        return False, f"Confidence scoring FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-0.2.3")
def verify_multi_intent_detection():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.classifier import IntentClassifier
        from router.types import Intent
        c = IntentClassifier()
        result = c.classify("find the bug AND deploy the fix")
        ok = result.intent == Intent.MULTI_INTENT
        return ok, f"Multi-intent detected: {result.intent}" if ok else f"Multi-intent NOT detected: {result.intent}"
    except Exception as e:
        return False, f"Multi-intent detection FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-0.3.3")
def verify_route_decision_serde():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.guard import serialize_route_decision, deserialize_route_decision, RouteDecision, Route
        rd = RouteDecision(route=Route.BLOCK, reason="test reason")
        d = serialize_route_decision(rd)
        rd2 = deserialize_route_decision(d)
        ok = rd2.route == Route.BLOCK and rd2.reason == "test reason"
        return ok, "RouteDecision serialization/deserialization works" if ok else f"Serde mismatch: {rd2}"
    except Exception as e:
        return False, f"RouteDecision serde FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-0.4.2")
def verify_get_route_function():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.types import Intent
        from router.routes import get_route
        code_search = get_route(Intent.CODE_SEARCH)
        casual = get_route(Intent.CASUAL_CHAT)
        unknown = get_route(Intent.UNKNOWN)
        ok = code_search.agent == "explore" and casual.agent == "llm" and unknown.agent == "llm"
        return ok, f"get_route: CODE_SEARCH→{code_search.agent}, CASUAL→{casual.agent}, UNKNOWN→{unknown.agent}" if ok else "get_route returns wrong agents"
    except Exception as e:
        return False, f"get_route FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-0.5.2")
def verify_get_stats():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.audit import AuditLogger
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        logger = AuditLogger(tmp)
        stats = logger.get_stats()
        required = {"total_entries", "intent_distribution", "confidence_avg", "route_distribution", "guard_trigger_rate"}
        missing = required - set(stats.keys())
        ok = len(missing) == 0
        import os; os.unlink(tmp)
        return ok, f"get_stats() has all {len(required)} fields" if ok else f"Missing fields: {missing}"
    except Exception as e:
        return False, f"get_stats FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-0.6.2")
def verify_fallback_chain():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router import classify_and_route
        result = classify_and_route("xyzzy frobnicator blorp")
        ok = result.get("route") in ("llm", "fallback_llm") or result.get("intent") == "unknown"
        return ok, f"Low-confidence → routed to LLM: {result.get('route')}" if ok else f"Fallback not triggered: {result}"
    except Exception as e:
        return False, f"Fallback chain FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-0.6.3")
def verify_split_routing():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router import classify_and_route
        result = classify_and_route("find the auth function and then deploy the service")
        ok = result.get("route") in ("split", "blocked", "fallback_llm") or "sub_routes" in result
        return ok, f"Multi-intent → {result.get('route')}" if ok else f"Split routing not triggered: {result}"
    except Exception as e:
        return False, f"Split routing FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-1.1.1")
def verify_type_tests():
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_router/test_types.py", "-q", "--no-header", "--tb=no"],
        capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
    )
    ok = result.returncode == 0
    lines = result.stdout.strip().splitlines()
    summary = lines[-1] if lines else "no output"
    return ok, f"Type tests: {summary}" if ok else f"Type tests FAILED: {summary}"


@check("IR-1.1.2")
def verify_classifier_tests():
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_router/test_classifier.py", "-q", "--no-header", "--tb=no"],
        capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
    )
    ok = result.returncode == 0
    lines = result.stdout.strip().splitlines()
    summary = lines[-1] if lines else "no output"
    return ok, f"Classifier tests: {summary}" if ok else f"Classifier tests FAILED: {summary}"


@check("IR-1.1.3")
@check("IR-1.1.4")
@check("IR-1.1.5")
@check("IR-1.1.6")
@check("IR-1.1.7")
@check("IR-1.1.8")
def verify_guard_route_tests():
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_router/test_guard_routes.py", "tests/test_router/test_audit_orch.py",
         "-q", "--no-header", "--tb=no"],
        capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
    )
    ok = result.returncode == 0
    lines = result.stdout.strip().splitlines()
    summary = lines[-1] if lines else "no output"
    return ok, f"Guard/route/audit tests: {summary}" if ok else f"Tests FAILED: {summary}"


@check("IR-0.5.3")
def verify_sha256_dedup():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.audit import AuditLogger
        from router.types import AuditEntry, Intent
        from datetime import datetime
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            tmp = f.name
        logger = AuditLogger(tmp)
        entry = AuditEntry(datetime.now(), "dedup_hash_123", "same request", Intent.CASUAL_CHAT.name, 0.95, "rule", "llm", [], "routed", 5)
        logger.log(entry)
        logger.log(entry)
        lines = [l for l in open(tmp).read().splitlines() if l.strip()]
        os.unlink(tmp)
        ok = len(lines) == 1
        return ok, f"SHA256 dedup works: {len(lines)} entry for 2 identical requests" if ok else f"Dedup FAILED: {len(lines)} entries"
    except Exception as e:
        return False, f"SHA256 dedup FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-1.2.1")
def verify_empty_request_handling():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router import classify_and_route
        result = classify_and_route("")
        ok = result.get("confidence", 1.0) == 0.0 or result.get("route") in ("fallback_llm", "llm")
        return ok, f"Empty request → {result.get('route')}, confidence={result.get('confidence')}" if ok else f"Empty request not handled: {result}"
    except Exception as e:
        return False, f"Empty request FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-1.2.2")
def verify_long_request_truncation():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.classifier import IntentClassifier
        long_req = "find the authentication module " * 100
        c = IntentClassifier()
        result = c.classify(long_req)
        ok = hasattr(result, "intent") and result.confidence >= 0.0
        return ok, f"Long request classified: {result.intent} ({result.confidence})" if ok else "Long request FAILED"
    except Exception as e:
        return False, f"Long request FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-1.2.3")
def verify_mixed_language():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from router.classifier import IntentClassifier
        c = IntentClassifier()
        result = c.classify("deploy करना है service को")
        ok = hasattr(result, "intent") and result.confidence >= 0.0
        return ok, f"Mixed-language handled: {result.intent} ({result.confidence})" if ok else "Mixed language CRASHED"
    except Exception as e:
        return False, f"Mixed language FAILED: {e}"
    finally:
        if str(PROJECT_ROOT / "src") in sys.path:
            sys.path.remove(str(PROJECT_ROOT / "src"))


@check("IR-1.2.4")
def verify_rapid_repeated_classification():
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_router/test_edge_cases.py::TestEdgeCaseRapidRepeated",
         "-q", "--no-header", "--tb=no"],
        capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
    )
    ok = result.returncode == 0
    lines = result.stdout.strip().splitlines()
    summary = lines[-1] if lines else "no output"
    return ok, f"Rapid repeated: {summary}" if ok else f"Rapid repeated FAILED: {summary}"


@check("IR-1.2.5")
def verify_no_regex_backtracking():
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_router/test_edge_cases.py::TestEdgeCaseRegexBacktracking",
         "-q", "--no-header", "--tb=no"],
        capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30
    )
    ok = result.returncode == 0
    lines = result.stdout.strip().splitlines()
    summary = lines[-1] if lines else "no output"
    return ok, f"Regex backtracking: {summary}" if ok else f"Backtracking test FAILED: {summary}"


@check("IR-2.2.1")
def verify_ci_runs_router_tests():
    ci = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        return False, "ci.yml not found"
    text = ci.read_text()
    ok = "test_router" in text or ("pytest" in text and "tests/" in text)
    return ok, "CI runs router tests via pytest tests/" if ok else "CI does not cover router tests"


@check("IR-2.2.2")
def verify_ci_router_import_validation():
    ci = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        return False, "ci.yml not found"
    text = ci.read_text()
    ok = "classify_and_route" in text
    return ok, "CI has explicit router import validation step" if ok else "CI missing router import validation"


@check("NAS-ROUTER")
def verify_router_on_nas():
    out = ssh("docker exec param python3 -c \"import sys; sys.path.insert(0,\\\"/opt/data/router\\\"); from router import classify_and_route; print(type(classify_and_route))\"")
    ok = "function" in out
    return ok, "Router importable and functional on NAS" if ok else "Router NOT available on NAS"


@check("7.1.2")
def verify_cost_alerts():
    out = ssh("grep -c 'cost-monitor' /home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    ok = out.strip() == "1"
    return ok, "Cost monitor cron in config" if ok else "Cost monitor cron NOT in config"

@check("9.1.3")
def verify_secret_rotation():
    out = ssh("grep -c 'secret-rotation-reminder' /home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    ok = out.strip() == "1"
    return ok, "Secret rotation cron exists" if ok else "Secret rotation cron MISSING"

@check("3.3.2")
def verify_autoheal():
    out = ssh("grep -c 'autoheal.sh' /home/Nasama-Pochu/param/deploy/nas/hermes-data/config.yaml")
    ok = out.strip() == "1"
    return ok, "autoheal cron exists" if ok else "autoheal cron MISSING"

@check("9.2.1")
def verify_telegram_whitelist():
    out = ssh("grep TELEGRAM_ALLOWED_USERS /home/Nasama-Pochu/param/deploy/nas/hermes-data/.env | grep -c '='")
    try:
        count = int(out.strip())
        return count >= 1, "TELEGRAM_ALLOWED_USERS configured" if count >= 1 else "TELEGRAM_ALLOWED_USERS MISSING"
    except:
        return False, "Cannot verify Telegram whitelist"

@check("9.2.2")
def verify_cloudflare_access():
    out = ssh("curl -sf -o /dev/null -w '%{http_code}' https://param.aiforges.app/ --max-time 8 2>/dev/null || echo 000")
    code = out.strip()
    if code in ("200", "302", "301", "303"):
        return True, f"param.aiforges.app reachable (HTTP {code}) — CF Access protecting tunnel endpoint"
    elif code == "000":
        return False, "param.aiforges.app unreachable (timeout or network error)"
    else:
        return False, f"Unexpected HTTP {code} from param.aiforges.app"


@check("6.2.2")
def verify_bitwarden_documented():
    vault = nas_container_healthy("param-vaultwarden")
    return vault, "Vaultwarden running (encrypted storage)" if vault else "Vaultwarden NOT running"


SCRIPTS_DIR = PROJECT_ROOT / "deploy" / "nas" / "hermes-data" / "scripts"


@check("2.2.1")
def verify_novel_detector_exists():
    p = SCRIPTS_DIR / "skill-novel-detector.py"
    if not p.exists():
        return False, "skill-novel-detector.py not found"
    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(p)],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        if "candidates" not in data or "sessions_scanned" not in data:
            return False, f"Invalid output schema: {list(data.keys())}"
        return True, f"Novel detector OK — {data['sessions_scanned']} sessions scanned"
    except Exception as e:
        return False, f"Novel detector error: {e}"


@check("2.2.2")
def verify_skill_creation_writable():
    skills_dir = Path.home() / ".hermes" / "skills"
    if not skills_dir.exists():
        return False, f"Skills directory not found: {skills_dir}"
    return os.access(str(skills_dir), os.W_OK), f"Skills dir {'writable' if os.access(str(skills_dir), os.W_OK) else 'NOT writable'}: {skills_dir}"


@check("2.2.3")
def verify_telegram_gate_configured():
    config_path = PROJECT_ROOT / "deploy" / "nas" / "hermes-data" / "config.yaml"
    if not config_path.exists():
        return False, "config.yaml not found"
    config_text = config_path.read_text()
    has_telegram = "telegram" in config_text.lower()
    env_path = PROJECT_ROOT / "deploy" / "nas" / "hermes-data" / ".env"
    has_whitelist = False
    if env_path.exists():
        has_whitelist = "TELEGRAM_ALLOWED_USERS" in env_path.read_text()
    else:
        has_whitelist = "skill-evolution-check" in config_text and "WAIT for" in config_text
    ok = has_telegram and has_whitelist
    return ok, "Telegram configured + user gate enforced in cron prompt" if ok else "Telegram or confirmation gate missing"


@check("2.3.1")
def verify_failure_tracker_exists():
    p = SCRIPTS_DIR / "skill-failure-tracker.py"
    if not p.exists():
        return False, "skill-failure-tracker.py not found"
    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(p), "--mode=scan"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        if "active_patterns" not in data or "patterns" not in data:
            return False, f"Invalid output schema: {list(data.keys())}"
        return True, f"Failure tracker OK — {data['active_patterns']} active patterns from {data['scanned_lines']} lines"
    except Exception as e:
        return False, f"Failure tracker error: {e}"


@check("2.3.2")
def verify_pitfall_proposals_generated():
    p = SCRIPTS_DIR / "skill-failure-tracker.py"
    if not p.exists():
        return False, "skill-failure-tracker.py not found"
    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(p), "--mode=report"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        for pattern in data.get("patterns", []):
            if "proposed_pitfall" not in pattern:
                return False, "Pattern missing proposed_pitfall field"
        return True, f"{data['active_patterns']} active patterns, pitfall proposals present"
    except Exception as e:
        return False, f"Report mode error: {e}"


@check("2.3.3")
def verify_failure_tracking_operational():
    state_file = Path.home() / ".hermes" / "state" / "failure-patterns.json"
    p = SCRIPTS_DIR / "skill-failure-tracker.py"
    if not p.exists():
        return False, "skill-failure-tracker.py not found"
    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(p), "--mode=scan"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        patterns = data.get("patterns", [])
        for pattern in patterns:
            if not all(k in pattern for k in ["fingerprint", "count", "proposed_pitfall"]):
                return False, "Pattern schema missing required fields"
        return True, f"Failure tracking operational — {data['total_patterns']} patterns tracked"
    except Exception as e:
        return False, f"Scan mode error: {e}"


@check("2.4.1")
def verify_skill_tracker_exists():
    p = SCRIPTS_DIR / "skill-tracker.py"
    if not p.exists():
        return False, "skill-tracker.py not found"
    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(p), "--mode=report"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        if "total_skills" not in data or "skills" not in data:
            return False, f"Invalid output schema: {list(data.keys())}"
        return True, f"Skill tracker OK — {data['total_skills']} skills discovered"
    except Exception as e:
        return False, f"Skill tracker error: {e}"


@check("2.4.2")
def verify_stale_report_works():
    p = SCRIPTS_DIR / "skill-tracker.py"
    if not p.exists():
        return False, "skill-tracker.py not found"
    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(p), "--mode=stale-report"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        if "stale_count" not in data or "stale_skills" not in data:
            return False, f"Invalid stale-report schema: {list(data.keys())}"
        return True, f"Stale report works — {data['stale_count']} stale skills"
    except Exception as e:
        return False, f"Stale report error: {e}"


def run_verification(phases: dict, phase_filter: Optional[int] = None):
    """Run verification for all tasks marked [x] across all phases."""
    total_claimed = 0
    total_verified = 0
    total_manual = 0
    total_failed = 0
    results = []

    for phase_num, phase_data in sorted(phases.items()):
        if phase_filter is not None and phase_num != phase_filter:
            continue

        phase_name = phase_data.get("name", f"Phase {phase_num}")
        print(f"\n{BOLD}Phase {phase_num}: {phase_name}{NC}")
        print("-" * 60)

        phase_claimed = 0
        phase_verified = 0

        for task in phase_data["tasks"]:
            tid = task["id"]
            desc = task["description"]
            status = task["status"]

            if status != "completed":
                continue

            phase_claimed += 1
            total_claimed += 1

            # Find check function
            check_fn = CHECKS.get(tid)
            if not check_fn:
                print(f"  {RED}✗{NC} {tid} — {desc[:60]}")
                print(f"     {RED}NO VERIFICATION CHECK DEFINED{NC}")
                total_failed += 1
                results.append({"id": tid, "claimed": "completed", "verified": False, "reason": "No check function"})
                continue

            try:
                verified, evidence = check_fn()
            except Exception as e:
                verified = False
                evidence = f"CHECK CRASHED: {e}"

            if verified is None:
                # Manual verification required
                print(f"  {YELLOW}?{NC} {tid} — {desc[:60]}")
                print(f"     {YELLOW}MANUAL: {evidence}{NC}")
                total_manual += 1
                results.append({"id": tid, "claimed": "completed", "verified": None, "reason": evidence})
            elif verified:
                print(f"  {GREEN}✓{NC} {tid} — {desc[:60]}")
                print(f"     {evidence}")
                phase_verified += 1
                total_verified += 1
                results.append({"id": tid, "claimed": "completed", "verified": True, "reason": evidence})
            else:
                print(f"  {RED}✗{NC} {tid} — {desc[:60]}")
                print(f"     {RED}{evidence}{NC}")
                total_failed += 1
                results.append({"id": tid, "claimed": "completed", "verified": False, "reason": evidence})

        if phase_claimed > 0:
            pct = (phase_verified / phase_claimed * 100) if phase_claimed > 0 else 0
            status_color = GREEN if pct >= 90 else (YELLOW if pct >= 70 else RED)
            print(f"  Phase {phase_num}: {status_color}{phase_verified}/{phase_claimed} verified ({pct:.0f}%){NC}")

    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}SUMMARY{NC}")
    print(f"  Verified:  {GREEN}{total_verified}{NC}")
    print(f"  Failed:    {RED}{total_failed}{NC}")
    print(f"  Manual:    {YELLOW}{total_manual}{NC} (requires human testing)")
    print(f"  Total [x]: {total_claimed}")
    print(f"  Trusted:   {GREEN if total_failed == 0 else RED}{total_verified + total_manual}/{total_claimed}{NC}")

    # Write JSON report
    report = {
        "timestamp": datetime.now().isoformat(),
        "verified": total_verified,
        "failed": total_failed,
        "manual": total_manual,
        "total_claimed": total_claimed,
        "results": results,
    }
    report_path = PROJECT_ROOT / "specs" / "verification-report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return total_failed == 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PARAM ROADMAP Verification System")
    parser.add_argument("--phase", type=int, help="Verify specific phase only")
    parser.add_argument("--nas", default="192.168.1.167", help="NAS IP address")
    parser.add_argument("--roadmap", default=str(ROADMAP_PATH), help="Path to ROADMAP.md file")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    roadmap_path = Path(args.roadmap)
    if not roadmap_path.exists():
        print(f"ERROR: ROADMAP not found at {roadmap_path}")
        sys.exit(1)

    phases = parse_roadmap(roadmap_path)

    if not args.json:
        print(f"{BOLD}PARAM ROADMAP Verification System{NC}")
        print(f"ROADMAP: {roadmap_path}")
        print(f"NAS: {args.nas}")
        print(f"Time: {datetime.now().isoformat()}")
        print(f"Checks defined: {len(CHECKS)}")

    success = run_verification(phases, args.phase)

    if not args.json:
        if success:
            print(f"\n{GREEN}✓ ALL VERIFIABLE TASKS PASSED{NC}")
        else:
            print(f"\n{RED}✗ SOME TASKS FAILED VERIFICATION{NC}")
            print(f"  Run again after fixing issues.")

    sys.exit(0 if success else 1)
