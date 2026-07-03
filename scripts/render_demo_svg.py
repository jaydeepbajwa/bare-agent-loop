"""Render docs/demo.svg from a real `--demo` run.

The image in the README is generated from actual demo output, not drawn by
hand, so it cannot silently drift from what the code does. Regenerate with:

    python3 scripts/render_demo_svg.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "docs" / "demo.svg"

LINE_HEIGHT = 21
FONT_SIZE = 14
PADDING_X = 24
HEADER_HEIGHT = 42
WIDTH = 960

BODY_COLOR = "#d1d5db"
DIM_COLOR = "#9ca3af"
TOOL_COLOR = "#67e8f9"
FINAL_COLOR = "#fbbf24"
GOAL_COLOR = "#34d399"


def line_color(line: str) -> str:
    stripped = line.lstrip()
    if line.startswith(("goal:", "repo:")):
        return GOAL_COLOR
    if stripped.startswith("[") and " final:" in line:
        return FINAL_COLOR
    if stripped.startswith("[") and " tool " in line:
        return TOOL_COLOR
    if line.startswith("    "):
        return DIM_COLOR
    return BODY_COLOR


MAX_CHARS = 104


def run_demo() -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "bare_agent", "--demo"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stdout.rstrip().splitlines()
    # Absolute paths are machine-specific; keep the image stable across machines.
    sanitized = [line.rstrip().replace(str(REPO_ROOT), ".") for line in lines]
    return [wrapped for line in sanitized for wrapped in _wrap(line)]


def _wrap(line: str) -> list[str]:
    """Word-wrap a long line, indenting continuations under its content."""
    if len(line) <= MAX_CHARS:
        return [line]
    indent = " " * (len(line) - len(line.lstrip()) + 2)
    words = line.split(" ")
    rows, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if current and len(candidate) > MAX_CHARS:
            rows.append(current)
            current = indent + word
        else:
            current = candidate
    if current:
        rows.append(current)
    return rows


def render(lines: list[str]) -> str:
    height = HEADER_HEIGHT + PADDING_X + LINE_HEIGHT * len(lines) + PADDING_X
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="title desc">',
        '  <title id="title">bare-agent --demo output</title>',
        '  <desc id="desc">Terminal output of the deterministic demo: the agent '
        "runs the failing test suite, reads two files, and explains the bug.</desc>",
        f'  <rect width="{WIDTH}" height="{height}" rx="10" fill="#111827"/>',
        f'  <rect x="0" y="0" width="{WIDTH}" height="{HEADER_HEIGHT}" rx="10" fill="#1f2937"/>',
        '  <circle cx="24" cy="21" r="7" fill="#f87171"/>',
        '  <circle cx="48" cy="21" r="7" fill="#fbbf24"/>',
        '  <circle cx="72" cy="21" r="7" fill="#34d399"/>',
        f'  <text x="96" y="27" fill="{DIM_COLOR}" font-family="Menlo, Consolas, monospace" '
        f'font-size="13">python3 -m bare_agent --demo</text>',
    ]
    y = HEADER_HEIGHT + PADDING_X
    for line in lines:
        if line:
            parts.append(
                f'  <text x="{PADDING_X}" y="{y}" fill="{line_color(line)}" '
                f'font-family="Menlo, Consolas, monospace" font-size="{FONT_SIZE}" '
                f'xml:space="preserve">{escape(line)}</text>'
            )
        y += LINE_HEIGHT
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    lines = run_demo()
    OUTPUT.write_text(render(lines), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(lines)} lines of demo output)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
