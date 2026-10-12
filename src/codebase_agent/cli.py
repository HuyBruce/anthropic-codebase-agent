from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .agent import CodebaseAgent
from .config import AgentConfig, PLACEHOLDER_API_KEYS


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codebase-agent",
        description="Ask an Anthropic-powered agent to inspect a local codebase.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="One-shot question. Omit it to start interactive mode.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Workspace the agent is allowed to inspect.",
    )
    parser.add_argument(
        "--model",
        help="Anthropic model name. Defaults to ANTHROPIC_MODEL or claude-sonnet-4-20250514.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check local configuration without calling the Anthropic API.",
    )
    return parser


def run_doctor(config: AgentConfig) -> int:
    failed = False

    print("Codebase Agent doctor")
    print(f"- workspace: {config.workspace}")
    if config.workspace.exists() and config.workspace.is_dir():
        print("  OK workspace exists")
    else:
        print("  ERROR workspace does not exist or is not a directory")
        failed = True

    print(f"- model: {config.model}")
    print(f"- memory db: {config.memory_db}")
    if config.memory_db.parent.exists():
        print("  OK memory parent directory exists")
    else:
        print("  ERROR memory parent directory does not exist")
        failed = True

    if config.api_key.strip() in PLACEHOLDER_API_KEYS:
        print("- api key: ERROR missing or still set to example placeholder")
        failed = True
    elif not config.api_key.startswith("sk-ant-"):
        print("- api key: ERROR does not look like a direct Anthropic API key")
        failed = True
    else:
        print("- api key: OK present")

    if shutil.which("rg"):
        print("- ripgrep: OK installed")
    else:
        print("- ripgrep: WARN not installed, Python fallback search will be used")

    return 1 if failed else 0


def main() -> None:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args()
    config = AgentConfig.from_env(project_root=Path.cwd())

    if args.workspace:
        config = AgentConfig(
            api_key=config.api_key,
            model=args.model or config.model,
            workspace=args.workspace.resolve(),
            memory_db=config.memory_db,
            max_tokens=config.max_tokens,
            max_turns=config.max_turns,
        )
    elif args.model:
        config = AgentConfig(
            api_key=config.api_key,
            model=args.model,
            workspace=config.workspace,
            memory_db=config.memory_db,
            max_tokens=config.max_tokens,
            max_turns=config.max_turns,
        )

    if args.doctor:
        parser.exit(run_doctor(config))

    agent = CodebaseAgent(config)
    if args.prompt:
        try:
            print(agent.ask(" ".join(args.prompt)))
        except RuntimeError as exc:
            parser.exit(1, f"Error: {exc}\n")
        return

    print(f"Codebase Agent | workspace={config.workspace}")
    print("Type /exit to quit.")
    while True:
        try:
            user_text = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if user_text in {"/exit", "/quit"}:
            return
        if not user_text:
            continue
        try:
            print(agent.ask(user_text))
        except RuntimeError as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
