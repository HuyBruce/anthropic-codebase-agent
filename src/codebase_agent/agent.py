from __future__ import annotations

from typing import Any

from .anthropic_client import AnthropicClient
from .config import AgentConfig
from .memory import MemoryStore
from .tools import ToolRegistry


SYSTEM_PROMPT = """You are Codebase Agent, a pragmatic software investigation assistant.

Rules:
- Use tools before making claims about files.
- Cite file paths and line numbers when available.
- Keep answers concise and actionable.
- Store durable project facts with remember when they will help future work.
- Never read outside the configured workspace.
"""


class CodebaseAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.memory = MemoryStore(config.memory_db)
        self.tools = ToolRegistry(config.workspace, self.memory)
        self.client = AnthropicClient(
            api_key=config.api_key,
            model=config.model,
            max_tokens=config.max_tokens,
        )
        self.messages: list[dict[str, Any]] = []

    def ask(self, user_text: str) -> str:
        self.config.validate_for_api_call()
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(self.config.max_turns):
            response = self.client.create_message(
                system=SYSTEM_PROMPT,
                messages=self.messages,
                tools=self.tools.schemas(),
            )
            content = response.get("content", [])
            self.messages.append({"role": "assistant", "content": content})

            tool_uses = [block for block in content if block.get("type") == "tool_use"]
            if not tool_uses:
                return self._collect_text(content)

            tool_results = []
            for block in tool_uses:
                tool_output = self.tools.run(
                    name=block["name"],
                    arguments=block.get("input", {}),
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": tool_output,
                    }
                )

            self.messages.append({"role": "user", "content": tool_results})

        return "Stopped after reaching AGENT_MAX_TURNS. Try narrowing the task."

    @staticmethod
    def _collect_text(content: list[dict[str, Any]]) -> str:
        text_parts = [
            block.get("text", "")
            for block in content
            if block.get("type") == "text" and block.get("text")
        ]
        return "\n".join(text_parts).strip()
