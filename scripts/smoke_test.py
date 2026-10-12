from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codebase_agent.memory import MemoryStore  # noqa: E402
from codebase_agent.tools import ToolRegistry  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        workspace = base / "workspace"
        workspace.mkdir()
        (workspace / "app.py").write_text(
            "def hello():\n    return 'world'\n",
            encoding="utf-8",
        )

        tools = ToolRegistry(workspace, MemoryStore(base / "memory.sqlite3"))

        escaped = json.loads(tools.run("read_file", {"path": "../secret.txt"}))
        assert "error" in escaped

        search = json.loads(tools.run("search_text", {"query": "hello"}))
        assert search["matches"], search

        stored = json.loads(
            tools.run("remember", {"kind": "architecture", "content": "app.py exposes hello"})
        )
        assert stored["stored"] is True

        recalled = json.loads(tools.run("recall", {"query": "hello"}))
        assert recalled["items"][0]["content"] == "app.py exposes hello"

    print("smoke test passed")


if __name__ == "__main__":
    main()
