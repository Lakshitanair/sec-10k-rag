import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

_default = "gemini-3.8-flash,gemini-3.5-flash,gemini-3.1-flash-lite"
MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", _default).split(",") if m.strip()]
if os.getenv("GEMINI_MODEL"):
    MODELS.insert(0, os.getenv("GEMINI_MODEL").strip())
    MODELS = list(dict.fromkeys(MODELS))  # remove duplicates, keep order
MIN_GAP = float(os.getenv("GEMINI_MIN_GAP", "6"))  # seconds between calls
THINKING = os.getenv("GEMINI_THINKING_LEVEL", "")  # empty = model default
TIMEOUT = 60
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_last_call = 0.0
LAST_MODEL = ""  # which model produced the latest answer


def generate(system, user, tries_per_model=3):
    global _last_call, LAST_MODEL
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is missing from your .env file")
    config = {"temperature": 0.0, "maxOutputTokens": 2000}
    if THINKING:
        config["thinkingConfig"] = {"thinkingLevel": THINKING}
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": config,
    }
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    last_error = ""
    for model in MODELS:
        for attempt in range(tries_per_model):
            gap = MIN_GAP - (time.time() - _last_call)
            if gap > 0:
                time.sleep(gap)
            try:
                resp = requests.post(URL.format(model=model), headers=headers, json=body, timeout=TIMEOUT)
            except requests.exceptions.RequestException as exc:
                _last_call = time.time()
                last_error = f"{model}: {type(exc).__name__}"
                print(f"  [{last_error}]", file=sys.stderr)
            else:
                _last_call = time.time()
                if resp.status_code == 404:
                    last_error = f"{model}: not available"
                    print(f"  [{model} not available, trying next model]", file=sys.stderr)
                    break
                if resp.status_code in (429, 500, 503):
                    last_error = f"{model}: {resp.status_code}"
                    print(f"  [{model} returned {resp.status_code}]", file=sys.stderr)
                elif resp.status_code >= 400:
                    raise RuntimeError(f"Gemini error {resp.status_code}: {resp.text[:300]}")
                else:
                    data = resp.json()
                    LAST_MODEL = model
                    try:
                        parts = data["candidates"][0]["content"]["parts"]
                        return "".join(p.get("text", "") for p in parts).strip()
                    except (KeyError, IndexError):
                        return ""  # blocked or empty response
            if attempt < tries_per_model - 1:
                time.sleep(5 * 3 ** attempt)  # 5, then 15 seconds
        print(f"  [moving on from {model}]", file=sys.stderr)
    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")