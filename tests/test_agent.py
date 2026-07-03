import json
import tempfile
import unittest
from pathlib import Path

from bare_agent.agent import AgentLoop
from bare_agent.memory import MemoryStore
from bare_agent.models import ScriptedModel
from bare_agent.tools import make_tools


class AgentLoopTests(unittest.TestCase):
    def test_invalid_json_is_retried(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(Path(directory) / ".memory.json")
            model = ScriptedModel(
                [
                    "not json",
                    json.dumps(
                        {
                            "type": "final",
                            "summary": "Recovered after a JSON repair request.",
                            "next_steps": [],
                        }
                    ),
                ]
            )
            agent = AgentLoop(model=model, tools={}, memory=memory, max_steps=3)

            run = agent.run("return a final answer")

            self.assertTrue(run.completed)
            self.assertEqual(run.events[0].kind, "invalid_json")
            self.assertEqual(len(model.requests), 2)
            self.assertIn("not valid JSON", model.requests[1][-1]["content"])

    def test_remembered_facts_reach_the_next_step_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = MemoryStore(root / ".memory.json")
            tools = make_tools(root, memory=memory, allow_write=False)
            model = ScriptedModel(
                [
                    json.dumps(
                        {
                            "type": "tool",
                            "tool": "remember",
                            "args": {"key": "root_cause", "value": "off-by-one in average()"},
                            "reason": "Store the diagnosis for later steps.",
                        }
                    ),
                    json.dumps(
                        {
                            "type": "final",
                            "summary": "Diagnosis stored.",
                            "next_steps": [],
                        }
                    ),
                ]
            )
            agent = AgentLoop(model=model, tools=tools, memory=memory, max_steps=3)

            run = agent.run("diagnose and remember")

            self.assertTrue(run.completed)
            # The system prompt of the SECOND request must already contain the
            # fact stored during the first step — memory is live within a run.
            second_system_prompt = model.requests[1][0]["content"]
            self.assertIn("off-by-one in average()", second_system_prompt)

    def test_tool_errors_are_sent_back_to_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = MemoryStore(root / ".memory.json")
            tools = make_tools(root, memory=memory, allow_write=False)
            model = ScriptedModel(
                [
                    json.dumps(
                        {
                            "type": "tool",
                            "tool": "write_file",
                            "args": {"path": "note.txt", "content": "hello"},
                            "reason": "Try to write a file.",
                        }
                    ),
                    json.dumps(
                        {
                            "type": "final",
                            "summary": "Write was correctly blocked until --allow-write is used.",
                            "next_steps": ["Rerun with --allow-write if the edit is desired."],
                        }
                    ),
                ]
            )
            agent = AgentLoop(model=model, tools=tools, memory=memory, max_steps=3)

            run = agent.run("write a note")

            self.assertTrue(run.completed)
            self.assertEqual(run.events[0].kind, "tool_error")
            self.assertIn("write_file is disabled", model.requests[1][-1]["content"])


if __name__ == "__main__":
    unittest.main()

