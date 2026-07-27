"""Assert every place that carries a version agrees, and that the skills' floor matches.

nabokov ships through two channels that nothing ties together: the linter goes to
PyPI, the skills go through git (``npx skills add``, and the Claude plugin
marketplace). A user can therefore hold skill instructions that describe rules
their installed linter has never heard of, and the failure is silent — the agent
asks for a rule that does not exist, gets nothing back, and reports a clean file.

The skills defend against that by invoking ``uvx 'nabokov>=X'`` once per session,
which fails loudly when the tool is too old. That only works if X tracks the real
version, so this checks it. Wired into ``make release``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (path, regex with one capture group, human name)
SOURCES = [
    ("pyproject.toml", r'^version = "([^"]+)"', "package version"),
    (".claude-plugin/plugin.json", r'"version": "([^"]+)"', "plugin manifest"),
    (".claude-plugin/marketplace.json", r'"version": "([^"]+)"', "marketplace entry"),
]

# The floor each skill pins in its first uvx invocation.
SKILL_FLOOR = r"uvx 'nabokov>=([0-9][^']*)'"
SKILLS = [
    "skills/nabokov-editor/SKILL.md",
    "skills/nabokov-copywriter/SKILL.md",
]


def _find(path: str, pattern: str) -> str | None:
    text = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(pattern, text, re.M)
    return match.group(1) if match else None


def main() -> int:
    found: dict[str, str] = {}
    errors: list[str] = []

    for path, pattern, label in SOURCES:
        version = _find(path, pattern)
        if version is None:
            errors.append(f"{path}: no version found ({label})")
        else:
            found[path] = version

    for path in SKILLS:
        floor = _find(path, SKILL_FLOOR)
        if floor is None:
            errors.append(
                f"{path}: no version floor. Its first uvx call must read "
                f"uvx 'nabokov>=X' so a stale install fails loudly."
            )
        else:
            found[path] = floor

    if len(set(found.values())) > 1:
        errors.append("versions disagree:")
        errors += [f"    {v:<12} {p}" for p, v in sorted(found.items())]

    if errors:
        print("version check FAILED", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)
        print(
            "\nThe skills ship from git and the linter from PyPI. If they disagree, a\n"
            "user gets instructions for rules their linter does not have, and the\n"
            "failure is silent. Bump all of them together.",
            file=sys.stderr,
        )
        return 1

    print(f"version check OK — everything at {next(iter(found.values()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
