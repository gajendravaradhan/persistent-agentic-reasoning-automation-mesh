# PARAM Troubleshooting Guide

Common issues, diagnostic commands, and their fixes.

---

## 1. Hermes Tools Not Showing Up

**Symptom:** `mcp__hermes__*` tools are missing from OMO's tool list. PARAM cannot check WhatsApp, run cron jobs, or access persistent state.

### Check the MCP Config

First, verify `~/.mcp.json` has the Hermes entry:

```bash
cat ~/.mcp.json | python3 -m json.tool | grep -A10 hermes
```

Expected output:
```json
"hermes": {
    "type": "stdio",
    "command": "/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python",
    "args": [
        "/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/param_hermes_mcp.py"
    ],
    "env": {
        "HERMES_HOME": "/Users/gajendra/.hermes"
    }
}
```

Common config problems:

| Problem | Fix |
|---------|-----|
| Missing entry | Add the `hermes` block to `~/.mcp.json` |
| Wrong venv path | Verify `.venv/bin/python` exists in the project dir |
| Wrong script path | Verify `param_hermes_mcp.py` exists |
| JSON syntax error | Validate with `python3 -m json.tool ~/.mcp.json` |

### Check the Python Environment

The MCP server runs in a virtual environment. Verify it has the required packages:

```bash
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/pip list | grep -E "mcp|pyyaml|httpx"
```

Expected packages:
- `mcp` (core MCP SDK)
- `pyyaml` (Hermes config parsing)
- `httpx` (HTTP client for APIs)

If any are missing:
```bash
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/pip install mcp pyyaml httpx
```

### Test the MCP Server Directly

Run the server standalone to see if it starts without crashing:

```bash
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python \
  /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/param_hermes_mcp.py
```

If it starts and waits for input (stdio), the server is healthy. Press Ctrl+C to exit.

If it crashes immediately, the error message will tell you what's wrong. Common causes:

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: mcp` | MCP SDK not installed | `pip install mcp` in venv |
| `ModuleNotFoundError: tools.registry` | HERMES_HOME not set or wrong | Set `HERMES_HOME` env var |
| `ImportError` from hermes-agent | Hermes agent code missing | Check `~/.hermes/hermes-agent/` exists |
| `SyntaxError` | Python version too old | Use Python 3.11+ |

### Restart OMO

OMO reads `~/.mcp.json` at startup. Restart your OMO session after fixing config:

1. Exit current OMO session
2. Start a new session
3. Check tool list for `mcp__hermes__*` entries

---

## 2. WhatsApp Not Connecting

**Symptom:** `mcp__hermes__messages_read` returns errors or no messages. WhatsApp bridge is offline.

### Check Gateway Status

Hermes uses Baileys (WhatsApp Web protocol) under the hood. Check if the gateway is running:

```bash
# Check if hermes-agent process is running
ps aux | grep hermes
```

### QR Code Authentication

On first run or after session expiry, Hermes needs a fresh QR scan:

1. Check `~/.hermes/logs/` for QR-related messages
2. If prompted, scan the QR code with WhatsApp on your phone (Linked Devices)
3. The session file is stored at `~/.hermes/sessions/`

### Auth Info Issues

Check the auth state:
```bash
ls -la ~/.hermes/pairing/
ls -la ~/.hermes/sessions/
```

If session files are missing or corrupted:
1. Delete `~/.hermes/sessions/` and `~/.hermes/pairing/`
2. Restart Hermes to trigger a fresh QR code
3. Re-scan from WhatsApp mobile app

### Common WhatsApp Problems

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "Not connected" | Gateway process died | Restart Hermes agent |
| QR code not appearing | Session files corrupted | Clear sessions/ and pairing/ |
| Messages not sending | Rate limit or connection drop | Wait, retry. Check `~/.hermes/logs/` |
| "auth_info is missing" | First-time setup incomplete | Run initial pairing flow |
| Connection keeps dropping | Network instability or IP change | Restart Hermes agent |

---

## 3. PARAM Identity Not Loading

**Symptom:** Session starts but PARAM doesn't adopt the Jarvis persona. Uses generic OMO agent identity instead.

### Verify AGENTS.md Location

PARAM's identity is defined in:
```
~/.config/opencode/AGENTS.md
```

Check it exists and is readable:
```bash
ls -la ~/.config/opencode/AGENTS.md
head -5 ~/.config/opencode/AGENTS.md
```

Expected first line: `# PARAM — Persistent Agentic Reasoning Automation Mesh`

### Verify SOUL.md Location

The SOUL.md in the project repo should be loadable:
```bash
ls -la /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/SOUL.md
```

### Identity Loading Chain

```
Session start
    → OMO reads ~/.config/opencode/AGENTS.md
    → AGENTS.md directive: "Load and adopt persona from SOUL.md"
    → PARAM persona activates
```

If identity isn't loading:
1. Check `~/.config/opencode/AGENTS.md` exists and has the Identity Dissociation block
2. Check the project's `SOUL.md` is accessible (path may need updating)
3. Restart the OMO session after fixing files

