"""Source-text handling: line/col mapping and length-preserving markup blanking.

The key invariant: the text we feed spaCy (``analysis_text``) is *always the same
length* as the original text, so every character offset spaCy reports maps back to the
exact (line, col) in the user's file. For Markdown and HTML we blank out non-prose
spans (code, tags, link targets, emphasis markers, table pipes) by overwriting them
with spaces rather than deleting them — offsets stay byte-for-byte aligned, and only
the visible prose is analyzed.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path

_MD_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd"}
_HTML_SUFFIXES = {".html", ".htm", ".xhtml"}


@dataclass(frozen=True)
class MarkupSpan:
    """A typed region of the original source: what sat here, and where.

    The blanking pass knows exactly what it is erasing at the moment it erases
    it — a fence, a heading marker, a link target. Recording the kind costs
    nothing and is otherwise unrecoverable: afterwards every blanked region is
    just spaces, and a heading's *text* is indistinguishable from body prose.

    This indexes source structure, not only erased text. ``link-text`` marks a
    region that survives into the analysis text and is read as prose; a rule that
    cares whether a phrase was link text needs to know that, and the blanked-text
    diff in ``markup_spans`` cannot tell it.
    """

    start: int
    end: int
    kind: str


# Every kind the index can carry. Named here so a rule can be checked against the
# set rather than guessing a string.
MARKUP_KINDS = frozenset(
    {
        "frontmatter",
        "fence",  # ``` or ~~~ block, delimiters included
        "inline-code",
        "html",  # raw HTML tag or comment inside Markdown
        "ref-def",  # [label]: url
        "citation",  # [1] Author, Title
        "image",  # the whole ![alt](src)
        "image-alt",  # just the alt text (empty span when there is none)
        "link-text",  # the visible words of [text](url) — kept, not blanked
        "link-url",  # the target of a link or image
        "url",  # bare or autolinked URL
        "heading-marker",  # the leading #s
        "heading",  # the heading's text, to end of line
        "table-row",
        "blockquote",
        "list-marker",
        "emphasis",
        "rule",  # thematic break / setext underline / table separator
    }
)


@dataclass
class SourceFile:
    """A single input document, ready for analysis."""

    display_name: str
    original_text: str
    analysis_text: str
    is_markdown: bool
    is_html: bool
    _line_starts: list[int]
    # Typed source structure, in the order the blanking pass found it.
    markup: list[MarkupSpan] = field(default_factory=list)

    @classmethod
    def from_text(
        cls,
        text: str,
        display_name: str,
        *,
        is_markdown: bool = False,
        is_html: bool = False,
    ) -> SourceFile:
        spans: list[MarkupSpan] = []
        if is_html:
            analysis = blank_html(text, spans)
        elif is_markdown:
            analysis = blank_markdown(text, spans)
        else:
            analysis = text
        return cls(
            display_name=display_name,
            original_text=text,
            analysis_text=analysis,
            is_markdown=is_markdown,
            is_html=is_html,
            _line_starts=_compute_line_starts(text),
            markup=spans,
        )

    def spans(self, *kinds: str) -> list[MarkupSpan]:
        """Every recorded span of the given kinds, in source order."""
        wanted = set(kinds)
        return sorted((s for s in self.markup if s.kind in wanted), key=lambda s: (s.start, s.end))

    def span_text(self, span: MarkupSpan) -> str:
        """The original text a span covers."""
        return self.original_text[span.start : span.end]

    @classmethod
    def from_path(cls, path: Path) -> SourceFile:
        text = path.read_text(encoding="utf-8-sig")  # tolerate BOM
        suffix = path.suffix.lower()
        return cls.from_text(
            text,
            str(path),
            is_markdown=suffix in _MD_SUFFIXES,
            is_html=suffix in _HTML_SUFFIXES,
        )

    @property
    def has_markup(self) -> bool:
        """True when the source has blanked markup (Markdown or HTML)."""
        return self.is_markdown or self.is_html

    def linecol(self, offset: int) -> tuple[int, int]:
        """Map a 0-based char offset to a 1-based (line, col)."""
        line_idx = bisect_right(self._line_starts, offset) - 1
        if line_idx < 0:
            line_idx = 0
        col = offset - self._line_starts[line_idx] + 1
        return line_idx + 1, col

    def offset(self, line: int, col: int) -> int:
        """Map a 1-based (line, col) back to a 0-based char offset (linecol inverse)."""
        return self._line_starts[line - 1] + col - 1

    def line_text(self, line: int) -> str:
        """Return the original text of a 1-based line number (no trailing newline)."""
        start = self._line_starts[line - 1]
        end = self._line_starts[line] if line < len(self._line_starts) else len(self.original_text)
        return self.original_text[start:end].rstrip("\n").rstrip("\r")

    def markup_spans(self, line: int) -> list[tuple[int, int]]:
        """0-based [start, end) column ranges on a line that were blanked as markup.

        A column is "markup" when the original had a non-space character there but the
        analysis text (fed to spaCy) has a space — i.e. syntax/URLs nabokov ignores.
        Reporters dim these so only the analyzed prose stands out.
        """
        start = self._line_starts[line - 1]
        end = self._line_starts[line] if line < len(self._line_starts) else len(self.original_text)
        original = self.original_text[start:end]
        analysis = self.analysis_text[start:end]
        spans: list[tuple[int, int]] = []
        run_start: int | None = None
        for col, (orig_ch, ana_ch) in enumerate(zip(original, analysis, strict=False)):
            is_markup = orig_ch not in "\n\r" and not orig_ch.isspace() and ana_ch == " "
            if is_markup and run_start is None:
                run_start = col
            elif not is_markup and run_start is not None:
                spans.append((run_start, col))
                run_start = None
        if run_start is not None:
            spans.append((run_start, len(original.rstrip("\n").rstrip("\r"))))
        return spans


def _compute_line_starts(text: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _blank(match: re.Match[str], keep: int | None = None) -> str:
    """Replace a match with equal-length whitespace, preserving newlines.

    If ``keep`` is a group index, that group's text is preserved in place and the
    rest of the match is blanked (used to keep visible link text while dropping the
    URL). Length is always preserved so offsets never shift.
    """
    if keep is None:
        return re.sub(r"[^\n]", " ", match.group(0))
    out = []
    for gi in range(1, (match.re.groups) + 1):
        seg = match.group(gi) or ""
        out.append(seg if gi == keep else re.sub(r"[^\n]", " ", seg))
    return "".join(out)


def _erase(
    pattern: re.Pattern[str],
    text: str,
    spans: list[MarkupSpan],
    kind: str | None,
    *,
    keep: int | None = None,
    parts: tuple[tuple[int, str], ...] = (),
) -> str:
    """Blank every match of ``pattern``, recording what was there.

    ``kind`` types the whole match; ``parts`` types individual groups — the way a
    link yields both its visible text and its target. A group that did not
    participate is skipped. Blanking is unchanged, so lengths and offsets hold.
    """

    def repl(match: re.Match[str]) -> str:
        if kind is not None:
            spans.append(MarkupSpan(match.start(), match.end(), kind))
        for index, part_kind in parts:
            start, end = match.span(index)
            if start != -1:
                spans.append(MarkupSpan(start, end, part_kind))
        return _blank(match, keep)

    return pattern.sub(repl, text)


# --- Markdown ---------------------------------------------------------------
# Order matters: fenced code first (so its contents aren't touched by later rules).
_FRONTMATTER = re.compile(r"\A---[ \t]*\n(?:[^\n]*\n)*?---[ \t]*(?=\n|\Z)")
_FENCED_CODE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_HTML_IN_MD = re.compile(r"<!--.*?-->|</?[a-zA-Z][^>]*>", re.DOTALL)
_IMAGE = re.compile(r"(!\[)([^\]]*)(\]\()([^)]*)(\))")
_LINK = re.compile(r"(\[)([^\]]*)(\]\()([^)]*)(\))")
_HEADING = re.compile(r"^(#{1,6}\s+)", re.MULTILINE)
# thematic breaks, setext underlines, and table separator rows (---, ===, |--|:-:|)
_RULE_OR_SEP = re.compile(r"^[ \t]*[|:=\- \t]*[-=][|:=\- \t]*$", re.MULTILINE)
_BLOCKQUOTE = re.compile(r"^(\s*>+\s?)", re.MULTILINE)
_LIST_MARKER = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)", re.MULTILINE)
# `*`/`~~` always; `_` only at word boundaries so snake_case identifiers survive.
_EMPHASIS = re.compile(
    r"\*{1,3}|~~"
    r"|(?<![A-Za-z0-9])_{1,3}(?=[A-Za-z0-9])"
    r"|(?<=[A-Za-z0-9])_{1,3}(?![A-Za-z0-9])"
)
_LINE = re.compile(r"^[^\n]*$", re.MULTILINE)
# reference-link definitions ([label]: url) and numbered citations ([1] Author, ...)
_REF_DEF = re.compile(r"^[ \t]*\[[^\]\n]+\]:[ \t]+\S[^\n]*$", re.MULTILINE)
_NUM_CITATION = re.compile(r"^[ \t]*\[\d+\][ \t]+\S[^\n]*$", re.MULTILINE)
# autolinks and bare URLs — never prose
_AUTOLINK = re.compile(r"<https?://[^>\s]+>")
_BARE_URL = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]]+")


def _blank_table_pipes(match: re.Match[str]) -> str:
    """Blank the `|` cell delimiters on a table row (a line with 2+ pipes)."""
    line = match.group(0)
    return line.replace("|", " ") if line.count("|") >= 2 else line


def _blank_list_marker(match: re.Match[str]) -> str:
    """Blank a list marker, leaving a newline where the bullet sat.

    The extra newline gives the marker's line a blank-line boundary, so the
    sentence component starts a new sentence at every list item — a tight list
    (no blank lines between items) is not glued into one mega-sentence. Length
    is preserved; only whitespace shape changes.
    """
    seg = match.group(0)
    out = re.sub(r"[^\n]", " ", seg)
    bullet = len(seg) - len(seg.lstrip())
    return out[:bullet] + "\n" + out[bullet + 1 :]


def blank_markdown(text: str, spans: list[MarkupSpan] | None = None) -> str:
    """Return ``text`` with non-prose Markdown markup replaced by equal-length spaces.

    Pass ``spans`` to also collect a typed index of what was found. Order still
    matters — fenced code goes first, so a link inside a code block is neither
    blanked twice nor recorded as a link.
    """
    spans = [] if spans is None else spans
    text = _erase(_FRONTMATTER, text, spans, "frontmatter")  # YAML metadata at the top
    text = _erase(_FENCED_CODE, text, spans, "fence")
    text = _erase(_INLINE_CODE, text, spans, "inline-code")
    _index_img_tags(text, spans)  # before the tag sweep blanks the alt attribute
    text = _erase(_HTML_IN_MD, text, spans, "html")
    text = _erase(_REF_DEF, text, spans, "ref-def")  # [label]: url definitions
    text = _erase(_NUM_CITATION, text, spans, "citation")  # [1] Author, Title, Year. url
    # keep visible text (group 2), blank the brackets + URL. The alt-text span is
    # recorded even when empty — an empty alt is exactly what a rule looks for.
    text = _erase(_IMAGE, text, spans, "image", keep=2, parts=((2, "image-alt"), (4, "link-url")))
    text = _erase(_LINK, text, spans, None, keep=2, parts=((2, "link-text"), (4, "link-url")))
    text = _erase(_AUTOLINK, text, spans, "url")
    text = _erase(_BARE_URL, text, spans, "url")
    text = _erase_headings(text, spans)
    text = _erase(_RULE_OR_SEP, text, spans, "rule")
    text = _erase_table_rows(text, spans)
    text = _erase(_BLOCKQUOTE, text, spans, "blockquote")
    text = _erase_list_markers(text, spans)
    text = _erase(_EMPHASIS, text, spans, "emphasis")
    return text


_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ALT_ATTR = re.compile(r"""\balt\s*=\s*("([^"]*)"|'([^']*)')""", re.IGNORECASE)


