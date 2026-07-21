"""Command-line entry point for nabokov."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .checks import RULE_META
from .config import VALID_TARGETS, ConfigError, build_config
from .reporters import get_reporter, resolve_format
from .source import _HTML_SUFFIXES, _MD_SUFFIXES, SourceFile

TEXT_SUFFIXES = {".txt", ".text", ".rst"} | _MD_SUFFIXES | _HTML_SUFFIXES

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


def _split_codes(values: list[str] | None) -> tuple[str, ...] | None:
    if not values:
        return None
    out: list[str] = []
    for value in values:
        out.extend(part.strip().upper() for part in value.split(",") if part.strip())
    return tuple(out) or None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nabokov",
        description="A console prose linter — readability checks, flake8 workflow.",
    )
    parser.add_argument("paths", nargs="*", help="files, directories, or - for stdin")
    parser.add_argument("--version", action="version", version=f"nabokov {__version__}")
    parser.add_argument("--list-rules", action="store_true", help="print the rule catalog and exit")
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="download the spaCy language model and exit (also: `nabokov download-model`)",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=["auto", "color", "flake8", "json", "github"],
        default=None,
        help="output format (default: color on a tty, else flake8)",
    )
    parser.add_argument("--select", action="append", help="rule codes/prefixes to enable")
    parser.add_argument("--ignore", action="append", help="rule codes/prefixes to disable")
    parser.add_argument("--extend-select", action="append", help="add to the selection")
    parser.add_argument("--extend-ignore", action="append", help="add to the ignore list")
    parser.add_argument(
        "--ai",
        action="store_true",
        default=None,
        help="also run the AI-writing checks (shorthand for --extend-select NB5)",
    )
    parser.add_argument(
        "--ai-only",
        action="store_true",
        default=None,
        help="run only the AI-writing checks (shorthand for --select NB5)",
    )
    parser.add_argument(
        "--target",
        type=str.upper,
        choices=sorted(VALID_TARGETS),
        default=None,
        help="reading-level target (default: NORMAL)",
    )
    parser.add_argument(
        "--max-grade", type=int, default=None, help="fail if the document grade exceeds N"
    )
    parser.add_argument("--exit-zero", action="store_true", default=None, help="always exit 0")
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default=None,
        help="colorize output (default: auto)",
    )
    parser.add_argument(
        "--statistics", action="store_true", default=None, help="print per-code counts"
    )
    parser.add_argument(
        "--all-adverbs",
        dest="adverbs_all_pos",
        action="store_true",
        default=None,
        help="flag every adverb, not only -ly adverbs",
    )
    parser.add_argument("--stdin-display-name", default=None, help="name to show for stdin input")
    return parser


def _collect_sources(paths: Sequence[str], stdin_name: str) -> tuple[list[SourceFile], bool]:
    """Return (sources, had_missing). Missing paths print to stderr and set the flag."""
    sources: list[SourceFile] = []
    had_missing = False
    for raw in paths:
        if raw == "-":
            suffix = Path(stdin_name).suffix.lower()
            sources.append(
                SourceFile.from_text(
                    sys.stdin.read(),
                    stdin_name,
                    is_markdown=suffix in _MD_SUFFIXES,
                    is_html=suffix in _HTML_SUFFIXES,
                )
            )
            continue
        path = Path(raw)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in TEXT_SUFFIXES:
                    sources.append(SourceFile.from_path(child))
        elif path.is_file():
            sources.append(SourceFile.from_path(path))
        else:
            print(f"nabokov: {raw}: no such file or directory", file=sys.stderr)
            had_missing = True
    return sources, had_missing


def _print_rules(out) -> None:
    out.write("nabokov rules:\n")
    for code, (name, desc) in RULE_META.items():
        out.write(f"  {code}  {name:<20}  {desc}\n")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        _print_rules(sys.stdout)
        return EXIT_OK

    if args.download_model or args.paths == ["download-model"]:
        from .analyzer import download_model

        download_model()
        return EXIT_OK

    select = _split_codes(args.select) or ()
    extend_select = _split_codes(args.extend_select) or ()
    if args.ai_only:
        select = (*select, "NB5")
    if args.ai:
        extend_select = (*extend_select, "NB5")

    overrides = {
        "fmt": args.fmt,
        "select": select or None,
        "ignore": _split_codes(args.ignore),
        "extend_select": extend_select or None,
        "extend_ignore": _split_codes(args.extend_ignore),
        "target": args.target,
        "max_grade": args.max_grade,
        "exit_zero": args.exit_zero,
        "color": args.color,
        "statistics": args.statistics,
        "adverbs_all_pos": args.adverbs_all_pos,
        "stdin_display_name": args.stdin_display_name,
    }
    if not args.paths:
        parser.error("no input paths (pass files, a directory, or - for stdin)")

    try:
        config = build_config(overrides)
    except ConfigError as exc:
        print(f"nabokov: config error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    sources, had_missing = _collect_sources(args.paths, config.stdin_display_name)
    if not sources:
        if not had_missing:
            print("nabokov: no supported files found", file=sys.stderr)
        return EXIT_ERROR

    # Import the engine lazily so --help / --version / --list-rules stay instant.
    from .analyzer import Engine

    engine = Engine(config)
    results = [engine.analyze(source) for source in sources]

    fmt = resolve_format(config.fmt, sys.stdout)
    get_reporter(fmt)(results, config, sys.stdout)

    if had_missing:
        return EXIT_ERROR  # a nonexistent path is a usage error
    if config.exit_zero:
        return EXIT_OK
    return EXIT_FINDINGS if any(r.issues for r in results) else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
