# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## Google Workspace (gog CLI)

**Setup complete ✅** - Authentication configured for niamh@telnyx.com

**To use in any session:**
```bash
source /Users/niamhcollins/clawd/.env.gog
```

**Common commands:**
```bash
# Gmail
gog gmail search 'newer_than:1d is:inbox' --max 10
gog gmail send --to someone@example.com --subject "Hi" --body "Message"

# Calendar  
gog calendar events primary --from "2026-03-04T00:00:00Z" --to "2026-03-04T23:59:59Z"

# Drive
gog drive search "quarterly report" --max 5

# Sheets
gog sheets get <sheetId> "Sheet1!A1:D10" --json
```

**Config details:**
- Account: niamh@telnyx.com
- Services: gmail,calendar,drive,contacts,docs,sheets  
- Keyring: file-based (avoids macOS keychain)
- Auth expires: Indefinitely with regular use

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.