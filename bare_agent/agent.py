from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from bare_agent.models import ModelClient
from bare_agent.prompts import build_system_prompt
from bare_agent.tools import Tool, ToolError


@dataclass
class AgentEvent:
    kind: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRun:
    completed: bool
    events: list[AgentEvent]
    final: dict[str, Any] | None = None


class AgentLoop:
    def __init__(
        self,
        model: ModelClient,
        tools: dict[str, Tool],
        memory,
        max_steps: int = 8,
    ):
        self.model = model
        self.tools = tools
        self.memory = memory
        self.max_steps = max_steps

    def run(self, goal: str) -> AgentRun:
        events: list[AgentEvent] = []
        messages = [
            {"role": "system", "content": build_system_prompt(self.tools, self.memory.load())},
            {"role": "user", "content": goal},
        ]

        for step in range(1, self.max_steps + 1):
            # Rebuild the system prompt each step so facts stored via the
            # `remember` tool are visible to the model on the NEXT step,
            # not just the next run.
            messages[0] = {
                "role": "system",
                "content": build_system_prompt(self.tools, self.memory.load()),
            }
            raw = self.model.complete(messages)
            try:
                action = json.loads(raw)
            except json.JSONDecodeError:
                events.append(
                    AgentEvent(
                        kind="invalid_json",
                        message="Model returned invalid JSON; asked it to repair the response.",
                        payload={"raw": raw},
                    )
                )
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. Return exactly one JSON "
                            "object matching the allowed response shapes."
                        ),
                    }
                )
                continue

            action_type = action.get("type")
            if action_type == "final":
                events.append(
                    AgentEvent(kind="final", message=str(action.get("summary", "")), payload=action)
                )
                return AgentRun(completed=True, events=events, final=action)

            if action_type != "tool":
                observation = {
                    "error": f"Unknown action type '{action_type}'. Use 'tool' or 'final'."
                }
                events.append(AgentEvent(kind="action_error", message=observation["error"]))
                messages = _append_observation(messages, raw, "action", observation)
                continue

            tool_name = str(action.get("tool", ""))
            tool = self.tools.get(tool_name)
            if tool is None:
                observation = {
                    "error": f"Unknown tool '{tool_name}'. Available tools: {sorted(self.tools)}."
                }
                events.append(AgentEvent(kind="tool_error", message=observation["error"]))
                messages = _append_observation(messages, raw, tool_name, observation)
                continue

            args = action.get("args", {})
            if not isinstance(args, dict):
                observation = {"error": "Tool args must be a JSON object."}
                events.append(AgentEvent(kind="tool_error", message=observation["error"]))
                messages = _append_observation(messages, raw, tool_name, observation)
                continue

            try:
                observation = tool.call(args)
                events.append(
                    AgentEvent(
                        kind="tool",
                        message=f"{tool_name} completed.",
                        payload={"tool": tool_name, "observation": observation, "step": step},
                    )
                )
            except ToolError as exc:
                observation = {"error": str(exc)}
                events.append(
                    AgentEvent(
                        kind="tool_error",
                        message=f"{tool_name} failed: {exc}",
                        payload={"tool": tool_name, "step": step},
                    )
                )
            messages = _append_observation(messages, raw, tool_name, observation)

        final = {
            "type": "final",
            "summary": f"Stopped after {self.max_steps} steps without a final answer.",
            "next_steps": ["Increase --max-steps or narrow the goal."],
        }
        events.append(AgentEvent(kind="limit", message=final["summary"], payload=final))
        return AgentRun(completed=False, events=events, final=final)


def _append_observation(
    messages: list[dict[str, str]], raw: str, tool_name: str, observation: dict[str, Any]
) -> list[dict[str, str]]:
    next_messages = list(messages)
    next_messages.append({"role": "assistant", "content": raw})
    next_messages.append(
        {
            "role": "user",
            "content": (
                f"Tool observation for {tool_name}:\n"
                f"{json.dumps(observation, indent=2, sort_keys=True)}\n"
                "Choose the next action."
            ),
        }
    )
    return next_messages

