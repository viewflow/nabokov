"""Tests for the stylometric layer: Burrows' Delta and POS-trigram divergence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nabokov.analyzer import load_nlp
from nabokov.source import SourceFile
from nabokov.styleprofile import build_profile, delta_distance, load_profile, pos_divergence

CORPUS = Path(__file__).resolve().parents[1] / ".corpus"

PLAIN = (
    "We shipped the release on Tuesday and the customers noticed the change. "
    "Nobody asked for a refund, and the support queue stayed quiet for the "
    "first time since the beta opened. Next quarter we will hire one more "
    "engineer and fix the billing page before the audit starts. "
) * 8  # ~380 words — above the 300-word scoring floor


def _doc(text):
    return load_nlp()(text)


def test_profile_gains_delta_and_trigram_sections():
    sources = [SourceFile.from_text(PLAIN * 8, f"d{i}.txt") for i in range(2)]
    profile = build_profile(sources, name="t")
    assert profile["delta"]["chunks"] >= 5
    assert profile["delta"]["words"]
    assert len(profile["pos_trigrams"]) > 20  # 3 repeated sentences yield few distinct patterns


def test_delta_none_on_short_text():
    p = load_profile("paulgraham")
    assert delta_distance(p, _doc("Too short to score.")) is None


def test_delta_none_without_section():
    assert delta_distance({"name": "x"}, _doc(PLAIN)) is None


def test_delta_lower_for_own_prose():
    # a profile built FROM this prose should sit closer to it than Graham's
    sources = [SourceFile.from_text(PLAIN * 8, f"d{i}.txt") for i in range(2)]
    own = build_profile(sources, name="own")
    doc = _doc(PLAIN)
    assert delta_distance(own, doc) < delta_distance(load_profile("paulgraham"), doc)


def test_pos_divergence_bounded():
    p = load_profile("paulgraham")
    j = pos_divergence(p, _doc(PLAIN))
    assert 0.0 <= j <= 1.0


def test_nb704_fires_on_far_text(analyze, tmp_path):
    from nabokov.config import Config

    profile = json.loads(
        (Path(__file__).resolve().parents[1] / "src/nabokov/profiles/paulgraham.json").read_text()
    )
    # push every stored mean far away so any prose measures as distant
    profile["delta"]["words"] = {
        w: [mean + 30, 0.5] for w, (mean, _) in profile["delta"]["words"].items()
    }
    path = tmp_path / "far.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    issues = analyze(PLAIN, config=Config(style=str(path))).issues
    assert any(i.code == "NB704" for i in issues)


def test_nb704_silent_close_to_home(analyze, tmp_path):
    sources = [SourceFile.from_text(PLAIN * 8, f"d{i}.txt") for i in range(2)]
    own = build_profile(sources, name="own")
    path = tmp_path / "own.json"
    path.write_text(json.dumps(own), encoding="utf-8")
    from nabokov.config import Config

    issues = analyze(PLAIN, config=Config(style=str(path))).issues
    assert not any(i.code == "NB704" for i in issues)


@pytest.mark.skipif(not (CORPUS / "paulgraham").is_dir(), reason="local corpus not present")
def test_corpus_separation_pg_vs_orwell():
    """Shipped-profile sanity: PG essays sit closer to the PG profile than to
    Orwell's. (The essays are inside the PG profile, which biases the same-
    author distance down a little — fine for a direction check.)"""
    pg = load_profile("paulgraham")
    orwell = load_profile("orwell")
    nlp = load_nlp()
    checked = 0
    for f in sorted((CORPUS / "paulgraham").glob("*.txt"))[:3]:
        doc = nlp(SourceFile.from_path(f).analysis_text)
        d_pg = delta_distance(pg, doc)
        d_or = delta_distance(orwell, doc)
        if d_pg is None or d_or is None:
            continue
        assert d_pg < d_or, f.name
        checked += 1
    assert checked
