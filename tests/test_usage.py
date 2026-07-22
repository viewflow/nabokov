"""Tests for NB306 (repeated word) and NB307 (uncomparable)."""

from __future__ import annotations

from nabokov.config import Config

NB306 = Config(select=("NB306",))
NB307 = Config(select=("NB307",))


def test_repeated_word(analyze):
    r = analyze("I saw the the problem.", config=NB306)
    assert [i.code for i in r.issues] == ["NB306"]
    assert "the the" in r.issues[0].message


def test_repeated_word_across_line_break(analyze):
    # the classic illusion hides on the line wrap
    r = analyze("Paris in the\nthe spring is lovely.", config=NB306)
    assert [i.code for i in r.issues] == ["NB306"]


def test_repeated_word_skips_grammatical_doubles(analyze):
    r = analyze("He had had enough. I know that that argument fails.", config=NB306)
    assert not r.issues


def test_repeated_word_skips_proper_nouns_and_emphasis_runs(analyze):
    r = analyze("No no no, said Duran Duran in Pago Pago.", config=NB306)
    assert not r.issues


def test_repeated_word_case_insensitive(analyze):
    r = analyze("It failed. The\nthe log shows why.", config=NB306)
    assert [i.code for i in r.issues] == ["NB306"]


def test_uncomparable(analyze):
    r = analyze("This approach is very unique and the most perfect fit.", config=NB307)
    msgs = [i.message for i in r.issues]
    assert len(msgs) == 2
    assert "drop 'very'" in msgs[0]
    assert "drop 'most'" in msgs[1]


def test_uncomparable_allows_approximators(analyze):
    # "almost impossible" is correct usage; bare absolutes are fine too
    r = analyze(
        "The system is almost impossible to break and nearly universal. She is unique.",
        config=NB307,
    )
    assert not r.issues


def test_uncomparable_needs_adjective(analyze):
    # "most" before a noun use should not fire ("very ideal" fires; "most ideals" doesn't)
    r = analyze("Most ideals fade with age.", config=NB307)
    assert not r.issues


def test_uncomparable_soft_absolutes_allow_comparison(analyze):
    # ordinary edited prose — comparatives on soft absolutes are not errors
    r = analyze(
        "Caching is the most essential feature. We need a more universal solution.",
        config=NB307,
    )
    assert not r.issues


def test_uncomparable_soft_absolutes_reject_intensifiers(analyze):
    r = analyze("This step is really essential and very ideal.", config=NB307)
    assert len(r.issues) == 2
