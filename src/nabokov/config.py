"""Configuration: rule selection and file discovery.

Precedence (highest first): CLI flags > ``.nabokov.toml`` > ``[tool.nabokov]`` in
``pyproject.toml`` > built-in defaults. Config is discovered by walking up from the
current directory. ``extend_select`` / ``extend_ignore`` accumulate across layers
(file + CLI); every other key is overridden by the higher layer.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .checks import ALL_CODES, DEFAULT_CODES

VALID_TARGETS = {"ACCESSIBLE", "NORMAL", "TECHNICAL", "ESSAY"}
BUDGET_CODES = {"NB301", "NB302", "NB303", "NB401"}
VALID_FORMATS = {"auto", "color", "flake8", "json", "github"}
VALID_COLORS = {"auto", "always", "never"}


class ConfigError(ValueError):
    """A bad value in a config file."""


def _match(code: str, tokens: tuple[str, ...]) -> bool:
    return any(code == t or code.startswith(t) for t in tokens)


@dataclass
class Config:
    select: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    extend_select: tuple[str, ...] = ()
    extend_ignore: tuple[str, ...] = ()
    target: str = "NORMAL"
    max_grade: int | None = None
    exit_zero: bool = False
    fmt: str = "auto"  # auto | color | flake8 | json | github
    color: str = "auto"  # auto | always | never
    statistics: bool = False
    adverbs_all_pos: bool = False
    stdin_display_name: str = "-"
    # Per-1000-word style budgets (code -> rate), overriding the target's defaults.
    budgets: dict[str, float] = field(default_factory=dict)

    def enabled_codes(self) -> set[str]:
        """Resolve the active rule codes from select/ignore, flake8-style."""
        if self.select:
            base = {c for c in ALL_CODES if _match(c, self.select)}
        else:
            base = set(DEFAULT_CODES)
        base |= {c for c in ALL_CODES if _match(c, self.extend_select)}
        base -= {c for c in ALL_CODES if self.is_ignored(c)}
        return base

    def is_ignored(self, code: str) -> bool:
        return _match(code, self.ignore) or _match(code, self.extend_ignore)


_LIST_KEYS = {"select", "ignore", "extend_select", "extend_ignore"}
_SCALAR_KEYS = {
    "target",
    "max_grade",
    "exit_zero",
    "fmt",
    "color",
    "statistics",
    "adverbs_all_pos",
}


def _coerce(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        norm = key.replace("-", "_")
        if norm in _LIST_KEYS:
            out[norm] = tuple(value) if isinstance(value, (list, tuple)) else (value,)
        elif norm in _SCALAR_KEYS or norm == "budgets":
            out[norm] = value
    if "target" in out:
        target = str(out["target"]).upper()
        if target not in VALID_TARGETS:
            raise ConfigError(
                f"invalid target {out['target']!r} (choose from {', '.join(sorted(VALID_TARGETS))})"
            )
        out["target"] = target
    if "fmt" in out and out["fmt"] not in VALID_FORMATS:
        raise ConfigError(
            f"invalid format {out['fmt']!r} (choose from {', '.join(sorted(VALID_FORMATS))})"
        )
    if "color" in out and out["color"] not in VALID_COLORS:
        raise ConfigError(
            f"invalid color {out['color']!r} (choose from {', '.join(sorted(VALID_COLORS))})"
        )
    if out.get("max_grade") is not None:
        try:
            out["max_grade"] = int(out["max_grade"])
        except (TypeError, ValueError):
            raise ConfigError(f"max_grade must be an integer, got {out['max_grade']!r}") from None
    if "budgets" in out:
        raw = out["budgets"]
        if not isinstance(raw, dict):
            raise ConfigError(f"budgets must be a table of code = rate, got {raw!r}")
        budgets: dict[str, float] = {}
        for code, rate in raw.items():
            norm_code = str(code).upper()
            if norm_code not in BUDGET_CODES:
                raise ConfigError(
                    f"budgets: unknown code {code!r} (choose from {', '.join(sorted(BUDGET_CODES))})"
                )
            if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate < 0:
                raise ConfigError(
                    f"budgets: {norm_code} must be a non-negative number, got {rate!r}"
                )
            budgets[norm_code] = float(rate)
        out["budgets"] = budgets
    return out


def find_config(start: Path | None = None) -> dict[str, Any]:
    """Walk up from ``start`` and return the first [tool.nabokov]/.nabokov.toml found."""
    start = (start or Path.cwd()).resolve()
    for directory in [start, *start.parents]:
        dotfile = directory / ".nabokov.toml"
        if dotfile.is_file():
            with dotfile.open("rb") as fh:
                data = tomllib.load(fh)
            return _coerce(data.get("nabokov", data))
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
            tool = data.get("tool", {}).get("nabokov")
            if tool is not None:
                return _coerce(tool)
    return {}


def build_config(cli_overrides: dict[str, Any], start: Path | None = None) -> Config:
    """Merge file config with CLI overrides (CLI wins; extend-keys accumulate)."""
    merged = find_config(start)
    for key, value in cli_overrides.items():
        if value is None:
            continue
        if key in ("extend_select", "extend_ignore") and merged.get(key):
            merged[key] = tuple(merged[key]) + tuple(value)
        else:
            merged[key] = value
    return Config(**merged)
