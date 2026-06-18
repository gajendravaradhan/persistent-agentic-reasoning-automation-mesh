# PARAM WhatsApp Setup Guide

How to make PARAM reachable via WhatsApp using the Hermes gateway.

---

## Prerequisites

- **Hermes Agent** installed (`pip install hermes-agent` or from source)
- **Python 3.11+** (required by the Hermes WhatsApp adapter)
- **WhatsApp account** on your phone (any number, not tied to PARAM)
- PARAM project already set up at `~/projects/persistent-agentic-reasoning-automation-mesh/`

---

## Step 1: Install the Hermes gateway service

The gateway is a systemd/launchd service that keeps the WhatsApp connection alive.

```bash
hermes gateway install
```

This registers the gateway as a background service. On macOS it creates a LaunchAgent plist. On Linux it creates a systemd user unit.

Verify the service file exists:

```bash
# macOS
ls ~/Library/LaunchAgents/com.hermes.gateway.plist

# Linux
systemctl --user status hermes-gateway
```

---

## Step 2: Configure the environment

Create or edit `~/.hermes/.env`:

```bash
mkdir -p ~/.hermes
```

Add these variables:

```ini
# WhatsApp gateway
WHATSAPP_ENABLED=true
WHATSAPP_MODE=whatsapp-web
OWNER_JID=917022861123@s.whatsapp.net
```

| Variable | Value | Notes |
|----------|-------|-------|
| `WHATSAPP_ENABLED` | `true` | Turns on the WhatsApp adapter |
| `WHATSAPP_MODE` | `whatsapp-web` | Uses Baileys (WhatsApp Web protocol), no business API needed |
| `OWNER_JID` | Your WhatsApp JID | Format: `countrycode+number@s.whatsapp.net`. Only this number can send commands to PARAM |

To find your JID, the gateway prints it on first connect. You can also derive it: remove the `+` from your phone number, prefix with country code digits, append `@s.whatsapp.net`. Example: `+91 70228-61123` becomes `917022861123@s.whatsapp.net`.

---

## Step 3: Start the gateway

```bash
hermes gateway start
```

The gateway launches and waits for WhatsApp authentication.

Check logs to confirm it is running:

```bash
hermes gateway logs --follow
```

You should see output like:

```
[hermes] WhatsApp adapter initializing...
[hermes] Waiting for QR scan...
```

---

## Step 4: Scan the QR code

1. Open WhatsApp on your phone.
2. Go to **Settings** → **Linked Devices** → **Link a Device**.
3. Point your phone camera at the QR code displayed in the terminal (or the log output).
4. Wait for the "Connected" confirmation.

If the QR code does not appear in the terminal, check `hermes gateway logs`. The QR is printed as ASCII art in the log output during first launch.

After a successful scan, the logs will show:

```
[hermes] WhatsApp connected as <your number>
[hermes] Listening for messages from 917022861123@s.whatsapp.net
```

The gateway stores authentication state in `~/.hermes/auth_info/`. Do not delete this directory, or you will need to re-scan the QR.

---

## Step 5: Test the connection

Send a WhatsApp message to the connected number from the **OWNER_JID** phone. Try:

```
ping
```

PARAM should respond within a few seconds:

```
pong - PARAM online
```

If you get no response, proceed to the troubleshooting section below.

---

## Verification Checklist

- [ ] Message sent from OWNER_JID phone to the WhatsApp number
- [ ] Message received by PARAM (visible in `hermes gateway logs`)
- [ ] PARAM processes the message
- [ ] Response delivered back to the phone

All four steps must pass before the setup is complete.

---

## Security

**OWNER_JID restriction**: The gateway ignores messages from any JID not matching `OWNER_JID`. This prevents random people from sending commands to PARAM. If you need multiple authorized users, configure them through Hermes contacts (see `hermes contacts add`).

**Local-only credentials**: All authentication data lives in `~/.hermes/auth_info/` on the local machine. It never leaves the device. Protect this directory with file permissions:

```bash
chmod 700 ~/.hermes
chmod 600 ~/.hermes/auth_info/*
```

**Auth info backup**: WhatsApp sessions can expire. Back up the auth state so you can restore without re-scanning:

```bash
cp -r ~/.hermes/auth_info ~/.hermes/auth_info.backup
```

Restore it later with:

```bash
cp -r ~/.hermes/auth_info.backup ~/.hermes/auth_info
```

---

## Troubleshooting

### QR code not showing

1. Check the gateway is actually running: `hermes gateway status`
2. View logs: `hermes gateway logs --follow`
3. If the gateway started before and already has auth state, it will not show a QR. Delete `~/.hermes/auth_info/` to force a fresh QR scan.
4. Restart: `hermes gateway restart`

### Connection drops

WhatsApp Web connections can time out after prolonged inactivity. The gateway includes auto-reconnect logic. If it stays disconnected:

1. `hermes gateway restart`
2. Check your phone has an active internet connection (WhatsApp Web requires the phone to be online).
3. If reconnect fails repeatedly, delete `~/.hermes/auth_info/` and re-scan the QR.

### Logged out / "phone disconnected"

This happens when WhatsApp invalidates the session (e.g., phone was offline too long, or you logged out from Linked Devices).

1. Delete the stale auth: `rm -rf ~/.hermes/auth_info/`
2. Restart the gateway: `hermes gateway restart`
3. Scan the QR code again (Step 4).

To reduce this risk, keep the phone online and connected to the internet.

### Messages not delivered to PARAM

- Confirm the sender JID matches `OWNER_JID` exactly (including `@s.whatsapp.net` suffix).
- Check gateway logs for errors: `hermes gateway logs --since 5m`
- Verify `WHATSAPP_ENABLED=true` in `~/.hermes/.env`

### PARAM responds but message never arrives on phone

- The WhatsApp Web protocol occasionally drops outbound delivery. The gateway retries once.
- Check logs for delivery errors.
- If persistent, restart the gateway.

---

## Old Bridge Deprecation

The existing Node.js WhatsApp bridge at `~/whatsapp-opencode-bridge/` (Baileys + Node.js) is being replaced by the Hermes built-in WhatsApp adapter.

### Migration steps

1. **Stop the old bridge** (if running):

   ```bash
   cd ~/whatsapp-opencode-bridge
   pm2 stop whatsapp-bridge   # or however it is managed
   ```

2. **Complete the Hermes setup** using Steps 1-5 above.

3. **Verify PARAM responds** to WhatsApp messages through Hermes.

4. **Remove the old bridge** (after confirming Hermes works):

   ```bash
   pm2 delete whatsapp-bridge
   rm -rf ~/whatsapp-opencode-bridge
   ```

The old bridge's auth state is not compatible with Hermes. You will need to scan a new QR code during the Hermes setup.

---

## Summary

| Step | Command |
|------|---------|
| Install | `hermes gateway install` |
| Configure | Edit `~/.hermes/.env` |
| Start | `hermes gateway start` |
| Auth | Scan QR from phone |
| Test | Send `ping` from WhatsApp |
| Monitor | `hermes gateway logs --follow` |

PARAM is now reachable on WhatsApp. Commands sent from the OWNER_JID will be processed like any other PARAM input channel.

---

*Last updated: June 2026*
