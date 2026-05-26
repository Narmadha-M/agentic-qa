"""
claude_client: calls Claude via OpenRouter (openrouter.ai).
Reads OPENROUTER_API_KEY from the environment.
"""

import os
import json
import urllib.request
import urllib.error
from utils.logger import log

MODEL = "anthropic/claude-sonnet-4-5"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_TOKENS = 4096


def ask_claude(prompt: str, system: str = "") -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Set OPENROUTER_API_KEY (or ANTHROPIC_API_KEY) before running.\n"
            "Example: $env:OPENROUTER_API_KEY = 'sk-or-v1-...'"
        )

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": messages,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"[Claude API] HTTP {e.code}: {error_body}")
        raise
