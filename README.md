# Anthropic Codebase Agent

A small, inspectable AI agent built from scratch with the Anthropic Messages API.

The agent is designed for one strong portfolio use case: point it at a local
repo, ask a question, and let it use tools to list files, read files, search
text, and store durable project memory.

## Why This Project Exists

This is intentionally smaller than a full agent framework. The goal is to show
clear ownership of the core pieces:

- Anthropic tool-calling loop
- Local tool registry
- Workspace-safe file access
- SQLite memory
- CLI interface
- Offline tests for the risky parts

## Features

- One-shot and interactive CLI
- Direct Anthropic REST API integration, no SDK required
- Tools:
  - `list_files`
  - `read_file`
  - `search_text`
  - `remember`
  - `recall`
- Workspace sandboxing so tools cannot read outside the selected folder
- Local SQLite memory for facts learned during investigations

## Quick Start

Requires Python 3.11+.

```powershell
git clone https://github.com/HuyBruce/anthropic-codebase-agent.git
cd anthropic-codebase-agent
copy .env.example .env
```

Edit `.env`:

```text
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-20250514
AGENT_WORKSPACE=.
```

Run a one-shot investigation:

```powershell
python run_agent.py --doctor
python run_agent.py "Find where Hermes documents custom skill creation and summarize the extension path."
```

Run interactive mode:

```powershell
python run_agent.py --workspace ..\hermes-agent
```

Example prompts:

```text
What are the main entry points of this repo?
Find the docs for adding tools and explain the minimum files I need to touch.
Search for Anthropic provider code and summarize how API keys are loaded.
Remember the repo's extension path after you inspect it.
Recall what you know about extension path.
```

## Running Tests

The core safety and memory behavior can be tested without an API key.

```powershell
python -m py_compile src\codebase_agent\*.py
python scripts\smoke_test.py
```

Optional pytest run:

```powershell
python -m pip install -r requirements.txt
python -m pytest
```

## Architecture

```text
src/codebase_agent/
  anthropic_client.py  # Minimal Anthropic Messages API client
  agent.py             # Tool-calling loop
  cli.py               # One-shot and interactive CLI
  config.py            # Env loading and config
  memory.py            # SQLite memory store
  tools.py             # Workspace-safe tool registry
run_agent.py           # Convenience launcher for local use
```

Flow:

```text
User prompt
  -> CodebaseAgent
  -> Anthropic Messages API
  -> tool_use blocks
  -> local ToolRegistry
  -> tool_result blocks
  -> final answer
```

## Portfolio Description

Short CV bullet:

```text
Built a local codebase investigation agent from scratch using Anthropic Messages API tool calling, workspace-safe file tools, SQLite memory, and an interactive Python CLI.
```

Longer project description:

```text
Designed and implemented a small autonomous codebase agent with a custom tool registry, Anthropic tool-use loop, local memory, and path-sandboxed file inspection. Added offline tests for path safety, search, and memory behavior, plus documentation and reproducible demo commands.
```

## Next Improvements

- Add streaming output
- Add semantic search with embeddings
- Add a web UI
- Add evaluation logs for repeated benchmark questions
- Add a Hermes Agent skill that calls this CLI as an external tool

## Publication snapshot

Prepared by Pham Gia Huy on 2026-10-12. The offline smoke test passed; a live paid API call was not rerun for publication. Local credentials and memory databases are excluded.
