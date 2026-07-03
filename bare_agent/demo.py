from __future__ import annotations

import json
import sys

from bare_agent.models import ScriptedModel


def build_demo_model() -> ScriptedModel:
    return ScriptedModel(
        responses=[
            json.dumps(
                {
                    "type": "tool",
                    "tool": "run_command",
                    "args": {
                        "argv": [
                            sys.executable,
                            "-m",
                            "unittest",
                            "discover",
                            "-s",
                            "examples/buggy_math",
                            "-p",
                            "test_*.py",
                        ],
                        "timeout_seconds": 10,
                    },
                    "reason": "Run the smallest relevant test suite before reading code.",
                }
            ),
            json.dumps(
                {
                    "type": "tool",
                    "tool": "read_file",
                    "args": {"path": "examples/buggy_math/calculator.py", "start": 1, "lines": 80},
                    "reason": "Inspect the implementation mentioned by the failing test.",
                }
            ),
            json.dumps(
                {
                    "type": "tool",
                    "tool": "read_file",
                    "args": {
                        "path": "examples/buggy_math/test_calculator.py",
                        "start": 1,
                        "lines": 80,
                    },
                    "reason": "Confirm the intended behavior from the test.",
                }
            ),
            json.dumps(
                {
                    "type": "final",
                    "summary": (
                        "The failing test is caused by average() dividing by len(values) - 1. "
                        "For [2, 4, 6], that returns 6.0 instead of the expected 4.0. "
                        "The fix is to divide by len(values) while keeping the empty-list guard."
                    ),
                    "next_steps": [
                        "Change examples/buggy_math/calculator.py to divide by len(values).",
                        "Rerun python -m unittest discover -s examples/buggy_math -p 'test_*.py'.",
                    ],
                }
            ),
        ]
    )

