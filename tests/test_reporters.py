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
    # a lone adverb is within the style budget, so it reports as a notice
    result = analyze("He quickly ran to the store.", name="a.txt")
    text = _render("github", result)
    assert "::notice file=a.txt,line=1,col=4::NB301" in text


def test_color_never_is_plain(analyze):
    result = analyze("He quickly ran to the store.", name="a.txt")
    text = _render("color", result, Config(color="never"))
    assert "\x1b[" not in text  # no ANSI escapes
    assert "NB301" in text


def test_statistics(analyze):
    result = analyze("He quickly and slowly ran.", name="a.txt")
    text = _render("flake8", result, Config(statistics=True))
    assert "Statistics" in text


def test_doc_stats_flag(analyze):
    result = analyze("He quickly ran to the store. Then he walked home.", name="a.txt")
    text = _render("flake8", result, Config(doc_stats=True))
    assert "Document stats" in text
    assert "burstiness=" in text
    # off by default
    assert "Document stats" not in _render("flake8", result)


def test_json_summary_has_burstiness(analyze):
    result = analyze("He quickly ran to the store. Then he walked home slowly.", name="a.txt")
    entry = json.loads(_render("json", result))[0]
    assert "burstiness" in entry["summary"]
    assert isinstance(entry["summary"]["burstiness"], (int, float))


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


# --- fix suggestions ---------------------------------------------------------
# One rule states a fix once; each reporter decides how to show it. These pin
# the wording per format, because editors parse flake8 lines and the arrow-vs-
# "try:" distinction is what tells a reader whether the fix is safe to paste.

AI = Config(extend_select=("NB5",))
WORDY = "We should use it in order to win."


def test_flake8_appends_the_fix_to_the_message(analyze):
    """Inline, not on a second line — editors attach one finding per line."""
    text = _render("flake8", analyze(WORDY, name="a.txt"))
    assert "a.txt:1:18: NB401 wordy: 'in order to' → to" in text


def test_flake8_marks_a_rewrite_differently(analyze):
    text = _render("flake8", analyze("The report was written by the team.", name="a.txt"))
    assert "try: The team wrote the report" in text


def test_color_puts_the_fix_on_its_own_line(analyze):
    text = _render("color", analyze(WORDY), Config(color="never"))
    assert "\n      → to\n" in text


def test_github_puts_the_fix_on_a_second_line(analyze):
    text = _render("github", analyze(WORDY))
    assert "%0A→ to" in text  # %0A is the annotation newline escape


def test_json_carries_the_applicability_tier(analyze):
    payload = json.loads(_render("json", analyze(WORDY)))
    entry = next(d for d in payload[0]["diagnostics"] if d["code"] == "NB401")
    assert entry["suggestion"] == "to"
    assert entry["applicability"] == "replace"


def test_json_marks_a_finding_without_a_fix_advisory(analyze):
    payload = json.loads(_render("json", analyze("He quickly ran to the store.")))
    entry = next(d for d in payload[0]["diagnostics"] if d["code"] == "NB301")
    assert entry["suggestion"] is None
    assert entry["applicability"] == "advisory"


def test_deletion_renders_as_delete_it(analyze):
    text = _render("flake8", analyze("This is very fast today.", config=AI))
    assert "→ delete it" in text


def test_hotspots_absent_unless_requested(analyze):
    result = analyze(WORDY)
    assert "Hotspots" not in _render("flake8", result)
    assert "Hotspots" in _render("flake8", result, Config(hotspots=3))
