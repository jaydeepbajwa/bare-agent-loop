from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from bare_agent.agent import AgentEvent, AgentLoop
from bare_agent.demo import build_demo_model
from bare_agent.memory import MemoryStore
from bare_agent.models import ModelError, OpenAIChatClient
from bare_agent.tools import make_tools


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bare-agent",
        description="Run a framework-free terminal agent loop over a local repo.",
    )
    parser.add_argument("goal", nargs="*", help="The agent goal, for example: triage failing tests.")
    parser.add_argument("--repo", default=".", help="Workspace root the tools may access.")
    parser.add_argument("--demo", action="store_true", help="Run a deterministic demo without an API key.")
    parser.add_argument("--allow-write", action="store_true", help="Enable the write_file tool.")
    parser.add_argument("--max-steps", type=int, default=8, help="Maximum model-tool loop iterations.")
    parser.add_argument("--env-file", default=".env", help="Optional dotenv-style file for API settings.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL for real LLM runs.")
    args = parser.parse_args(argv)

    load_dotenv(Path(args.env_file))

    if args.demo:
        repo_root = Path(__file__).resolve().parents[1]
        goal = "Triage the failing tests in examples/buggy_math and explain the likely fix."
        model = build_demo_model()
    else:
        repo_root = Path(args.repo).resolve()
        goal = " ".join(args.goal).strip()
        if not goal:
            parser.error("provide a goal or use --demo")
        api_key = os.getenv("OPENAI_API_KEY", "")
        model_name = args.model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not api_key:
            print(
                "OPENAI_API_KEY is missing. Copy .env.example to .env, set a key, "
                "or run python3 -m bare_agent --demo.",
                file=sys.stderr,
            )
            return 2
        model = OpenAIChatClient(api_key=api_key, model=model_name, base_url=base_url)

    memory = MemoryStore(repo_root / ".bare_agent_memory.json")
    tools = make_tools(repo_root, memory=memory, allow_write=args.allow_write)
    agent = AgentLoop(model=model, tools=tools, memory=memory, max_steps=args.max_steps)

    print(f"goal: {goal}")
    print(f"repo: {repo_root}")
    try:
        run = agent.run(goal)
    except ModelError as exc:
        print(f"model error: {exc}", file=sys.stderr)
        return 1

    for index, event in enumerate(run.events, start=1):
        print(format_event(index, event))
    return 0 if run.completed else 1


def load_dotenv(path: Path) -> None:
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


def format_event(index: int, event: AgentEvent) -> str:
    if event.kind == "tool":
        observation = event.payload.get("observation", {})
        tool_name = event.payload.get("tool", "tool")
        if tool_name == "run_command":
            return (
                f"[{index}] tool {tool_name}: exit={observation.get('exit_code')}\n"
                f"{_indent(_compact_command_output(observation))}"
            )
        if tool_name == "read_file":
            return (
                f"[{index}] tool {tool_name}: {observation.get('path')} "
                f"lines {observation.get('start')}-{observation.get('end')}"
            )
        return f"[{index}] tool {tool_name}: ok"
    if event.kind == "final":
        next_steps = event.payload.get("next_steps") or []
        rendered_steps = "\n".join(f"    - {step}" for step in next_steps)
        return f"[{index}] final: {event.message}\n{rendered_steps}"
    return f"[{index}] {event.kind}: {event.message}"


def _compact_command_output(observation: dict) -> str:
    stdout = str(observation.get("stdout", "")).strip()
    stderr = str(observation.get("stderr", "")).strip()
    chunks = []
    if stdout:
        chunks.append("stdout:\n" + stdout[-1200:])
    if stderr:
        chunks.append("stderr:\n" + stderr[-1200:])
    return "\n".join(chunks) if chunks else "no output"


def _indent(text: str) -> str:
    return "\n".join(f"    {line}" for line in text.splitlines())


if __name__ == "__main__":
    raise SystemExit(main())

