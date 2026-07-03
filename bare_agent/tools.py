from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class ToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict[str, Any]
    call: Callable[[dict[str, Any]], dict[str, Any]]


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        if not self.root.exists():
            raise ToolError(f"Workspace root does not exist: {self.root}")

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ToolError(
                f"Path '{relative_path}' escapes the workspace. Use a path under {self.root}."
            ) from exc
        return candidate


def make_tools(root: Path, memory, allow_write: bool = False) -> dict[str, Tool]:
    workspace = Workspace(root)

    def list_files(args: dict[str, Any]) -> dict[str, Any]:
        start = workspace.resolve(str(args.get("path", ".")))
        max_entries = int(args.get("max_entries", 80))
        if not start.exists():
            raise ToolError(f"Cannot list '{start}': path does not exist.")
        if start.is_file():
            return {"root": str(workspace.root), "files": [str(start.relative_to(workspace.root))]}

        ignored = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
        entries: list[str] = []
        for current_root, dirs, files in os.walk(start):
            dirs[:] = sorted(directory for directory in dirs if directory not in ignored)
            for filename in sorted(files):
                path = Path(current_root) / filename
                entries.append(str(path.relative_to(workspace.root)))
                if len(entries) >= max_entries:
                    return {"root": str(workspace.root), "files": entries, "truncated": True}
        return {"root": str(workspace.root), "files": entries, "truncated": False}

    def read_file(args: dict[str, Any]) -> dict[str, Any]:
        path = workspace.resolve(str(args["path"]))
        start = max(1, int(args.get("start", 1)))
        line_count = min(240, max(1, int(args.get("lines", 120))))
        if not path.exists():
            raise ToolError(f"Cannot read '{path}': file does not exist.")
        if not path.is_file():
            raise ToolError(f"Cannot read '{path}': it is not a file.")
        text = path.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = text[start - 1 : start - 1 + line_count]
        return {
            "path": str(path.relative_to(workspace.root)),
            "start": start,
            "end": start + len(selected) - 1,
            "total_lines": len(text),
            "content": "\n".join(selected),
        }

    def write_file(args: dict[str, Any]) -> dict[str, Any]:
        if not allow_write:
            raise ToolError(
                "write_file is disabled. Rerun with --allow-write after reviewing the plan."
            )
        path = workspace.resolve(str(args["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(args.get("content", ""))
        path.write_text(content, encoding="utf-8")
        return {
            "path": str(path.relative_to(workspace.root)),
            "bytes_written": len(content.encode("utf-8")),
        }

    def run_command(args: dict[str, Any]) -> dict[str, Any]:
        argv = args.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            raise ToolError("run_command expects args.argv as a non-empty list of strings.")
        allowed = {
            "git",
            "ls",
            "node",
            "npm",
            "pnpm",
            "pytest",
            "python",
            "python3",
            "rg",
        }
        executable = Path(argv[0]).name
        if executable not in allowed and Path(argv[0]).resolve() != Path(os.sys.executable).resolve():
            raise ToolError(
                f"Command '{argv[0]}' is not allowed. Allowed executables: {sorted(allowed)}."
            )
        timeout = min(60, max(1, int(args.get("timeout_seconds", 20))))
        try:
            result = subprocess.run(
                argv,
                cwd=workspace.root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ToolError(f"Command executable not found: {argv[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"Command timed out after {timeout}s: {argv}") from exc
        return {
            "argv": argv,
            "exit_code": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        }

    def remember(args: dict[str, Any]) -> dict[str, Any]:
        key = str(args["key"]).strip()
        value = str(args["value"]).strip()
        if not key:
            raise ToolError("remember requires a non-empty key.")
        return {"memory": memory.remember(key, value)}

    return {
        "list_files": Tool(
            name="list_files",
            description="List files under a workspace path, ignoring common cache directories",
            schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."},
                    "max_entries": {"type": "integer", "default": 80},
                },
            },
            call=list_files,
        ),
        "read_file": Tool(
            name="read_file",
            description="Read a bounded slice of a UTF-8 text file inside the workspace",
            schema={
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer", "default": 1},
                    "lines": {"type": "integer", "default": 120},
                },
            },
            call=read_file,
        ),
        "write_file": Tool(
            name="write_file",
            description="Write a UTF-8 file inside the workspace; disabled unless --allow-write is set",
            schema={
                "type": "object",
                "required": ["path", "content"],
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
            call=write_file,
        ),
        "run_command": Tool(
            name="run_command",
            description="Run an allowlisted local command as argv without a shell; non-zero exits are observations",
            schema={
                "type": "object",
                "required": ["argv"],
                "properties": {
                    "argv": {"type": "array", "items": {"type": "string"}},
                    "timeout_seconds": {"type": "integer", "default": 20},
                },
            },
            call=run_command,
        ),
        "remember": Tool(
            name="remember",
            description="Persist a short observation into working memory",
            schema={
                "type": "object",
                "required": ["key", "value"],
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
            },
            call=remember,
        ),
    }

