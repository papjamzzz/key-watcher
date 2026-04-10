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
CHECK_INTERVAL = 300  # seconds (5 min)

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "model": "GPT-4o",
        "env": "OPENAI_API_KEY",
        "color": "#74aa9c",
    },
    "anthropic": {
        "name": "Anthropic",
        "model": "Claude",
        "env": "ANTHROPIC_API_KEY",
        "color": "#d4a27f",
    },
    "google": {
        "name": "Google",
        "model": "Gemini",
        "env": "GOOGLE_API_KEY",
        "color": "#4285f4",
    },
    "grok": {
        "name": "xAI",
        "model": "Grok",
        "env": "GROK_API_KEY",
        "color": "#aaaaaa",
    },
    "mistral": {
        "name": "Mistral",
        "model": "Mistral Large",
        "env": "MISTRAL_API_KEY",
        "color": "#ff7000",
    },
}


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
    # Keep only last 100 checks per provider
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
    c.execute(
        "SELECT * FROM checks WHERE provider=? ORDER BY id DESC LIMIT 1",
        (provider,)
    )
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_history(provider, limit=20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT status FROM checks WHERE provider=? ORDER BY id DESC LIMIT ?",
        (provider, limit)
    )
    rows = c.fetchall()
    conn.close()
    return [r["status"] for r in reversed(rows)]


def check_openai(key):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    return r.status_code, r


def check_anthropic(key):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {"model": "claude-haiku-4-5-20251001", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    return r.status_code, r


def check_google(key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    body = {
        "contents": [{"parts": [{"text": "hi"}]}],
        "generationConfig": {"maxOutputTokens": 1}
    }
    r = requests.post(url, json=body, timeout=15)
    return r.status_code, r


def check_grok(key):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"model": "grok-2-latest", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    return r.status_code, r


def check_mistral(key):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"model": "mistral-large-latest", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    return r.status_code, r


CHECK_FNS = {
    "openai": check_openai,
    "anthropic": check_anthropic,
    "google": check_google,
    "grok": check_grok,
    "mistral": check_mistral,
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

    fn = CHECK_FNS[provider_id]
    t0 = time.time()
    try:
        code, resp = fn(key)
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
    time.sleep(3)  # small delay on startup
    while True:
        check_all()
        time.sleep(CHECK_INTERVAL)


# ── Routes ──────────────────────────────────────────────────────────────────

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
            "latest": latest,
            "history": history,
        }
    return jsonify(result)


@app.route("/api/check/<provider_id>", methods=["POST"])
def api_check_one(provider_id):
    if provider_id not in PROVIDERS:
        return jsonify({"error": "unknown provider"}), 404
    run_check(provider_id)
    latest = get_latest(provider_id)
    return jsonify(latest)


@app.route("/api/check/all", methods=["POST"])
def api_check_all():
    check_all()
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    app.run(host="127.0.0.1", port=5563, debug=False)
