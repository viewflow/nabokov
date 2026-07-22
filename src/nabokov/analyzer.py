"""The analysis engine: load spaCy once, run enabled rules, produce results."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache

from .checks import ALL_RULES, CheckContext
from .config import BUDGET_CODES, Config
from .data_loader import thresholds
from .issue import DocumentStats, Issue, Severity
from .readability import burstiness, classify, letters_in, reading_level, sentence_lengths
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

# A document is "line-oriented" (one thought per line — aphorism lists, blog dumps)
# when almost every non-blank line ends in terminal punctuation. There, a newline is
# a real boundary, so unpunctuated headings/titles don't glue into the paragraph
# below. Hard-wrapped prose (most lines end mid-sentence) never qualifies.
_TERMINAL_CHARS = set(".!?:;…")
_LINE_CLOSERS = "\"'”’)]}*_"  # noqa: RUF001 - curly closing quotes are intentional
_LINE_ORIENTED_RATIO = 0.8
_LINE_ORIENTED_MIN_LINES = 5


def _is_line_oriented(text: str) -> bool:
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    if len(lines) < _LINE_ORIENTED_MIN_LINES:
        return False
    punctuated = sum(1 for line in lines if line.rstrip(_LINE_CLOSERS)[-1:] in _TERMINAL_CHARS)
    return punctuated / len(lines) >= _LINE_ORIENTED_RATIO


def _starts_sentence(prev, tok, line_oriented: bool, list_marks: set[str]) -> bool:
    """Should ``tok`` open a new sentence, given the whitespace token before it?"""
    if prev is None:
        return True  # first token of the document
    if not prev.is_space:
        return False
    if prev.text.count("\n") >= 2:
        return True  # blank line = paragraph break
    return "\n" in prev.text and (line_oriented or tok.text in list_marks)


def _register_components() -> None:
    """Register a component that makes a blank line a hard sentence boundary.

    A blank line always separates paragraphs, so this stops spaCy from gluing a
    heading/badge/list fragment onto the following paragraph into one fake run-on —
    which otherwise inflates the grade and mislocates findings in Markdown. The
    newlines live inside a single whitespace token, so we key off that token.
    In line-oriented documents every newline is a boundary; elsewhere a list-marker
    line still starts its own sentence so tight lists are not glued.
    """
    global _component_registered
    if _component_registered:
        return
    from spacy.language import Language

    @Language.component("blank_line_boundaries")
    def blank_line_boundaries(doc):
        list_marks = {"-", "*", "•", "+"}
        line_oriented = _is_line_oriented(doc.text)
        for i, tok in enumerate(doc):
            prev = doc[i - 1] if i else None
            if _starts_sentence(prev, tok, line_oriented, list_marks):
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

    print(
        f"nabokov: downloading language model {MODEL} (~13 MB, one-time)…",
        file=sys.stderr,
        flush=True,
    )
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
    print("nabokov: model installed, loading…", file=sys.stderr, flush=True)


@lru_cache(maxsize=1)
def load_nlp(auto_download: bool = True):
    """Load the spaCy pipeline once per process (shared across all engines).

    The model isn't a PyPI dependency (direct-URL deps are rejected there), so on the
    first run we fetch it automatically. Disable with ``auto_download=False``.
    """
    import importlib
    import importlib.util

    # Check for the model package before the multi-second spaCy import, so on a
    # first run the download message appears immediately instead of after a
    # long silent pause that looks like a hang.
    if importlib.util.find_spec(MODEL) is None:
        if not auto_download:
            raise RuntimeError(
                f"spaCy model {MODEL!r} is not installed. "
                f"Run `nabokov download-model` (or `python -m spacy download {MODEL}`)."
            )
        download_model()
        importlib.invalidate_caches()

    import spacy

    _register_components()
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

        issues = _apply_target_rules(issues, self.config)
        issues = _apply_noqa(issues, source)
        issues = _drop_quoted(issues, source)
        issues = _dedup_adverbs(issues)
        stats = _document_stats(doc, self.config.target, issues)
        issues = _apply_budgets(issues, stats.words, self.config)
        issues = _demote_hard_sentences(issues, stats)

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


# Quoted material is evidence, not the author's prose — findings inside it are
# dropped. A quoted region is a Markdown blockquote, or a quoted span (straight or
# curly double quotes, or curly single quotes — that pair is apostrophe-safe) of at
# least _QUOTED_MIN_WORDS words: a multi-word quoted phrase is a mention, dialogue,
# or citation, none of which is the author's usage. A single-word quote does not
# make a region (an inch mark must not swallow its neighborhood), but when the
# quote holds exactly the flagged term — 'the word "delve"' — that is a pure
# mention and the finding drops too. A hard-sentence finding whose span is mostly
# quotation (an author's sentence framing a long citation) is demoted to info —
# the grade belongs to the quoted prose, not the author's.
_QUOTED_SPAN = re.compile(r"“[^“”]{1,2000}”|‘[^‘’]{1,2000}’|\"[^\"\n]{1,2000}\"")  # noqa: RUF001
_QUOTED_MIN_WORDS = 2
_QUOTED_MAJORITY = 0.5
_BLOCKQUOTE_LINE = re.compile(r"^\s*>")


def _quoted_regions(source: SourceFile) -> list[tuple[int, int]]:
    """0-based [start, end) char ranges of quoted material in the document."""
    regions = []
    for match in _QUOTED_SPAN.finditer(source.analysis_text):
        if len(match.group(0).split()) >= _QUOTED_MIN_WORDS:
            regions.append((match.start(), match.end()))
    if source.is_markdown:
        run_start = None
        n_lines = source.original_text.count("\n") + 1
        for lineno in range(1, n_lines + 2):
            quoted = lineno <= n_lines and _BLOCKQUOTE_LINE.match(source.line_text(lineno))
            if quoted and run_start is None:
                run_start = lineno
            elif not quoted and run_start is not None:
                last = lineno - 1
                regions.append(
                    (
                        source.offset(run_start, 1),
                        source.offset(last, 1) + len(source.line_text(last)),
                    )
                )
                run_start = None
    return regions


def _mention_regions(source: SourceFile) -> list[tuple[int, int]]:
    """0-based [start, end) interiors of every quoted span, single words included."""
    return [
        (match.start() + 1, match.end() - 1)
        for match in _QUOTED_SPAN.finditer(source.analysis_text)
    ]


def _drop_quoted(issues: list[Issue], source: SourceFile) -> list[Issue]:
    """Drop issues inside quoted material; demote mostly-quoted hard sentences."""
    regions = _quoted_regions(source)
    mentions = _mention_regions(source)
    if not regions and not mentions:
        return issues
    kept = []
    for issue in issues:
        start = source.offset(issue.line, issue.col)
        end = source.offset(issue.end_line, issue.end_col)
        if any(r_start <= start and end <= r_end for r_start, r_end in regions):
            continue
        # exact mention: the quote holds nothing but the flagged term
        if any(start == m_start and end == m_end for m_start, m_end in mentions):
            continue
        if issue.code in ("NB201", "NB202") and end > start:
            overlap = sum(
                max(0, min(end, r_end) - max(start, r_start)) for r_start, r_end in regions
            )
            if overlap / (end - start) > _QUOTED_MAJORITY:
                issue = replace(issue, severity=Severity.INFO)
        kept.append(issue)
    return kept


def _apply_target_rules(issues: list[Issue], config: Config) -> list[Issue]:
    """Genre suppression: some codes are not tells in some registers.

    Staccato fragments and repeated openers ARE the social-post genre, so the
    SOCIAL target switches those rules off entirely (see ``target_rules`` in
    thresholds.json). Picking another target brings them back.
    """
    table = thresholds().get("target_rules", {})
    off = set(table.get(config.target, {}).get("off", ()))
    if not off:
        return issues
    return [issue for issue in issues if issue.code not in off]


# NB301 defers to a qualifier/intensifier/hedge-stack finding on the same words:
# "probably" is a hedge, not a manner adverb, and one finding per span is enough.
_DEDUP_WINNERS = {"NB303", "NB510", "NB520"}


def _dedup_adverbs(issues: list[Issue]) -> list[Issue]:
    """Drop NB301 issues whose span is already covered by NB303/NB510."""
    winners = [
        ((i.line, i.col), (i.end_line, i.end_col)) for i in issues if i.code in _DEDUP_WINNERS
    ]
    if not winners:
        return issues
    kept = []
    for issue in issues:
        if issue.code == "NB301":
            start, end = (issue.line, issue.col), (issue.end_line, issue.end_col)
            if any(w_start < end and start < w_end for w_start, w_end in winners):
                continue
        kept.append(issue)
    return kept


def _style_budgets(config: Config) -> dict[str, float]:
    """The per-1000-word budgets for the active target, with config overrides."""
    defaults = thresholds()["style_budgets"]
    table = dict(defaults.get(config.target, defaults["NORMAL"]))
    table.update(config.budgets)
    return {code: rate for code, rate in table.items() if code in BUDGET_CODES}


def _apply_budgets(issues: list[Issue], words: int, config: Config) -> list[Issue]:
    """Density-based severity for the style checks (NB301/NB302/NB303).

    An adverb, qualifier, or passive is a style signal, not a defect — the defect is
    overuse. Within the target's per-1000-word budget the findings are advisory
    (info); over it they escalate to warnings. Short texts get a flat grace of 2
    occurrences so a single adverb in a tweet-sized snippet never escalates.
    """
    budgets = _style_budgets(config)
    counts = Counter(i.code for i in issues)
    out = []
    for issue in issues:
        rate = budgets.get(issue.code)
        if rate is not None:
            allowed = max(2, math.ceil(rate * words / 1000))
            if counts[issue.code] <= allowed:
                issue = replace(issue, severity=Severity.INFO)
        out.append(issue)
    return out


def _demote_hard_sentences(issues: list[Issue], stats: DocumentStats) -> list[Issue]:
    """NB202 drops to info when the whole document reads fine for its target.

    A grade-11 sentence in a grade-8 document is rhythm — the long half of
    burstiness — not a defect. The extreme NB201 sentences stay warnings.
    """
    if stats.readability != "normal":
        return issues
    return [replace(i, severity=Severity.INFO) if i.code == "NB202" else i for i in issues]


def _document_stats(doc, target: str, issues: list[Issue]) -> DocumentStats:
    words = [t for t in doc if not (t.is_punct or t.is_space)]
    n_words = len(words)
    n_sentences = sum(1 for _ in doc.sents)
    letters = sum(letters_in(t.text) for t in words)
    grade = reading_level(letters, n_words, n_sentences)
    bucket = classify(grade, n_words, target)
    cv = burstiness(sentence_lengths(doc))

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
        burstiness=round(cv, 2),
        counts=counts,
    )
