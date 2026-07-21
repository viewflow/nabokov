"""The analysis engine: load spaCy once, run enabled rules, produce results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from .checks import ALL_RULES, CheckContext
from .config import Config
from .issue import DocumentStats, Issue, Severity
from .readability import classify, letters_in, reading_level
from .source import SourceFile

_NOQA = re.compile(
    r"nabokov:\s*(?:ignore|disable|noqa)(?:\s*[:=]\s*|\s+)?([A-Za-z0-9,\s]*)",
    re.IGNORECASE,
)

_CATEGORY_BY_CODE = {
    "NB301": "adverbs",
    "NB302": "passiveVoices",
    "NB303": "qualifiers",
    "NB401": "complexWords",
    "NB202": "hardSentences",
    "NB201": "veryHardSentences",
}


@dataclass
class AnalysisResult:
    source: SourceFile
    issues: list[Issue]
    stats: DocumentStats


_component_registered = False


def _register_components() -> None:
    """Register a component that makes a blank line a hard sentence boundary.

    A blank line always separates paragraphs, so this stops spaCy from gluing a
    heading/badge/list fragment onto the following paragraph into one fake run-on —
    which otherwise inflates the grade and mislocates findings in Markdown. The
    newlines live inside a single whitespace token, so we key off that token.
    """
    global _component_registered
    if _component_registered:
        return
    from spacy.language import Language

    @Language.component("blank_line_boundaries")
    def blank_line_boundaries(doc):
        for i, tok in enumerate(doc):
            if i == 0 or (doc[i - 1].is_space and doc[i - 1].text.count("\n") >= 2):
                tok.is_sent_start = True
            elif tok.is_space:
                tok.is_sent_start = False
        return doc

    _component_registered = True


MODEL = "en_core_web_sm"
MODEL_URL = (
    "https://github.com/explosion/spacy-models/releases/download/"
    "en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
)


def download_model() -> None:
    """Fetch the spaCy language model into the current environment.

    Installs straight into ``sys.executable`` rather than delegating to
    ``spacy.cli.download``: that helper falls back to a bare ``uv pip
    install`` when no ``pip`` binary is on PATH (the case inside a `uvx`
    tool environment, which ships without pip), and without ``--python``
    that installs into whichever venv `uv` happens to discover from the
    cwd — not the environment `nabokov` is actually running in.
    """
    import importlib.util
    import shutil
    import subprocess
    import sys

    print(f"nabokov: downloading language model {MODEL} (one-time)…", file=sys.stderr)
    if importlib.util.find_spec("pip") is not None:
        cmd = [sys.executable, "-m", "pip", "install", "--no-input", MODEL_URL]
    elif shutil.which("uv"):
        cmd = ["uv", "pip", "install", "--python", sys.executable, MODEL_URL]
    else:
        raise RuntimeError(
            "No package installer found. spaCy models require either pip or uv "
            "to be available to download and install."
        )
    subprocess.run(cmd, check=True)  # noqa: S603 - cmd built from constants above


@lru_cache(maxsize=1)
def load_nlp(auto_download: bool = True):
    """Load the spaCy pipeline once per process (shared across all engines).

    The model isn't a PyPI dependency (direct-URL deps are rejected there), so on the
    first run we fetch it automatically. Disable with ``auto_download=False``.
    """
    import importlib

    import spacy

    _register_components()
    try:
        nlp = spacy.load(MODEL, disable=["ner"])
    except OSError:
        if not auto_download:
            raise RuntimeError(
                f"spaCy model {MODEL!r} is not installed. "
                f"Run `nabokov download-model` (or `python -m spacy download {MODEL}`)."
            ) from None
        download_model()
        importlib.invalidate_caches()
        nlp = spacy.load(MODEL, disable=["ner"])
    nlp.add_pipe("blank_line_boundaries", before="parser")
    return nlp


class Engine:
    """Owns the spaCy pipeline (loaded once, lazily) and runs the enabled rules."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            self._nlp = load_nlp()
        return self._nlp

    def analyze(self, source: SourceFile) -> AnalysisResult:
        doc = self.nlp(source.analysis_text)
        enabled = self.config.enabled_codes()
        ctx = CheckContext(doc=doc, source=source, config=self.config, nlp=self.nlp)
        issues: list[Issue] = []
        for rule in ALL_RULES:
            if not set(rule.codes) & enabled:
                continue
            for issue in rule.check(ctx):
                if issue.code in enabled:
                    issues.append(issue)

        issues = _apply_noqa(issues, source)
        stats = _document_stats(doc, self.config.target, issues)

        if (
            self.config.max_grade is not None
            and stats.grade > self.config.max_grade
            and not self.config.is_ignored("NB101")
        ):
            issues.append(
                Issue(
                    code="NB101",
                    name="readability",
                    message=(
                        f"document grade {stats.grade} exceeds max-grade {self.config.max_grade}"
                    ),
                    line=1,
                    col=1,
                    end_line=1,
                    end_col=1,
                    severity=Severity.ERROR,
                )
            )

        issues.sort(key=lambda i: i.sort_key)
        return AnalysisResult(source=source, issues=issues, stats=stats)


def _apply_noqa(issues: list[Issue], source: SourceFile) -> list[Issue]:
    """Drop issues suppressed by an inline `nabokov: ignore[=CODES]` comment."""
    suppress: dict[int, set[str] | None] = {}
    for lineno in range(1, source.original_text.count("\n") + 2):
        text = source.line_text(lineno)
        match = _NOQA.search(text)
        if not match:
            continue
        codes = {c.strip().upper() for c in match.group(1).split(",") if c.strip()}
        suppress[lineno] = codes or None  # None == suppress everything on this line

    if not suppress:
        return issues
    kept = []
    for issue in issues:
        rule = suppress.get(issue.line, "absent")
        if rule == "absent":
            kept.append(issue)
        elif rule is None:
            continue  # blanket suppression
        elif issue.code not in rule:
            kept.append(issue)
    return kept


def _document_stats(doc, target: str, issues: list[Issue]) -> DocumentStats:
    words = [t for t in doc if not (t.is_punct or t.is_space)]
    n_words = len(words)
    n_sentences = sum(1 for _ in doc.sents)
    letters = sum(letters_in(t.text) for t in words)
    grade = reading_level(letters, n_words, n_sentences)
    bucket = classify(grade, n_words, target)

    counts = dict.fromkeys(
        [
            "adverbs",
            "complexWords",
            "hardSentences",
            "passiveVoices",
            "qualifiers",
            "veryHardSentences",
        ],
        0,
    )
    for issue in issues:
        cat = _CATEGORY_BY_CODE.get(issue.code)
        if cat:
            counts[cat] += 1

    return DocumentStats(
        grade=grade,
        readability=bucket,
        words=n_words,
        sentences=n_sentences,
        letters=letters,
        reading_time_secs=n_words / 250 * 60,
        counts=counts,
    )
