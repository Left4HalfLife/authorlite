# Existing imports and setup...
# Existing imports and setup...
\"\"\"Simple Flask app that forwards requests to LM Studio API.

This proof of concept reads configuration from `.env` using the
`python-dotenv` package.  It exposes a single endpoint `/chat` which
accepts a JSON payload with a `prompt` field and forwards it to the
configured LM Studio instance.  The response is returned verbatim.

The app writes each request/response pair as a JSON file in the
`data` directory so that the container can persist them across restarts.
\"\"\"

import json
import os
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env located next to this file.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

ENDPOINT = os.getenv("ENDPOINT")
API_KEY = os.getenv("LM_STUDIO_API_KEY")

if not ENDPOINT or not API_KEY:
    raise RuntimeError("ENDPOINT and LM_STUDIO_API_KEY must be set in .env")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _save_interaction(prompt: str, response: dict):
    """Persist the prompt and response to a timestamped JSON file."""
    filename = DATA_DIR / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as fp:
        json.dump({"prompt": prompt, "response": response}, fp, indent=2)


# ---------------------------------------------------------------------------
# Helper: fetch available models from LM Studio
def _fetch_models():
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        resp = requests.get(f"{ENDPOINT}/v1/models", headers=headers, timeout=5)
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]
    except Exception as e:
        app.logger.error(f"Failed to fetch models: {e}")
        return []

@app.route("/models", methods=["GET"])
def models_route():
    models = _fetch_models()
    # Return as JSON or can serve dash.html for model discovery
    if request.args.get('html'):
        return render_template("dash.html", models=models, endpoint=ENDPOINT, apiKey=API_KEY)
    return jsonify({"models": models})


@app.route("/", endpoint="index_page")
def index():
    # Serve the new dashboard with model info
    models = _fetch_models()
    return render_template("dash.html", models=models, endpoint=ENDPOINT, apiKey=API_KEY)

# ---------------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    prompt = data.get("prompt")
    if not prompt:
        return jsonify(error="'prompt' field required"), 400

    # Use model from client if provided, otherwise use default
    model = data.get("model", "gpt-oss-20b")

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    # Ensure we don't double‑prepend /v1
    base = ENDPOINT.rstrip("/")
    resp = requests.post(f"{base}/v1/chat/completions", headers=headers, json=payload)

    if resp.status_code != 200:
        app.logger.error(f"LM Studio returned {resp.status_code}: {resp.text}")
        return jsonify(error="LM Studio API error", details=resp.text), resp.status_code

    result = resp.json()
    _save_interaction(prompt, result)
    return jsonify(result)

if __name__ == "__main__":
    # Run on port 3846 as requested.
    app.run(host="0.0.0.0", port=3846)