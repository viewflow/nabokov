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
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BOT_LOCK = "bot/uv.lock"

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


def _check_no_hardcoded_dunder(errors: list[str]) -> None:
    """``__version__`` must come from package metadata, never a literal.

    26.7.7 shipped reporting itself as 26.7.6 because ``src/nabokov/__init__.py``
    held a literal that nothing checked — a sixth version location, one file
    deeper than this script was looking. Rather than add it to the list and keep
    remembering, the module now reads ``importlib.metadata``. This keeps it that
    way.
    """
    path = "src/nabokov/__init__.py"
    text = (ROOT / path).read_text(encoding="utf-8")
    if re.search(r'^__version__\s*=\s*["\']\d', text, re.M):
        errors.append(
            f"{path}: __version__ is a hardcoded literal. Derive it from "
            f"importlib.metadata so it cannot drift from pyproject.toml."
        )


def _bot_lock_version() -> str | None:
    """The nabokov version ``bot/uv.lock`` resolves to.

    Read as TOML, not by regex: the lock is a list of ``[[package]]`` tables in
    alphabetical order, so a bare ``version = "..."`` search returns whichever
    package sorts first, and the comparison would silently be against the wrong
    number.
    """
    data = tomllib.loads((ROOT / BOT_LOCK).read_text(encoding="utf-8"))
    for package in data.get("package", []):
        if package.get("name") == "nabokov":
            return package.get("version")
    return None


def check_bot_lock() -> int:
    """Refuse to deploy the bot against a stale pin.

    The bot depends on ``nabokov @ git+…`` with no pin, so its lock records a
    commit, and ``uv sync`` on the server installs whatever that commit says —
    deploying new bot code does not pull a new linter. 26.7.9 shipped to PyPI and
    to the website while the bot ran 26.7.8 for exactly this reason.

    This cannot join the checks in ``main()``. The lock resolves against the
    remote, so it can only be bumped after the release commit is pushed, which
    means it necessarily lags at ``make release`` time. The invariant that holds
    is the deploy-time one, so this hangs off ``update-bot`` and ``deploy-bot``.

    Version equality is the test. It catches a forgotten bump, which is the
    failure that happens; it cannot catch a lock pointing at a different commit
    carrying the same version, which would need an amended release.
    """
    package = _find("pyproject.toml", r'^version = "([^"]+)"')
    locked = _bot_lock_version()
    if package is None:
        print("pyproject.toml: no version found", file=sys.stderr)
        return 1
    if locked is None:
        print(f"{BOT_LOCK}: no nabokov entry", file=sys.stderr)
        return 1
    if locked != package:
        print("bot lock check FAILED", file=sys.stderr)
        print(f"  {BOT_LOCK} pins nabokov {locked}, this repo is at {package}", file=sys.stderr)
        print(
            "\nThe bot installs nabokov from the commit in its lock, so deploying now\n"
            "would ship new bot code against the old linter. Push the release commit\n"
            "first, then:\n"
            "    make bot-lock && git add bot/uv.lock && git commit -m 'bot: bump lock'",
            file=sys.stderr,
        )
        return 1
    print(f"bot lock check OK — nabokov {locked}")
    return 0


def main() -> int:
    found: dict[str, str] = {}
    errors: list[str] = []
    _check_no_hardcoded_dunder(errors)

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
    raise SystemExit(check_bot_lock() if "--bot-lock" in sys.argv else main())
