from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODEL = "claude-sonnet-4-20250514"
PLACEHOLDER_API_KEYS = {
    "",
    "your_anthropic_api_key_here",
    "your_key_here",
    "sk-ant-api03-your-key-here",
}


def load_dotenv(path: Path) -> None:
    """Small .env loader to keep the project dependency-free."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class AgentConfig:
    api_key: str
    model: str
    workspace: Path
    memory_db: Path
    max_tokens: int = 1600
    max_turns: int = 8

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> "AgentConfig":
        root = project_root or Path.cwd()
        load_dotenv(root / ".env")

        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        workspace = Path(os.getenv("AGENT_WORKSPACE", ".")).expanduser()
        memory_db = Path(os.getenv("AGENT_MEMORY_DB", ".agent_memory.sqlite3")).expanduser()

        if not workspace.is_absolute():
            workspace = (root / workspace).resolve()
        if not memory_db.is_absolute():
            memory_db = (root / memory_db).resolve()

        return cls(
            api_key=api_key,
            model=model,
            workspace=workspace,
            memory_db=memory_db,
            max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "1600")),
            max_turns=int(os.getenv("AGENT_MAX_TURNS", "8")),
        )

    def validate_for_api_call(self) -> None:
        normalized_key = self.api_key.strip()
        if normalized_key in PLACEHOLDER_API_KEYS:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is missing or still set to the example placeholder. "
                "Open .env and replace it with your real Anthropic API key."
            )
        if not normalized_key.startswith("sk-ant-"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY does not look like a direct Anthropic API key. "
                "Expected it to start with 'sk-ant-'."
            )
