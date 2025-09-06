#!/usr/bin/env python3
"""Simple CLI tool to interact with an AI coding agent via OpenAI API.

The OpenAI API key is stored in a small JSON settings file so that it can be
shared between the desktop editor and this CLI. The key must be entered via the
CodeSmith settings page in the editor.
"""
import argparse
import json
import os
import sys
from typing import List

import requests


AGENT_NAME = "CodeSmith"
YACY_SEARCH_URL = os.environ.get("YACY_SEARCH_URL", "http://localhost:8090/yacysearch.json")

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".codesmith_settings.json")


def load_settings() -> dict:
    """Load persisted settings for CodeSmith.

    Returns an empty dictionary if the settings file does not exist or cannot
    be read.
    """
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_settings(settings: dict) -> None:
    """Persist CodeSmith settings to disk."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
        json.dump(settings, fh)


def load_api_key() -> str:
    """Retrieve the stored OpenAI API key.

    Raises:
        RuntimeError: If the key has not been configured via the CodeSmith
            settings page.
    """
    api_key = load_settings().get("api_key")
    if not api_key:
        raise RuntimeError(
            "OpenAI API key not configured. Set it through the CodeSmith settings page."
        )
    return api_key


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


def _create_search_query(prompt: str) -> str:
    """Ask the AI to craft a concise web search query."""
    try:
        api_key = load_api_key()
    except RuntimeError:
        return prompt
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Craft a concise, well-structured web search query for the following text.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 32,
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=15,
        )
        if response.status_code != 200:
            return prompt
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return prompt


def _web_search(query: str, max_results: int = 5) -> str:
    """Perform a YaCy web search and return result snippets.

    Besides the title and URL, a short text snippet is returned for each result
    to provide more context. Network failures or unexpected responses are
    handled gracefully so that the main workflow continues even if no web
    results are available.
    """

    try:
        resp = requests.get(
            YACY_SEARCH_URL,
            params={"query": query, "rows": max_results},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # pragma: no cover - network errors
        return f"Web search failed: {exc}"

    items = data.get("channels", [{}])[0].get("items", [])
    results: List[str] = []
    for item in items[:max_results]:
        title = item.get("title", "No title").strip()
        link = item.get("link") or ""
        snippet = (
            item.get("description")
            or item.get("about")
            or ""
        ).strip()
        snippet = " ".join(snippet.split())  # collapse whitespace
        if len(snippet) > 160:
            snippet = f"{snippet[:157]}..."
        results.append(f"{title} - {link}\n  {snippet}" if snippet else f"{title} - {link}")

    if not results:
        return "No web results found."
    return "\n".join(results)


def _build_payload(prompt: str, mode: str) -> dict:
    """Create payload for OpenAI Chat Completions API."""
    search_query = _create_search_query(prompt)
    search_info = _web_search(search_query)
    if mode == "qa":
        context = _gather_codebase()
        system_content = (
            f"You are {AGENT_NAME}, an AI assistant answering questions about the NovaAtom codebase."
        )
        user_content = (
            f"Repository contents:\n{context}\n\nSearch query: {search_query}\nWeb search results:\n{search_info}\n\nQuestion: {prompt}"
        )
    else:
        system_content = f"You are {AGENT_NAME}, an AI coding assistant."
        user_content = (
            f"Search query: {search_query}\nWeb search results:\n{search_info}\n\nPrompt: {prompt}"
        )

    return {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    }


def _build_edit_payload(file_content: str, instructions: str) -> dict:
    """Create payload instructing the model to modify file contents."""
    search_query = _create_search_query(instructions)
    search_info = _web_search(search_query)
    system_content = (
        f"You are {AGENT_NAME}, an AI coding assistant that edits files. "
        "Return only the updated file contents without additional commentary."
    )
    user_content = (
        f"Search query: {search_query}\nWeb search results:\n{search_info}\n\n"
        f"Current file contents:\n{file_content}\n\n"
        f"Edit instructions: {instructions}"
    )
    return {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
    }


def query_ai(prompt: str, mode: str) -> str:
    """Send a prompt to the AI model and return the response text."""
    api_key = load_api_key()

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


def edit_file(path: str, instructions: str) -> None:
    """Use the AI agent to edit a local file in place."""
    api_key = load_api_key()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            original = fh.read()
    except OSError as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(_build_edit_payload(original, instructions)),
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"API request failed: {response.text}")
    data = response.json()
    new_content = data["choices"][0]["message"]["content"]
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_content)
    except OSError as exc:
        raise RuntimeError(f"Failed to write {path}: {exc}")


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
    parser.add_argument(
        "--edit",
        metavar="FILE",
        help="Edit FILE in place using the prompt as instructions.",
    )
    ns = parser.parse_args(argv)

    prompt = " ".join(ns.prompt)
    try:
        if ns.edit:
            edit_file(ns.edit, prompt)
            print(f"{AGENT_NAME}: Updated {ns.edit}")
        else:
            answer = query_ai(prompt, ns.mode)
            print(f"{AGENT_NAME}: {answer}")
    except RuntimeError as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main(sys.argv[1:]))
