#!/usr/bin/env python3
"""Simple CLI tool to interact with an AI coding agent via OpenAI API."""
import argparse
import json
import os
import sys
from typing import List

import requests


AGENT_NAME = "CodeSmith"


def _gather_codebase() -> str:
    """Collect contents of repository files for question mode."""
    parts: List[str] = []
    for root, _, files in os.walk("."):
        for name in files:
            if name.endswith(".py") or name.lower() == "readme.md":
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        parts.append(f"File: {path}\n{fh.read()}")
                except OSError:
                    continue
    return "\n\n".join(parts)


def _build_payload(prompt: str, mode: str) -> dict:
    """Create payload for OpenAI Chat Completions API."""
    if mode == "qa":
        context = _gather_codebase()
        system_content = (
            f"You are {AGENT_NAME}, an AI assistant answering questions about the NovaAtom codebase."
        )
        user_content = f"Repository contents:\n{context}\n\nQuestion: {prompt}"
    else:
        system_content = f"You are {AGENT_NAME}, an AI coding assistant."
        user_content = prompt

    return {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    }


def query_ai(prompt: str, mode: str) -> str:
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
        data=json.dumps(_build_payload(prompt, mode)),
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"API request failed: {response.text}")
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Interact with the CodeSmith agent")
    parser.add_argument(
        "prompt", nargs="+", help="Prompt or question for the agent"
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["coding", "qa"],
        default="coding",
        help="Select 'coding' for general coding help or 'qa' to ask about the repository.",
    )
    ns = parser.parse_args(argv)

    prompt = " ".join(ns.prompt)
    try:
        answer = query_ai(prompt, ns.mode)
    except RuntimeError as exc:
        print(exc)
        return 1
    print(f"{AGENT_NAME}: {answer}")
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main(sys.argv[1:]))