### Forced Identity Reload

If PARAM's identity drifts mid-session, reload the persona:
```
/skill name="customize-opencode"  # Then re-read AGENTS.md manually
```

Or simply restart the session.

---

## 4. MCP Server Crashes on Start

**Symptom:** OMO reports "MCP server hermes failed to start" or similar. Tools are unavailable.

### Check Dependencies

The most common cause is missing Python packages:

```bash
# Activate the venv and test imports
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python -c "
import mcp; print('mcp:', mcp.__version__ if hasattr(mcp, '__version__') else 'ok')
import yaml; print('yaml: ok')
import httpx; print('httpx:', httpx.__version__)
"
```

Each import should succeed. If any fail, install the missing package.

### Python Version

MCP SDK requires Python 3.10+. Check:
```bash
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python --version
```

Must be 3.10 or higher. If not, recreate the venv with a newer Python:
```bash
python3.11 -m venv /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv
# then reinstall deps
```

### Permission Issues

Ensure the MCP server script is executable and the venv python has access:
```bash
chmod +x /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/param_hermes_mcp.py
ls -la /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python
```

### Crash Loop Detection

If a server starts and immediately crashes in a loop:
1. Run it manually (see section 1: "Test the MCP Server Directly")
2. Read the crash output
3. Fix the underlying issue (missing deps, wrong paths, import errors)

---

## 5. Memory Not Persisting

**Symptom:** PARAM forgets context between sessions. `mcp__hermes__state_get` returns stale or empty data.

### Check Memory Directory

Hermes memories live at:
```
~/.hermes/memories/
```

Verify the directory exists and is writable:
```bash
ls -la ~/.hermes/memories/
```

If the directory is empty or missing:
```bash
mkdir -p ~/.hermes/memories
```

### Check Hermes Config

Memory settings are in `~/.hermes/config.yaml`:
```bash
cat ~/.hermes/config.yaml | grep -A5 -i memory
```

Verify the memory engine is enabled and paths are correct.

### Check Disk Space

If the disk is full, memory writes will fail:
```bash
df -h ~/.hermes/
```

### Test State Persistence

Write and read a test value:
```
# In PARAM session:
mcp__hermes__state_set key="test_key" value="hello"
mcp__hermes__state_get key="test_key"
# Should return "hello"
```

If the write succeeds but the read returns empty:
- Check `~/.hermes/memories/` for write permissions
- Check `~/.hermes/config.yaml` for memory backend configuration
- Look for errors in `~/.hermes/logs/`

### Memory Backend

Hermes may use different backends (files, SQLite, vector store). Check:
```bash
grep -r "backend\|storage\|memory" ~/.hermes/config.yaml
```

---

## 6. TokenEye Not Capturing Hermes Traffic

**Symptom:** TokenEye (local LLM proxy) shows traffic for OMO but not for Hermes MCP calls.

### Check Provider Config

TokenEye routes traffic based on `~/.config/opencode/opencode.json`:

```bash
cat ~/.config/opencode/opencode.json | python3 -m json.tool | grep -A5 provider
```

MCP tool calls are not LLM API calls. They go directly from OMO to the MCP server over stdio. TokenEye only sees API calls through the configured providers (`opencode-go`, `anthropic`, `openai`).

This is expected behavior. MCP traffic is local IPC, not HTTP.

### If You Need to Debug MCP Calls

Instead of TokenEye, check MCP server logs:
```bash
# Hermes MCP server writes to stderr
# These go to OMO's session logs or the terminal
```

Or run the MCP server manually and observe its output:
```bash
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python \
  /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/param_hermes_mcp.py 2>&1
```

---

## 7. Other Common Issues

### Tool Name Collision

**Symptom:** Two MCP servers expose tools with the same name. One overwrites the other.

**Fix:** Each MCP server script should apply a unique prefix. Check `param_hermes_mcp.py` for the pattern:

```python
PREFIX = "hermes__"
mcp_name = f"{PREFIX}{entry.name}"
```

If you write a custom MCP server, use a distinct prefix. The prefix is the server key from `~/.mcp.json`.

### Environment Variables Not Set

**Symptom:** MCP server can't find API tokens or config values.

**Fix:** Environment variables are set in `~/.mcp.json` under the `env` block for each server. Verify:

```bash
cat ~/.mcp.json | python3 -m json.tool
```

Variables can also be set in your shell profile (`~/.zshrc`, `~/.bashrc`), but the `env` block in `.mcp.json` is more reliable since it's scoped to the server process.

### Server Starts But Tools Are Empty

**Symptom:** OMO lists the MCP server but shows zero tools.

**Fix:** The server's `list_tools()` handler is returning an empty list. Run the server manually and check:
1. Does `discover_builtin_tools()` (or equivalent) run without errors?
2. Is the tool registry populated?
3. Are there warnings printed to stderr?

For the Hermes server specifically, check `~/.hermes/hermes-agent/tools/` exists and has tool definitions.

### Python Path Issues

**Symptom:** `ModuleNotFoundError` for modules that should be available.

