"""nabokov linter wrapper.

The linter is English-only (spaCy en model), so Cyrillic-dominant texts skip
it: they get the DeepSeek rewrite but no before/after score. spaCy is
synchronous and CPU-bound — callers run these functions via
``asyncio.to_thread``.
"""

from functools import lru_cache


def is_english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    cyrillic = sum(1 for c in letters if "Ѐ" <= c <= "ӿ")
    return cyrillic / len(letters) < 0.3


@lru_cache(maxsize=1)
def _engine():
    from nabokov.analyzer import Engine
    from nabokov.config import Config

    return Engine(Config(target="SOCIAL", extend_select=("NB5",)))


def lint(text: str) -> dict | None:
    """Score + findings for an English text; None for non-English."""
    if not is_english(text):
        return None
    from nabokov.score import compute
    from nabokov.source import SourceFile

    source = SourceFile.from_text(text, "text.md", is_markdown=True)
    result = _engine().analyze(source)
    score = compute(result)
    findings = [
        {"line": i.line, "code": i.code, "message": i.message}
        for i in result.issues
    ]
    return {
        "score": score.get("score"),
        "findings_count": len(findings),
        "findings": findings[:20],
    }
