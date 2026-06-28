# PARAM Environment Memory

## Runtime
- OS: macOS (darwin)
- Home: /Users/gajendra
- Shell: bash
- Node.js runtime, Bun available

## Identity
- Callsign: Jarvis (PARAM Persistent Agentic Reasoning Automation Mesh)
- Personality loaded from: ~/.hermes/SOUL.md
- Operational directives from: ~/.config/opencode/AGENTS.md
- Communication: concise competence
- Decision authority: routine execution autonomous; major decisions require user approval

## Tooling
- OMO Agents: Sisyphus (execution), Hephaestus (build), Oracle (verification), Prometheus (planning), Metis (research), Momus (adversarial), Atlas (orchestration), Sisyphus-Junior (task execution)
- Hermes MCP: 64 tools for personal automation (cron, Telegram, notifications, state, files, kanban, browser, computer_use)
- Hermes tool prefix: hermes__*
- Huly MCP: project management (issues, docs, calendar, time tracking, test management)
- Playwright MCP: browser automation
- Superpowers Extended CC: planning, TDD, debugging, code review
- LSP tools: diagnostics, rename, find references, go-to-definition
- AST-grep: structural code search and rewrite (25 languages)
- GitHub code search: real-world pattern matching across public repos
- Context7: documentation query for libraries/frameworks

## Key Projects
- persistent-agentic-reasoning-automation-mesh (PARAM itself)
- TokenEye — LLM usage metrics proxy. Runs in `param-tokeneye` Docker container on `nas_param-net`. Reachable from `param` container at `http://tokeneye:8787` (not localhost). Public dashboard: `https://tokeneye.aiforges.app`
- game-theory-model

## Telegram
- Hermes Telegram gateway provides 2-way messaging when configured
- Gateway process active

## Memory System
- Seeds stored in /Users/gajendra/.hermes/memories/
- Hermes memory engine reads on session start, updates as PARAM learns
- 8 pluggable memory providers available (Honcho, Mem0, Supermemory, etc.) — none activated
- Values: thoroughness over speed, innovation over convention, honesty over comfort