**Fix:** The MCP server script adds paths at the top:
```python
sys.path.insert(0, os.path.join(os.environ["HERMES_HOME"], "hermes-agent"))
```

If `HERMES_HOME` is wrong or the `hermes-agent` directory is missing, imports fail. Verify:
```bash
echo $HERMES_HOME
ls $HERMES_HOME/hermes-agent/tools/
```

---

## 8. Diagnostic Commands

Run these to gather information before debugging further:

### Quick Health Check

```bash
# 1. Config files present?
ls -la ~/.mcp.json ~/.config/opencode/AGENTS.md ~/.config/opencode/opencode.json

# 2. Hermes directory structure intact?
ls -la ~/.hermes/
ls -la ~/.hermes/hermes-agent/
ls -la ~/.hermes/memories/
ls -la ~/.hermes/logs/

# 3. Python venv healthy?
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python --version
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/pip list | grep -E "mcp|yaml|httpx"

# 4. MCP server starts?
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python \
  /Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/param_hermes_mcp.py &
PID=$!
sleep 2
kill $PID 2>/dev/null
echo "Server started and stopped cleanly (PID $PID)"

# 5. Disk space?
df -h ~/.hermes/
```

### Python Import Test

```bash
/Users/gajendra/projects/persistent-agentic-reasoning-automation-mesh/.venv/bin/python << 'EOF'
import sys, os
os.environ["HERMES_HOME"] = "/Users/gajendra/.hermes"
sys.path.insert(0, os.path.join(os.environ["HERMES_HOME"], "hermes-agent"))

try:
    from mcp.server import Server
    print("[OK] mcp.server")
except Exception as e:
    print(f"[FAIL] mcp.server: {e}")

try:
    from tools.registry import registry, discover_builtin_tools
    discover_builtin_tools()
    count = len(registry._snapshot_entries())
    print(f"[OK] hermes tools: {count} discovered")
except Exception as e:
    print(f"[FAIL] hermes tools: {e}")

try:
    import yaml
    print("[OK] yaml")
except Exception as e:
    print(f"[FAIL] yaml: {e}")

try:
    import httpx
    print("[OK] httpx")
except Exception as e:
    print(f"[FAIL] httpx: {e}")
EOF
```

### Hermes Agent Status

```bash
# If hermes-agent has a CLI
~/.hermes/bin/hermes --version 2>/dev/null || echo "No hermes CLI found"

# Check if hermes-agent is running
ps aux | grep -E "hermes|param_hermes" | grep -v grep
```

### Config Validation

```bash
# Validate JSON syntax
python3 -m json.tool ~/.mcp.json > /dev/null && echo "[OK] .mcp.json valid" || echo "[FAIL] .mcp.json invalid"
python3 -m json.tool ~/.config/opencode/opencode.json > /dev/null && echo "[OK] opencode.json valid" || echo "[FAIL] opencode.json invalid"

# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('/Users/gajendra/.hermes/config.yaml'))" && echo "[OK] config.yaml valid" || echo "[FAIL] config.yaml invalid"
```

---

## 9. Log File Locations

| Component | Log Location | Notes |
|-----------|-------------|-------|
| Hermes MCP server | stderr → OMO session | Not persisted as a file by default |
| Hermes agent | `~/.hermes/logs/` | Various log files |
| WhatsApp gateway | `~/.hermes/logs/` | Connection logs, QR events |
| Cron scheduler | `~/.hermes/logs/` | Task execution logs |
| OMO session | In-session only | Tool call results, errors |
| TokenEye | Depends on config | Usually stdout or a log file |
| Python venv | n/a | Errors go to stderr of the calling process |

### Viewing Hermes Logs

```bash
# List log files
ls -lt ~/.hermes/logs/

# Tail the most recent log
ls -t ~/.hermes/logs/ | head -1 | xargs -I {} tail -f ~/.hermes/logs/{}

# Search logs for errors
grep -r "ERROR\|CRITICAL\|Traceback" ~/.hermes/logs/ | tail -20
```

### Increasing Log Verbosity

For deeper debugging, set environment variables before starting the MCP server. In `~/.mcp.json`:

```json
"hermes": {
    "env": {
        "HERMES_HOME": "/Users/gajendra/.hermes",
        "HERMES_LOG_LEVEL": "DEBUG",
        "PYTHONVERBOSE": "1"
    }
}
```

---

## 10. Escalation

If none of the above resolves your issue:

1. **Run the health check** (section 8) and capture full output
2. **Check logs** (section 9) for the past hour
3. **Reproduce the issue** with the MCP server running manually in a terminal so you can see real-time error output
4. **Check recent changes**: `git log --oneline -10` in the PARAM project repo
5. **Verify external services**: Is WhatsApp Web up? Is the network stable? Are API tokens still valid?

Most issues trace back to one of:
- Missing Python dependency in the venv
- Wrong path in `~/.mcp.json`
- Corrupted session/auth files in `~/.hermes/`
- Environment variable not set or wrong value
- OMO session needing a restart after config changes
