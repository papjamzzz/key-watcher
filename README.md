<p align="center">
  <img src="static/logo.png" width="120" alt="Key Watcher logo"/>
</p>

# Key Watcher — API Key Health Monitor

> **Know before it breaks.**

Real-time health monitoring for every API key in your stack. One dashboard. Every provider. Live status, grouped by service type.

---

## What It Does

- **Live health checks** — pings every configured API key every 5 minutes via authenticated test calls
- **Provider grouping** — keys organized by type: AI Models, Media, Data, Comms
- **Status LEDs** — green for valid, red for invalid or expired, amber for unconfigured
- **Per-app attribution** — shows which project each key belongs to (5i, WithYou, Trader, StreamFader)
- **Zero config** — reads from your `.env` automatically, no manual entry

---

## Providers Monitored

| Group | Provider | Used By |
|-------|----------|---------|
| AI | OpenAI (GPT-4o) | 5i, WithYou |
| AI | Anthropic (Claude) | 5i, all apps |
| AI | Google (Gemini) | 5i, WithYou |
| AI | xAI (Grok) | 5i |
| AI | Mistral Large | 5i |
| AI | ElevenLabs (TTS) | WithYou |
| Media | TMDB | StreamFader |
| Media | OMDB | StreamFader |
| Media | MDBList | StreamFader |
| Data | Odds API | KK Trader |
| Comms | Twilio | KK Trader |

---

## Setup

```bash
git clone https://github.com/papjamzzz/key-watcher.git
cd key-watcher
cp .env.example .env
# Keys are read from your existing .env — no extra config needed
make setup
make run
```

Opens at `http://127.0.0.1:5563`

Or double-click `launch.command` on Mac.

---

## How It Works

```
.env file (shared across all apps)
  └── app.py — reads PROVIDERS config
        every 5 minutes → authenticated test call per provider
              ↓
        SQLite (data/keys.db) — stores last check result + timestamp
              ↓
        Flask (port 5563) — serves status as JSON
              ↓
        Dashboard — live LED grid, grouped by service type
```

---

## Stack

Python · Flask · SQLite · Vanilla JS · JetBrains Mono

No external UI frameworks. Runs local. Keys never leave your machine.

---

## Part of Creative Konsoles

Built by [Creative Konsoles](https://creativekonsoles.com) — tools built using thought.

**[creativekonsoles.com](https://creativekonsoles.com)** &nbsp;·&nbsp; support@creativekonsoles.com

<!-- repo maintenance: 2026-04-10 -->
