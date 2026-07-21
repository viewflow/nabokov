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
from dataclasses import dataclass
from pathlib import Path

_MD_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd"}
_HTML_SUFFIXES = {".html", ".htm", ".xhtml"}


@dataclass
class SourceFile:
    """A single input document, ready for analysis."""

    display_name: str
    original_text: str
    analysis_text: str
    is_markdown: bool
    is_html: bool
    _line_starts: list[int]

    @classmethod
    def from_text(
        cls,
        text: str,
        display_name: str,
        *,
        is_markdown: bool = False,
        is_html: bool = False,
    ) -> SourceFile:
        if is_html:
            analysis = blank_html(text)
        elif is_markdown:
            analysis = blank_markdown(text)
        else:
            analysis = text
        return cls(
            display_name=display_name,
            original_text=text,
            analysis_text=analysis,
            is_markdown=is_markdown,
            is_html=is_html,
            _line_starts=_compute_line_starts(text),
        )

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


def blank_markdown(text: str) -> str:
    """Return ``text`` with non-prose Markdown markup replaced by equal-length spaces."""
    text = _FRONTMATTER.sub(_blank, text)  # YAML metadata block at the top
    text = _FENCED_CODE.sub(_blank, text)
    text = _INLINE_CODE.sub(_blank, text)
    text = _HTML_IN_MD.sub(_blank, text)
    text = _REF_DEF.sub(_blank, text)  # [label]: url definitions
    text = _NUM_CITATION.sub(_blank, text)  # [1] Author, Title, Year. url
    # keep visible text (group 2), blank the brackets + URL
    text = _IMAGE.sub(lambda m: _blank(m, keep=2), text)
    text = _LINK.sub(lambda m: _blank(m, keep=2), text)
    text = _AUTOLINK.sub(_blank, text)
    text = _BARE_URL.sub(_blank, text)
    text = _HEADING.sub(_blank, text)
    text = _RULE_OR_SEP.sub(_blank, text)
    text = _LINE.sub(_blank_table_pipes, text)
    text = _BLOCKQUOTE.sub(_blank, text)
    text = _LIST_MARKER.sub(_blank_list_marker, text)
    text = _EMPHASIS.sub(_blank, text)
    return text


# --- HTML -------------------------------------------------------------------
_HTML_BLOCK = re.compile(
    r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|<!--.*?-->",
    re.DOTALL | re.IGNORECASE,
)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def blank_html(text: str) -> str:
    """Return ``text`` with HTML tags, comments, and script/style blanked out."""
    text = _HTML_BLOCK.sub(_blank, text)
    text = _HTML_TAG.sub(_blank, text)
    return text
