#!/usr/bin/env python3
"""Simple CLI tool to interact with an AI coding agent via OpenAI API."""
import json
import os
import sys
from typing import List

import requests


AGENT_NAME = "CodeSmith"


def _build_payload(prompt: str) -> dict:
    """Create payload for OpenAI Chat Completions API."""
    return {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": f"You are {AGENT_NAME}, an AI coding assistant.",
            },
            {"role": "user", "content": prompt},
        ],
    }


def query_ai(prompt: str) -> str:
    """Send a prompt to the AI model and return the response text."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(_build_payload(prompt)),
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"API request failed: {response.text}")
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def main(args: List[str]) -> int:
    if not args:
        print("Usage: python ai_cli.py 'your prompt'")
        return 1
    prompt = " ".join(args)
    try:
        answer = query_ai(prompt)
    except RuntimeError as exc:
        print(exc)
        return 1
    print(f"{AGENT_NAME}: {answer}")
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main(sys.argv[1:]))
