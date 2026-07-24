"""Tests for the author style profile builder."""

from __future__ import annotations

import json

import pytest

from nabokov.config import Config
from nabokov.source import SourceFile
from nabokov.styleprofile import build_profile, render_card

DOC_A = (
    "But the plan worked. We shipped the release on Tuesday, and the customers "
    "stayed happy for a month. But nobody expected the queue to stay quiet.\n\n"
    "So the team celebrated. The release had taken three weeks of hard work.\n"
)
DOC_B = (
    "But the second release went faster. We shipped it in a week, and the "
    "customers noticed the difference immediately.\n\n"
    "So the pattern held. Shipping early kept the queue quiet and the team calm.\n"
)


def _profile():
    sources = [
        SourceFile.from_text(DOC_A, "a.txt"),
        SourceFile.from_text(DOC_B, "b.txt"),
    ]
    return build_profile(sources, name="testauthor")


def test_profile_counts_and_shape():
    p = _profile()
    assert p["name"] == "testauthor"
    assert p["corpus"]["docs"] == 2
    assert p["corpus"]["words"] > 50
    assert p["corpus"]["sentences"] >= 8


def test_function_words_and_connectors():
    p = _profile()
    assert "the" in p["function_words_per_1000"]
    # both docs open sentences with "But" and "So"
    assert p["connectors_per_1000_sentences"]["but"] > 0
    assert p["connectors_per_1000_sentences"]["so"] > 0


def test_favorites_require_recurrence_across_docs():
    p = _profile()
    # "release" and "customers" appear in both docs; "celebrated" only in one
    favorites = p["favorite_words_per_1000"]
    assert "release" in favorites
    assert "celebrate" not in favorites


def test_rates_are_bounded():
    p = _profile()
    r = p["rhythm"]
    assert 0.0 <= r["punchline_ending_share"] <= 1.0
    assert 0.0 <= r["fragment_share"] <= 1.0
    assert r["sentence_mean"] > 0


def test_profile_is_json_serializable():
    json.dumps(_profile())


def test_card_renders_with_small_corpus_warning():
    card = render_card(_profile())
    assert "Voice card — testauthor" in card
    assert "Small corpus" in card  # well under 10k words
    assert "never" in card  # the no-fabrication footer


def test_cli_build_profile(tmp_path, capsys):
    from nabokov.cli import main

    (tmp_path / "one.txt").write_text(DOC_A, encoding="utf-8")
    (tmp_path / "two.txt").write_text(DOC_B, encoding="utf-8")
    out = tmp_path / "author.style.json"
    rc = main([str(tmp_path), "--build-profile", str(out)])
    assert rc == 0
    assert out.exists()
    profile = json.loads(out.read_text(encoding="utf-8"))
    assert profile["name"] == "author"
    assert "Voice card" in capsys.readouterr().out


# --- NB7xx style-drift rules ---

AUTHOR = {
    "name": "testauthor",
    "corpus": {"docs": 10, "words": 20000, "sentences": 1500},
    "rhythm": {
        "sentence_mean": 16.0,
        "sentence_cv": 0.7,
        "segment_cv": 0.7,
        "paragraph_mean_sentences": 4.0,
        "paragraph_cv": 0.8,
        "punchline_ending_share": 0.2,
        "fragment_share": 0.03,
    },
    "punctuation_per_1000_words": {"em_dash": 0.5, "question": 2.0},
    "function_words_per_1000": {"the": 60.0},
    "sentence_openers_per_1000_sentences": {"the": 80.0},
    "connectors_per_1000_sentences": {"but": 50.0, "and": 30.0, "so": 20.0},
    "favorite_words_per_1000": {},
    "favorite_bigrams_per_1000": {},
}


@pytest.fixture
def author_profile(tmp_path):
    path = tmp_path / "testauthor.json"
    path.write_text(json.dumps(AUTHOR), encoding="utf-8")
    return str(path)


def test_nb701_flags_foreign_connector(analyze, author_profile):
    text = "Moreover, the plan worked. The team shipped the release on time."
    issues = analyze(text, config=Config(style=author_profile)).issues
    assert any(i.code == "NB701" and "moreover" in i.message for i in issues)


def test_nb701_allows_author_connectors(analyze, author_profile):
    text = "But the plan worked. The team shipped the release on time."
    issues = analyze(text, config=Config(style=author_profile)).issues
    assert not any(i.code == "NB701" for i in issues)


def test_nb7_inert_without_style(analyze):
    text = "Moreover, the plan worked — twice — and won — again. Did it? Yes? Sure?"
    assert not any(i.code.startswith("NB7") for i in analyze(text).issues)


def test_nb703_flags_punctuation_excess(analyze, author_profile):
    text = (
        "The plan — the old one — worked well. The team — all of them — shipped. "
        "The release went out on time for every customer without a rollback."
    )
    issues = analyze(text, config=Config(style=author_profile)).issues
    assert any(i.code == "NB703" and "em dash" in i.message for i in issues)


def test_nb702_flags_flat_rhythm(analyze, author_profile):
    text = (
        "The team shipped the release on time. The customers noticed the change "
        "quickly. The metrics moved in the right direction. The queue stayed "
        "quiet for a whole month. The billing page needed a small fix. The "
        "support team closed every open ticket."
    )
    issues = analyze(text, config=Config(style=author_profile)).issues
    assert any(i.code == "NB702" for i in issues)


def test_load_profile_unknown_name():
    from nabokov.styleprofile import load_profile

    with pytest.raises(ValueError, match="paulgraham"):
        load_profile("no-such-author")


def test_bundled_profiles_resolve():
    from nabokov.styleprofile import available_profiles, load_profile

    names = available_profiles()
    assert "paulgraham" in names
    assert load_profile("paulgraham")["corpus"]["words"] > 100_000


def test_cli_profile_card(capsys):
    from nabokov.cli import main

    assert main(["--profile-card", "paulgraham"]) == 0
    assert "Voice card — paulgraham" in capsys.readouterr().out
    assert main(["--profile-card", "list"]) == 0
    assert "orwell" in capsys.readouterr().out


def test_cli_unknown_style_errors(tmp_path, capsys):
    from nabokov.cli import main

    f = tmp_path / "t.txt"
    f.write_text("Fine prose here.", encoding="utf-8")
    assert main([str(f), "--style", "nobody"]) == 2
    assert "unknown style profile" in capsys.readouterr().err