def _index_img_tags(text: str, spans: list[MarkupSpan]) -> None:
    """Record raw ``<img>`` tags and their alt attributes.

    Runs for Markdown as well as HTML: a README that centres its screenshots, or
    carries badges, reaches for a raw tag as soon as Markdown's syntax runs out.
    Must run *before* the tag sweep blanks the attribute out of reach.

    A tag with no ``alt`` records an empty span at the tag's start — the same
    shape Markdown's ``![](src)`` produces, so a rule handles one case, not two.
    """
    for tag in _IMG_TAG.finditer(text):
        spans.append(MarkupSpan(tag.start(), tag.end(), "image"))
        attr = _ALT_ATTR.search(tag.group(0))
        if attr is None:
            spans.append(MarkupSpan(tag.start(), tag.start(), "image-alt"))
            continue
        # group 2 or 3, depending on which quote style was used
        index = 2 if attr.group(2) is not None else 3
        start = tag.start() + attr.start(index)
        spans.append(MarkupSpan(start, start + len(attr.group(index)), "image-alt"))


def _erase_headings(text: str, spans: list[MarkupSpan]) -> str:
    """Blank the leading #s, and record the heading's text separately.

    The marker is markup and the text is prose, so they are different kinds. A
    rule about heading punctuation or capitalization wants the text range, which
    is otherwise indistinguishable from an ordinary line once the #s are spaces.
    """

    def repl(match: re.Match[str]) -> str:
        spans.append(MarkupSpan(match.start(), match.end(), "heading-marker"))
        line_end = text.find("\n", match.end())
        spans.append(MarkupSpan(match.end(), len(text) if line_end == -1 else line_end, "heading"))
        return _blank(match)

    return _HEADING.sub(repl, text)


def _erase_table_rows(text: str, spans: list[MarkupSpan]) -> str:
    """Blank the `|` delimiters, recording only the lines that really are rows."""

    def repl(match: re.Match[str]) -> str:
        line = match.group(0)
        if line.count("|") < 2:
            return line
        spans.append(MarkupSpan(match.start(), match.end(), "table-row"))
        return line.replace("|", " ")

    return _LINE.sub(repl, text)


def _erase_list_markers(text: str, spans: list[MarkupSpan]) -> str:
    def repl(match: re.Match[str]) -> str:
        spans.append(MarkupSpan(match.start(), match.end(), "list-marker"))
        return _blank_list_marker(match)

    return _LIST_MARKER.sub(repl, text)


# --- HTML -------------------------------------------------------------------
_HTML_BLOCK = re.compile(
    r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|<!--.*?-->",
    re.DOTALL | re.IGNORECASE,
)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def blank_html(text: str, spans: list[MarkupSpan] | None = None) -> str:
    """Return ``text`` with HTML tags, comments, and script/style blanked out."""
    spans = [] if spans is None else spans
    _index_img_tags(text, spans)
    text = _erase(_HTML_BLOCK, text, spans, "html")
    text = _erase(_HTML_TAG, text, spans, "html")
    return text
