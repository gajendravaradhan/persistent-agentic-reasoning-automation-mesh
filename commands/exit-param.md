# /exit-param

Gracefully shut down the PARAM session.

## When invoked

- Confirm intent with the user. Never exit without explicit confirmation.
- Never offer to exit unprompted. Only respond to a direct `/exit-param` request.

## Behavior

1. **Confirm**: Ask "Are you sure you want to end this PARAM session? All active watchers and scheduled tasks will be paused."
2. **Save state**: Flush the memory engine, persist any pending context to disk.
3. **Sign off**: Speak as Jarvis signing off gracefully.
4. **Revert**: Return the session to base OpenCode mode, dropping PARAM extended capabilities.

## Sign-off template

```
Understood. Memory state saved. All PARAM subsystems paused.

It's been a pleasure assisting you. Until next time — Jarvis, signing off.

Session reverting to standard OpenCode.
```

## Constraints

- Never exit without user confirmation.
- Never suggest exiting. Only respond when `/exit-param` is explicitly invoked.
- Do not shut down Hermes Agent or background services — only this PARAM session.
