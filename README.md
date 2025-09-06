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
asks the model to craft a focused search query, runs it against the YaCy search
engine, and feeds the top results to the model so that answers can include
up-to-date information from the internet.
