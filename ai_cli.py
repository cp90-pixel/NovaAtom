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
from typing import List, Optional

import requests

from semantic_router import Route, SemanticRouter
from semantic_router.llms import OpenAILLM
from semantic_router.schema import Message

try:  # Optional dependency for listing models
    from openai import OpenAI
except Exception:  # pragma: no cover - handled when SDK missing
    OpenAI = None  # type: ignore


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


def _create_search_query(prompt: str, model: str) -> str:
    """Ask the selected model to craft a concise web search query."""
    try:
        api_key = load_api_key()
        router = get_router(api_key)
    except RuntimeError:
        return prompt
    messages = [
        Message(
            role="system",
            content="Craft a concise, well-structured web search query for the following text.",
        ),
        Message(role="user", content=prompt),
    ]
    try:
        route = router.check_for_matching_routes(model)
        llm = route.llm if route and route.llm else router.llm
        if llm is None:
            return prompt
        return llm(messages).strip()
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


_router: Optional[SemanticRouter] = None
_model_cache: List[str] = []


def list_openai_models(api_key: str) -> List[str]:
    """Return available OpenAI model IDs.

    Falls back to ``gpt-4o-mini`` if fetching fails or the SDK is absent.
    """
    global _model_cache
    if _model_cache:
        return _model_cache
    if OpenAI is None:
        _model_cache = ["gpt-4o-mini"]
        return _model_cache
    try:
        client = OpenAI(api_key=api_key)
        resp = client.models.list()
        models = [m.id for m in resp.data if m.id.startswith("gpt")]
        _model_cache = models or ["gpt-4o-mini"]
    except Exception:  # pragma: no cover - network or auth issues
        _model_cache = ["gpt-4o-mini"]
    return _model_cache


def get_router(api_key: str) -> SemanticRouter:
    """Initialize or return a cached Semantic Router for all models."""
    global _router
    if _router is None:
        models = list_openai_models(api_key)
        routes: List[Route] = []
        default_llm: Optional[OpenAILLM] = None
        for model in models:
            llm = OpenAILLM(name=model, openai_api_key=api_key)
            routes.append(Route(name=model, utterances=[model], llm=llm))
            if default_llm is None:
                default_llm = llm
        if default_llm is None:  # pragma: no cover - safeguard
            default_llm = OpenAILLM(name="gpt-4o-mini", openai_api_key=api_key)
            routes.append(Route(name="gpt-4o-mini", utterances=["gpt-4o-mini"], llm=default_llm))
        _router = SemanticRouter(llm=default_llm, routes=routes)
    return _router


def _build_messages(prompt: str, mode: str, model: str) -> List[Message]:
    """Create messages for the OpenAI model via Semantic Router."""
    search_query = _create_search_query(prompt, model)
    search_info = _web_search(search_query)
    if mode == "qa":
        context = _gather_codebase()
        system_content = (
            f"You are {AGENT_NAME}, an AI assistant answering questions about the NovaAtom codebase."
        )
        user_content = (
            f"Repository contents:\n{context}\n\nSearch query: {search_query}\n"
            f"Web search results:\n{search_info}\n\nQuestion: {prompt}"
        )
    else:
        system_content = f"You are {AGENT_NAME}, an AI coding assistant."
        user_content = (
            f"Search query: {search_query}\nWeb search results:\n{search_info}\n\nPrompt: {prompt}"
        )
    return [
        Message(role="system", content=system_content),
        Message(role="user", content=user_content),
    ]


def _build_edit_messages(file_content: str, instructions: str, model: str) -> List[Message]:
    """Create messages instructing the model to modify file contents."""
    search_query = _create_search_query(instructions, model)
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
    return [
        Message(role="system", content=system_content),
        Message(role="user", content=user_content),
    ]


def query_ai(prompt: str, mode: str, model: Optional[str] = None) -> str:
    """Send a prompt to the AI model and return the response text.

    Args:
        prompt: User prompt.
        mode: Either ``"coding"`` or ``"qa"``.
        model: Optional OpenAI model name; defaults to the first available model.
    """
    api_key = load_api_key()
    router = get_router(api_key)
    model_name = model or list_openai_models(api_key)[0]
    messages = _build_messages(prompt, mode, model_name)
    route = router.check_for_matching_routes(model_name)
    llm = route.llm if route and route.llm else router.llm
    if llm is None:
        raise RuntimeError("No LLM configured for Semantic Router.")
    return llm(messages).strip()


def edit_file(path: str, instructions: str, model: Optional[str] = None) -> None:
    """Use the AI agent to edit a local file in place.

    Args:
        path: File to modify.
        instructions: Natural-language edit instructions.
        model: Optional OpenAI model name.
    """
    api_key = load_api_key()
    router = get_router(api_key)
    model_name = model or list_openai_models(api_key)[0]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            original = fh.read()
    except OSError as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}")

    messages = _build_edit_messages(original, instructions, model_name)
    route = router.check_for_matching_routes(model_name)
    llm = route.llm if route and route.llm else router.llm
    if llm is None:
        raise RuntimeError("No LLM configured for Semantic Router.")
    new_content = llm(messages)
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
    parser.add_argument(
        "--model",
        help="Specify which OpenAI model to use (defaults to the first available).",
    )
    ns = parser.parse_args(argv)

    prompt = " ".join(ns.prompt)
    try:
        if ns.edit:
            edit_file(ns.edit, prompt, ns.model)
            print(f"{AGENT_NAME}: Updated {ns.edit}")
        else:
            answer = query_ai(prompt, ns.mode, ns.model)
            print(f"{AGENT_NAME}: {answer}")
    except RuntimeError as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main(sys.argv[1:]))
