from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .memory import MemoryStore


MAX_FILE_BYTES = 512_000
IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
}


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]

    def anthropic_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    def __init__(self, workspace: Path, memory: MemoryStore) -> None:
        self.workspace = workspace.resolve()
        self.memory = memory
        self._tools = self._build_tools()

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.anthropic_schema() for tool in self._tools.values()]

    def run(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = tool.handler(arguments)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as exc:  # Tool errors should go back to the model.
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    def _build_tools(self) -> dict[str, Tool]:
        tools = [
            Tool(
                name="list_files",
                description="List files in the workspace, optionally filtered by glob.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "root": {"type": "string", "default": "."},
                        "glob": {"type": "string", "default": "*"},
                        "limit": {"type": "integer", "default": 80},
                    },
                },
                handler=self._list_files,
            ),
            Tool(
                name="read_file",
                description="Read a text file from the workspace.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "max_chars": {"type": "integer", "default": 12000},
                    },
                    "required": ["path"],
                },
                handler=self._read_file,
            ),
            Tool(
                name="search_text",
                description="Search for text in workspace files.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "root": {"type": "string", "default": "."},
                        "limit": {"type": "integer", "default": 30},
                    },
                    "required": ["query"],
                },
                handler=self._search_text,
            ),
            Tool(
                name="remember",
                description="Store a durable note about the project or investigation.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "default": "note"},
                        "content": {"type": "string"},
                    },
                    "required": ["content"],
                },
                handler=self._remember,
            ),
            Tool(
                name="recall",
                description="Search durable local memory.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
                handler=self._recall,
            ),
        ]
        return {tool.name: tool for tool in tools}

    def _resolve_workspace_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        resolved = candidate.resolve()
        if resolved != self.workspace and self.workspace not in resolved.parents:
            raise ValueError(f"Path escapes workspace: {raw_path}")
        return resolved

    def _iter_files(self, root: Path, glob: str) -> list[Path]:
        files: list[Path] = []
        for path in root.rglob(glob):
            if not path.is_file():
                continue
            if any(part in IGNORED_DIRS for part in path.relative_to(self.workspace).parts):
                continue
            files.append(path)
        return files

    def _list_files(self, arguments: dict[str, Any]) -> dict[str, Any]:
        root = self._resolve_workspace_path(str(arguments.get("root", ".")))
        glob = str(arguments.get("glob", "*"))
        limit = int(arguments.get("limit", 80))
        files = self._iter_files(root, glob)[:limit]
        return {
            "workspace": str(self.workspace),
            "files": [str(path.relative_to(self.workspace)) for path in files],
            "count": len(files),
        }

    def _read_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_workspace_path(str(arguments["path"]))
        max_chars = int(arguments.get("max_chars", 12000))
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"File is too large to read safely: {path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": str(path.relative_to(self.workspace)),
            "content": content[:max_chars],
            "truncated": len(content) > max_chars,
        }

    def _search_text(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments["query"])
        root = self._resolve_workspace_path(str(arguments.get("root", ".")))
        limit = int(arguments.get("limit", 30))

        rg_result = self._search_with_rg(query, root, limit)
        if rg_result is not None:
            return rg_result

        matches: list[dict[str, Any]] = []
        lowered = query.lower()
        for path in self._iter_files(root, "*"):
            if len(matches) >= limit:
                break
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            for line_no, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
            ):
                if lowered in line.lower():
                    matches.append(
                        {
                            "path": str(path.relative_to(self.workspace)),
                            "line": line_no,
                            "text": line.strip(),
                        }
                    )
                    break
        return {"query": query, "matches": matches, "engine": "python"}

    def _search_with_rg(self, query: str, root: Path, limit: int) -> dict[str, Any] | None:
        try:
            search_root = str(root.relative_to(self.workspace))
        except ValueError:
            search_root = str(root)
        if search_root == ".":
            search_root = "."

        try:
            completed = subprocess.run(
                ["rg", "--line-number", "--no-heading", "--fixed-strings", query, search_root],
                cwd=self.workspace,
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return None

        if completed.returncode not in (0, 1):
            return None

        matches: list[dict[str, Any]] = []
        for line in completed.stdout.splitlines()[:limit]:
            path_text, line_no_text, text = (line.split(":", 2) + ["", ""])[:3]
            matches.append(
                {
                    "path": path_text,
                    "line": int(line_no_text) if line_no_text.isdigit() else None,
                    "text": text.strip(),
                }
            )
        return {"query": query, "matches": matches, "engine": "ripgrep"}

    def _remember(self, arguments: dict[str, Any]) -> dict[str, Any]:
        kind = str(arguments.get("kind", "note"))
        content = str(arguments["content"])
        self.memory.add(kind=kind, content=content)
        return {"stored": True, "kind": kind}

    def _recall(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments["query"])
        limit = int(arguments.get("limit", 5))
        items = self.memory.search(query=query, limit=limit)
        return {
            "query": query,
            "items": [
                {
                    "kind": item.kind,
                    "content": item.content,
                    "created_at": item.created_at,
                }
                for item in items
            ],
        }
