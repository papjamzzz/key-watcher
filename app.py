import os
import sqlite3
import threading
import time
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DB_PATH = "data/keys.db"
CHECK_INTERVAL = 300  # 5 min

PROVIDERS = {
    # ── AI Models ──────────────────────────────────────────────────────
    "openai": {
        "name": "OpenAI", "model": "GPT-4o · 5i",
        "env": "OPENAI_API_KEY", "color": "#74aa9c", "group": "AI",
    },
    "openai_withyou": {
        "name": "OpenAI", "model": "GPT-4o · WithYou",
        "env": "WITHYOU_OPENAI_API_KEY", "color": "#74aa9c", "group": "AI",
    },
    "anthropic": {
        "name": "Anthropic", "model": "Claude · 5i",
        "env": "ANTHROPIC_API_KEY", "color": "#d4a27f", "group": "AI",
    },
    "anthropic_apps": {
        "name": "Anthropic", "model": "Claude · Apps",
        "env": "ANTHROPIC_API_KEY_APPS", "color": "#d4a27f", "group": "AI",
    },
    "google": {
        "name": "Google", "model": "Gemini · 5i",
        "env": "GOOGLE_API_KEY", "color": "#4285f4", "group": "AI",
    },
    "gemini_withyou": {
        "name": "Google", "model": "Gemini · WithYou",
        "env": "WITHYOU_GEMINI_API_KEY", "color": "#4285f4", "group": "AI",
    },
    "grok": {
        "name": "xAI", "model": "Grok · 5i",
        "env": "GROK_API_KEY", "color": "#aaaaaa", "group": "AI",
    },
    "mistral": {
        "name": "Mistral", "model": "Mistral Large · 5i",
        "env": "MISTRAL_API_KEY", "color": "#ff7000", "group": "AI",
    },
    "elevenlabs": {
        "name": "ElevenLabs", "model": "TTS · WithYou",
        "env": "ELEVENLABS_API_KEY", "color": "#f9c846", "group": "AI",
    },
    # ── Media ──────────────────────────────────────────────────────────
    "tmdb": {
        "name": "TMDB", "model": "Movie DB · StreamFader",
        "env": "TMDB_API_KEY", "color": "#01b4e4", "group": "Media",
    },
    "omdb": {
        "name": "OMDB", "model": "Movie DB · StreamFader",
        "env": "OMDB_API_KEY", "color": "#f5c518", "group": "Media",
    },
    "mdblist": {
        "name": "MDBList", "model": "Lists · StreamFader",
        "env": "MDBLIST_API_KEY", "color": "#6366f1", "group": "Media",
    },
    # ── Data / Finance ─────────────────────────────────────────────────
    "odds": {
        "name": "Odds API", "model": "Sports Lines · Trader",
        "env": "ODDS_API_KEY", "color": "#22c55e", "group": "Data",
    },
    # ── Comms ──────────────────────────────────────────────────────────
    "twilio": {
        "name": "Twilio", "model": "SMS · Trader",
        "env": "TWILIO_ACCOUNT_SID", "env2": "TWILIO_AUTH_TOKEN",
        "color": "#f22f46", "group": "Comms",
    },
}


# ── DB ──────────────────────────────────────────────────────────────────────

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            status TEXT NOT NULL,
            status_code INTEGER,
            latency_ms INTEGER,
            error TEXT,
            checked_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_check(provider, status, status_code, latency_ms, error):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO checks (provider, status, status_code, latency_ms, error, checked_at) VALUES (?,?,?,?,?,?)",
        (provider, status, status_code, latency_ms, error, datetime.utcnow().isoformat())
    )
    c.execute("""
        DELETE FROM checks WHERE provider=? AND id NOT IN (
            SELECT id FROM checks WHERE provider=? ORDER BY id DESC LIMIT 100
        )
    """, (provider, provider))
    conn.commit()
    conn.close()


def get_latest(provider):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM checks WHERE provider=? ORDER BY id DESC LIMIT 1", (provider,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_history(provider, limit=20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT status FROM checks WHERE provider=? ORDER BY id DESC LIMIT ?", (provider, limit))
    rows = c.fetchall()
    conn.close()
    return [r["status"] for r in reversed(rows)]


# ── Check functions ──────────────────────────────────────────────────────────
# Each returns (http_status_code, response_object_or_None)
# Return 401 from body checks to trigger "invalid" classification.

def check_openai(key, _=None):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
        timeout=15,
    )
    return r.status_code, r


def check_anthropic(key, _=None):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
        timeout=15,
    )
    return r.status_code, r


