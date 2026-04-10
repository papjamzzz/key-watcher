# Key Watcher — Re-Entry File
*Re-entry: key-watcher*

## What This Is
API key health monitor for all 5i providers. Runs background checks every 5 minutes against live APIs using minimal 1-token requests. Dark theme dashboard with per-key status, latency, error details, and history sparkline.

## Re-Entry Phrase
"Re-entry: key-watcher"

## Current Status
LIVE locally. Port 5563.

## File Structure
```
key-watcher/
├── app.py              ← Flask, port 5563. Background thread checks all keys every 5min.
├── templates/
│   └── index.html      ← Dark theme dashboard, auto-refresh every 30s
├── static/logo.png
├── data/keys.db        ← SQLite, auto-created, gitignored
├── requirements.txt
├── Makefile
├── launch.command
├── .env                ← Copy keys from ~/5i/.env
├── .env.example
└── CLAUDE.md
```

## How to Run
```bash
cd ~/key-watcher
make setup   # first time only
make run     # http://127.0.0.1:5563
```

## Providers Monitored
| ID | Provider | Model | Env Var |
|----|----------|-------|---------|
| openai | OpenAI | GPT-4o | OPENAI_API_KEY |
| anthropic | Anthropic | Claude | ANTHROPIC_API_KEY |
| google | Google | Gemini | GOOGLE_API_KEY |
| grok | xAI | Grok | GROK_API_KEY |
| mistral | Mistral | Mistral Large | MISTRAL_API_KEY |

## Status Codes
| Status | Meaning |
|--------|---------|
| live | 200 OK — key healthy |
| invalid | 401/403 — key rejected |
| quota | 429 — rate limited or quota exhausted |
| provider_down | 5xx — provider error |
| timeout | Request took >15s |
| unreachable | Connection failed |
| no_key | Key not set in .env |

## API Routes
- `GET /` — Dashboard
- `GET /api/status` — JSON status for all providers
- `POST /api/check/<provider_id>` — Force-check one provider
- `POST /api/check/all` — Force-check all providers

## Key Technical Decisions
- Background thread with time.sleep (no APScheduler dependency)
- SQLite stores last 100 checks per provider
- Minimal 1-token API calls to avoid wasting quota
- 15s timeout per check

## Port
5563

## GitHub
https://github.com/papjamzzz/key-watcher

---
*Last updated: 2026-04-10*
