from __future__ import annotations

import json

from codebase_agent.memory import MemoryStore
from codebase_agent.tools import ToolRegistry


def test_read_file_rejects_path_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    memory = MemoryStore(tmp_path / "memory.sqlite3")
    tools = ToolRegistry(workspace, memory)

    result = json.loads(tools.run("read_file", {"path": "../secret.txt"}))

    assert "error" in result
    assert "escapes workspace" in result["error"]


def test_search_and_memory_round_trip(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "app.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    memory = MemoryStore(tmp_path / "memory.sqlite3")
    tools = ToolRegistry(workspace, memory)

    search_result = json.loads(tools.run("search_text", {"query": "hello"}))
    remember_result = json.loads(
        tools.run("remember", {"kind": "architecture", "content": "app.py exposes hello"})
    )
    recall_result = json.loads(tools.run("recall", {"query": "hello"}))

    assert search_result["matches"]
    assert remember_result["stored"] is True
    assert recall_result["items"][0]["content"] == "app.py exposes hello"