def check_google(key, _=None):
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
        json={"contents": [{"parts": [{"text": "hi"}]}], "generationConfig": {"maxOutputTokens": 1}},
        timeout=15,
    )
    return r.status_code, r


def check_grok(key, _=None):
    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "grok-2-latest", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
        timeout=15,
    )
    return r.status_code, r


def check_mistral(key, _=None):
    r = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "mistral-large-latest", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
        timeout=15,
    )
    return r.status_code, r


def check_elevenlabs(key, _=None):
    r = requests.get(
        "https://api.elevenlabs.io/v1/user",
        headers={"xi-api-key": key},
        timeout=15,
    )
    return r.status_code, r


def check_tmdb(key, _=None):
    r = requests.get(
        f"https://api.themoviedb.org/3/configuration?api_key={key}",
        timeout=15,
    )
    return r.status_code, r


def check_omdb(key, _=None):
    r = requests.get(
        f"http://www.omdbapi.com/?apikey={key}&t=inception",
        timeout=15,
    )
    if r.status_code == 200:
        try:
            if r.json().get("Response") == "False":
                return 401, r  # body says invalid
        except Exception:
            pass
    return r.status_code, r


def check_mdblist(key, _=None):
    r = requests.get(
        f"https://mdblist.com/api/?apikey={key}&s=inception",
        timeout=15,
    )
    if r.status_code == 200:
        try:
            data = r.json()
            if data.get("response") is False or "invalid" in str(data.get("message", "")).lower():
                return 401, r
        except Exception:
            pass
    return r.status_code, r


def check_odds(key, _=None):
    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/?apiKey={key}",
        timeout=15,
    )
    return r.status_code, r


def check_twilio(account_sid, auth_token):
    r = requests.get(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json",
        auth=(account_sid, auth_token),
        timeout=15,
    )
    return r.status_code, r


CHECK_FNS = {
    "openai":        check_openai,
    "openai_withyou": check_openai,
    "anthropic":     check_anthropic,
    "anthropic_apps": check_anthropic,
    "google":        check_google,
    "gemini_withyou": check_google,
    "grok":          check_grok,
    "mistral":       check_mistral,
    "elevenlabs":    check_elevenlabs,
    "tmdb":          check_tmdb,
    "omdb":          check_omdb,
    "mdblist":       check_mdblist,
    "odds":          check_odds,
    "twilio":        check_twilio,
}


def classify(status_code):
    if status_code == 200:
        return "live"
    elif status_code in (401, 403):
        return "invalid"
    elif status_code == 429:
        return "quota"
    elif status_code and status_code >= 500:
        return "provider_down"
    else:
        return "error"


def run_check(provider_id):
    cfg = PROVIDERS[provider_id]
    key = os.getenv(cfg["env"], "").strip()
    if not key:
        save_check(provider_id, "no_key", None, None, "Key not set in .env")
        return

    key2 = os.getenv(cfg.get("env2", ""), "").strip() if cfg.get("env2") else None
    fn = CHECK_FNS[provider_id]
    t0 = time.time()
    try:
        code, resp = fn(key, key2)
        latency = int((time.time() - t0) * 1000)
        status = classify(code)
        error = None
        if status != "live":
            try:
                error = resp.text[:200]
            except Exception:
                error = f"HTTP {code}"
        save_check(provider_id, status, code, latency, error)
    except requests.exceptions.Timeout:
        save_check(provider_id, "timeout", None, None, "Request timed out")
    except requests.exceptions.ConnectionError as e:
        save_check(provider_id, "unreachable", None, None, str(e)[:200])
    except Exception as e:
        save_check(provider_id, "error", None, None, str(e)[:200])


def check_all():
    for pid in PROVIDERS:
        run_check(pid)


def background_loop():
    time.sleep(3)
    while True:
        check_all()
        time.sleep(CHECK_INTERVAL)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", providers=PROVIDERS)


@app.route("/api/status")
def api_status():
    result = {}
    for pid, cfg in PROVIDERS.items():
        latest = get_latest(pid)
        history = get_history(pid)
        result[pid] = {
            "name": cfg["name"],
            "model": cfg["model"],
            "color": cfg["color"],
            "group": cfg.get("group", ""),
            "latest": latest,
            "history": history,
        }
    return jsonify(result)


@app.route("/api/check/<provider_id>", methods=["POST"])
def api_check_one(provider_id):
    if provider_id not in PROVIDERS:
        return jsonify({"error": "unknown provider"}), 404
    run_check(provider_id)
    return jsonify(get_latest(provider_id))


@app.route("/api/check/all", methods=["POST"])
def api_check_all():
    check_all()
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    app.run(host="127.0.0.1", port=5563, debug=False)
