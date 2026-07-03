import sys
import tempfile
import unittest
from pathlib import Path

from bare_agent.memory import MemoryStore
from bare_agent.tools import ToolError, Workspace, make_tools


class ToolTests(unittest.TestCase):
    def test_workspace_blocks_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))

            with self.assertRaises(ToolError) as raised:
                workspace.resolve("../outside.txt")

            self.assertIn("escapes the workspace", str(raised.exception))

    def test_run_command_returns_nonzero_exit_as_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = MemoryStore(root / ".memory.json")
            tools = make_tools(root, memory=memory)

            result = tools["run_command"].call(
                {
                    "argv": [
                        sys.executable,
                        "-c",
                        "import sys; print('failing on purpose'); sys.exit(7)",
                    ],
                    "timeout_seconds": 5,
                }
            )

            self.assertEqual(result["exit_code"], 7)
            self.assertIn("failing on purpose", result["stdout"])

    def test_write_file_requires_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = MemoryStore(root / ".memory.json")
            tools = make_tools(root, memory=memory, allow_write=False)

            with self.assertRaises(ToolError) as raised:
                tools["write_file"].call({"path": "note.txt", "content": "hello"})

            self.assertIn("--allow-write", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

