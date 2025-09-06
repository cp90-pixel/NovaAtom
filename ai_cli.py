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


def _web_search(query: str, max_results: int = 5) -> str:
    """Perform a DuckDuckGo web search and return top result snippets.

    DuckDuckGo's HTML endpoint is scraped because it does not require an API
    key. Only the title and URL of each result are returned to keep the context
    compact. Network or parsing failures are ignored so that lack of search
    results does not break the main workflow.
    """

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        html = requests.get(
            "https://duckduckgo.com/html/", params={"q": query}, headers=headers, timeout=10
        ).text
    except Exception as exc:  # pragma: no cover - network errors
        return f"Web search failed: {exc}"

    import html as html_module
    import re
    pattern = re.compile(
        r'result__a[^>]*?href="(.*?)"[^>]*?>(.*?)</a>', re.IGNORECASE | re.DOTALL
    )
    results: List[str] = []
    for url, title in pattern.findall(html):
        # DuckDuckGo wraps result URLs, extract the real target if possible
        if url.startswith("//duckduckgo.com/l/?"):  # redirect link
            from urllib.parse import parse_qs, urlparse, unquote

            qs = parse_qs(urlparse(url).query)
            real_url = unquote(qs.get("uddg", [url])[0])
        else:
            real_url = url
        clean_title = html_module.unescape(re.sub("<.*?>", "", title)).strip()
        results.append(f"{clean_title} - {real_url}")
        if len(results) >= max_results:
            break

    if not results:
        return "No web results found."
    return "\n".join(results)


def _build_payload(prompt: str, mode: str) -> dict:
    """Create payload for OpenAI Chat Completions API."""
    search_info = _web_search(prompt)
    if mode == "qa":
        context = _gather_codebase()
        system_content = (
            f"You are {AGENT_NAME}, an AI assistant answering questions about the NovaAtom codebase."
        )
        user_content = (
            f"Repository contents:\n{context}\n\nWeb search results:\n{search_info}\n\nQuestion: {prompt}"
        )
    else:
        system_content = f"You are {AGENT_NAME}, an AI coding assistant."
        user_content = f"Web search results:\n{search_info}\n\nPrompt: {prompt}"

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
