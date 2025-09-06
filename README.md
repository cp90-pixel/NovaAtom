# NovaAtom

This repository contains a basic code editor built with Tkinter.

## Usage

```
python code_editor.py
```

This will launch the editor where you can open, edit, and save files.

## Features

- Open, edit, and save plain text files.
- Find text within the document (`Ctrl+F`).
- Replace text throughout the document (`Ctrl+H`).
- Run shell commands in an integrated terminal (`Ctrl+T`).
- Jump to function or class definitions (`F12`).
- CodeSmith-powered code autocomplete (`Ctrl+Space`). The editor prompts for your OpenAI API key if it isn't set.
- Ask questions or apply edits with CodeSmith directly from the editor via the **CodeSmith** menu, which also lets you update your API key.
- Load custom extensions from the `extensions/` directory to add new commands.

## Extensions

Place Python files in an `extensions/` directory alongside `code_editor.py`. Each
file should define a `register(editor)` function that receives the
`CodeEditor` instance. Use this hook to add menu items or otherwise customize
the editor. See `extensions/word_count.py` for an example that adds a simple
word count command.

## AI CLI Coding Agent

A small helper script `ai_cli.py` lets you send prompts to the CodeSmith agent from the command line.
Set your OpenAI API key in the `OPENAI_API_KEY` environment variable and run:

```
python ai_cli.py "Explain recursion"
```

By default the CLI runs in **coding** mode for general programming help. Use the
`--mode qa` option to ask questions specifically about this repository:

```
python ai_cli.py --mode qa "What does ai_cli.py do?"
```

The response from CodeSmith will be printed to the terminal. The script uses the
`requests` library and the OpenAI Chat Completions API. For both modes the CLI
asks the model to craft a focused search query, runs it against a local YaCy
search engine, and feeds the top results — including a short snippet for context
— to the model so that answers can include up-to-date information from the internet.

To have CodeSmith modify a file directly, supply the path via `--edit`:

```
python ai_cli.py --edit README.md "replace Hello with Hi"
```

The agent receives the current file contents and your instructions, then writes
the updated contents back to disk.

### Running YaCy locally

By default `ai_cli.py` queries `http://localhost:8090`. Start your own YaCy
instance via Docker:

```
docker run -d --name yacy -p 8090:8090 -p 8443:8443 yacy/yacy_search_server
```

If your instance runs elsewhere, set the `YACY_SEARCH_URL` environment variable
to the full search endpoint, e.g. `http://myhost:8090/yacysearch.json`.

## Commitment to Open Source

**This pledge is permanent and irrevocable.** I guarantee that every past,
present, and future version of NovaAtom will remain entirely open source and
licensed under the MIT License. There will never be a closed-source edition or
license change that restricts your freedom to use, modify, and share this
project.
