"""NB311 — image with no alt text. The first rule built on the markup index."""

from __future__ import annotations

import pytest

from nabokov.issue import Applicability, Severity


def _found(result, code="NB311"):
    return [i for i in result.issues if i.code == code]


@pytest.mark.parametrize(
    ("text", "markdown", "html"),
    [
        ("![](chart.png)\n", True, False),
        ('<img src="chart.png">\n', True, False),
        ('<img src="chart.png">\n', False, True),
        ('<img alt="" src="chart.png">\n', False, True),
        ("![   ](chart.png)\n", True, False),  # whitespace is not a description
    ],
)
def test_missing_alt_flagged(analyze, text, markdown, html):
    result = analyze(text, is_markdown=markdown, is_html=html, name="t.md")
    assert _found(result), text


@pytest.mark.parametrize(
    ("text", "markdown", "html"),
    [
        ("![Revenue by quarter](chart.png)\n", True, False),
        ('<img src="c.png" alt="Revenue by quarter">\n', True, False),
        ("<img src='c.png' alt='Revenue by quarter'>\n", False, True),
    ],
)
def test_described_image_not_flagged(analyze, text, markdown, html):
    result = analyze(text, is_markdown=markdown, is_html=html, name="t.md")
    assert not _found(result), text


def test_image_inside_a_code_fence_not_flagged(analyze):
    """Showing the syntax is not using it — fences blank before indexing."""
    text = '# T\n\n```html\n<img src="x.png">\n```\n'
    assert not _found(analyze(text, is_markdown=True))


def test_plain_text_never_fires(analyze):
    assert not _found(analyze("![](x.png) is markdown syntax, but this is a .txt\n"))


def test_is_advisory_and_info(analyze):
    """Only the author knows what the picture shows; and an empty alt is a
    legitimate marking for a decorative image, so this is never a warning."""
    issue = _found(analyze("![](chart.png)\n", is_markdown=True))[0]
    assert issue.applicability is Applicability.ADVISORY
    assert issue.suggestion is None
    assert issue.severity is Severity.INFO
    assert "decorative" in issue.message


def test_span_covers_the_whole_image(analyze):
    issue = _found(analyze("Look: ![](chart.png) here.\n", is_markdown=True))[0]
    assert issue.text == "![](chart.png)"


def test_several_images_each_reported(analyze):
    text = "![](a.png)\n\n![Described](b.png)\n\n![](c.png)\n"
    assert len(_found(analyze(text, is_markdown=True))) == 2
