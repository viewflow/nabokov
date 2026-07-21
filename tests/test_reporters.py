"""Reporter output tests (plain formats; color forced off for determinism)."""

from __future__ import annotations

import io
import json

from nabokov.config import Config
from nabokov.reporters import get_reporter


def _render(fmt, result, config=None):
    out = io.StringIO()
    get_reporter(fmt)([result], config or Config(), out)
    return out.getvalue()


def test_flake8_format(analyze):
    result = analyze("He quickly ran to the store.", name="a.txt")
    text = _render("flake8", result)
    assert "a.txt:1:4: NB301" in text
    assert "1 issue" in text or "issues" in text


def test_json_format_shape(analyze):
    result = analyze("He quickly ran to the store.", name="a.txt")
    payload = json.loads(_render("json", result))
    assert isinstance(payload, list)
    entry = payload[0]
    assert entry["path"] == "a.txt"
    assert "grade" in entry["summary"]
    assert any(d["code"] == "NB301" for d in entry["diagnostics"])


def test_github_annotations(analyze):
    result = analyze("He quickly ran to the store.", name="a.txt")
    text = _render("github", result)
    assert "::warning file=a.txt,line=1,col=4::NB301" in text


def test_color_never_is_plain(analyze):
    result = analyze("He quickly ran to the store.", name="a.txt")
    text = _render("color", result, Config(color="never"))
    assert "\x1b[" not in text  # no ANSI escapes
    assert "NB301" in text


def test_statistics(analyze):
    result = analyze("He quickly and slowly ran.", name="a.txt")
    text = _render("flake8", result, Config(statistics=True))
    assert "Statistics" in text


def test_color_uses_inline_highlight_not_carets(analyze):
    result = analyze("He quickly ran to the corner store today.", name="a.txt")
    text = _render("color", result, Config(color="never"))
    assert "^^^" not in text  # inline highlighting, not a separate caret line
    assert "NB301" in text


def test_color_truncates_long_lines(analyze):
    long_line = "This " + "extremely padded filler clause " * 25 + "was written by the whole team."
    result = analyze(long_line, name="a.txt")
    text = _render("color", result, Config(color="never"))
    # the long source line must be windowed with an ellipsis, never dumped whole
    assert "…" in text
    assert max(len(line) for line in text.splitlines()) < 120
