"""Tests for offset->line/col mapping and length-preserving markdown blanking."""

from __future__ import annotations

from nabokov.config import Config
from nabokov.source import SourceFile, blank_html, blank_markdown


def test_linecol_multiline():
    src = SourceFile.from_text("ab\ncde\nf", "t.txt", is_markdown=False)
    assert src.linecol(0) == (1, 1)
    assert src.linecol(1) == (1, 2)
    assert src.linecol(3) == (2, 1)  # first char of line 2
    assert src.linecol(4) == (2, 2)
    assert src.linecol(7) == (3, 1)


def test_linecol_crlf():
    src = SourceFile.from_text("ab\r\ncd", "t.txt", is_markdown=False)
    # offset of 'c' is 4 (a,b,\r,\n,c)
    assert src.linecol(4) == (2, 1)


def test_line_text():
    src = SourceFile.from_text("first line\nsecond line\n", "t.txt", is_markdown=False)
    assert src.line_text(1) == "first line"
    assert src.line_text(2) == "second line"


def test_blank_markdown_preserves_length():
    text = "# Title\n\nSome **bold** text with `code` here.\n"
    blanked = blank_markdown(text)
    assert len(blanked) == len(text)
    # newlines preserved at the same positions
    assert [i for i, c in enumerate(text) if c == "\n"] == [
        i for i, c in enumerate(blanked) if c == "\n"
    ]


def test_blank_markdown_removes_code_keeps_prose():
    text = "Use `utilize` sparingly but really consider it.\n"
    blanked = blank_markdown(text)
    assert "utilize" not in blanked  # inline code blanked
    assert "really" in blanked  # prose kept


def test_blank_fenced_code():
    text = "Intro.\n\n```\nadverbs quickly here\n```\n\nOutro.\n"
    blanked = blank_markdown(text)
    assert "quickly" not in blanked
    assert "Intro" in blanked and "Outro" in blanked


def test_blank_link_keeps_visible_text():
    text = "See [the docs](https://example.com/page) now.\n"
    blanked = blank_markdown(text)
    assert "the docs" in blanked
    assert "example.com" not in blanked
    assert len(blanked) == len(text)


def test_markdown_code_not_linted(analyze):
    text = "Prose is fine.\n\n```\nThis was written slowly and carefully.\n```\n"
    result = analyze(text, is_markdown=True, name="doc.md")
    # the passive/adverbs inside the code fence must not be flagged
    assert result.issues == []


def test_blank_line_breaks_sentences(analyze):
    # a short heading fragment then a paragraph must not glue into one run-on
    text = (
        "Short Heading\n\n"
        "This is a completely separate paragraph standing entirely on its own line.\n"
    )
    result = analyze(text, is_markdown=True, name="d.md")
    assert result.stats.sentences >= 2
    # nothing should be anchored on the 2-word heading line
    assert all(i.line != 1 for i in result.issues)


def test_markdown_link_url_not_flagged(analyze):
    text = "See [the guide](https://example.com/really-long-slug-here) now.\n"
    result = analyze(text, is_markdown=True, name="d.md")
    # the URL slug ("really-...") must not surface as prose (e.g. an adverb)
    assert all("example.com" not in i.text for i in result.issues)


def test_snake_case_identifier_preserved():
    # intra-word underscores must survive; only emphasis underscores are blanked
    assert "user_name_field" in blank_markdown("set the user_name_field now")


def test_markdown_emphasis_underscore_blanked():
    assert "_" not in blank_markdown("this is _emphasized_ text here")


def test_table_pipes_and_separator_blanked():
    text = "| Name | Age |\n|------|-----|\n| Bob  | 30  |\n"
    blanked = blank_markdown(text)
    assert "|" not in blanked
    assert len(blanked) == len(text)


def test_blank_html_drops_tags_keeps_prose():
    text = "<p>Hello <b>world</b></p>"
    blanked = blank_html(text)
    assert len(blanked) == len(text)
    assert "<" not in blanked and ">" not in blanked
    assert "Hello" in blanked and "world" in blanked


def test_html_prose_flagged_tags_ignored(analyze):
    result = analyze(
        "<p>He <b>quickly</b> ran to the store.</p>",
        is_html=True,
        name="x.html",
        config=Config(select=("NB301",)),
    )
    assert any(i.code == "NB301" and i.text == "quickly" for i in result.issues)


def test_html_script_not_linted(analyze):
    text = "<p>Fine prose.</p>\n<script>the cake was eaten by dogs</script>\n"
    result = analyze(text, is_html=True, name="x.html")
    assert not any(i.code == "NB302" for i in result.issues)  # script content ignored


def test_yaml_frontmatter_blanked():
    text = "---\ntitle: A Very Long Complicated Overwrought Title\ntags: [a, b]\n---\n\n# H\n\nProse.\n"
    blanked = blank_markdown(text)
    assert "title" not in blanked and "Overwrought" not in blanked  # frontmatter gone
    assert "Prose" in blanked  # body kept
    assert len(blanked) == len(text)


def test_frontmatter_not_confused_with_thematic_break():
    text = "# Title\n\nReal prose here.\n\n---\n\nMore real prose here.\n"
    blanked = blank_markdown(text)
    assert "Real prose here" in blanked
    assert "More real prose here" in blanked


def test_numbered_citation_blanked():
    text = "Body prose.\n\n[1] Cheng et al., Some Paper Title, 2025. https://example.com/x\n"
    blanked = blank_markdown(text)
    assert "Cheng" not in blanked  # citation line blanked
    assert "Body prose" in blanked


def test_reference_definition_blanked():
    blanked = blank_markdown('Text.\n\n[label]: https://example.com "A Title"\n')
    assert "example.com" not in blanked


def test_bare_url_blanked():
    blanked = blank_markdown("See https://example.com/really-long-slug for details.\n")
    assert "http" not in blanked
    assert "details" in blanked
