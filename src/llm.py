import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MIN_GAP = float(os.getenv("GEMINI_MIN_GAP", "6"))  # seconds between calls
THINKING = os.getenv("GEMINI_THINKING_LEVEL", "")  # e.g. low; empty = model default
TIMEOUT = 120
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_last_call = 0.0


def generate(system, user, retries=5):
    global _last_call
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
    for attempt in range(retries):
        gap = MIN_GAP - (time.time() - _last_call)
        if gap > 0:
            time.sleep(gap)
        try:
            resp = requests.post(URL.format(model=MODEL), headers=headers, json=body, timeout=TIMEOUT)
        except requests.exceptions.RequestException as exc:
            _last_call = time.time()
            last_error = f"{type(exc).__name__}"
            wait = 5 * 2 ** attempt
            print(f"  [{last_error}, retrying in {wait}s]", file=sys.stderr)
            time.sleep(wait)
            continue
        _last_call = time.time()
        if resp.status_code in (429, 500, 503):
            last_error = f"{resp.status_code}: {resp.text[:300]}"
            wait = 5 * 2 ** attempt
            print(f"  [Gemini returned {resp.status_code}, retrying in {wait}s]", file=sys.stderr)
            time.sleep(wait)
            continue
        if resp.status_code >= 400:
            raise RuntimeError(f"Gemini error {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError):
            return ""  # blocked or empty response
    raise RuntimeError(f"Gemini kept failing. Last error: {last_error}")