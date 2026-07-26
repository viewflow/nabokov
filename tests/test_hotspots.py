"""Hotspot ranking: which paragraph to fix first."""

from __future__ import annotations

from nabokov.config import Config
from nabokov.hotspots import compute, format_hotspots, payload

AI = Config(extend_select=("NB5",))

# One dense paragraph between two clean ones. The ranking has to find the middle
# one regardless of the order paragraphs appear in.
MIXED = """We shipped the parser on Tuesday. It handles nested lists now.

Moreover, the platform leverages a robust tapestry of very innovative paradigms
that could potentially supercharge a groundbreaking and transformative outcome.

The build takes four minutes. Tests run in twelve seconds.
"""


def test_the_worst_paragraph_ranks_first(analyze):
    spots = compute(analyze(MIXED, config=AI))
    assert spots
    assert spots[0].line == 3
    assert "NB502" in spots[0].counts


def test_clean_paragraphs_are_absent(analyze):
    """A paragraph with no findings is not a hotspot, however long it is."""
    spots = compute(analyze(MIXED, config=AI))
    assert all(spot.issues > 0 for spot in spots)
    assert all(spot.line != 6 for spot in spots)


def test_density_beats_raw_count(analyze):
    """A short dense paragraph outranks a long one holding more total findings.

    Ranking on count alone would just surface the longest paragraph, which tells
    a writer nothing about where the trouble is concentrated. Here the first
    paragraph carries five findings against the second's thirteen, and still
    wins — it is the one that is wrong in every line.
    """
    text = (
        "The platform leverages a robust tapestry of innovative paradigms daily.\n"
        "\n"
        "The parser was shipped on Tuesday and the nested lists were handled "
        "correctly, and the change had been requested by several customers "
        "previously, and the build was kept green throughout the rollout, and "
        "the tests were run automatically, and the release was approved quickly "
        "by the team, and the notes were published immediately, and nobody was "
        "asked to stay late that evening in the office downtown near the river "
        "where the old print shop used to stand before the city rebuilt that "
        "whole block last spring.\n"
    )
    spots = compute(analyze(text, config=AI))
    assert spots[0].line == 1
    assert spots[0].issues < spots[1].issues


def test_a_heading_does_not_outrank_a_paragraph(analyze):
    """The length floor stops a two-word line with one finding taking the top slot."""
    text = "# Very Unique\n\n" + (
        "Moreover, the platform leverages a robust tapestry of very innovative\n"
        "paradigms that could potentially supercharge the outcome.\n"
    )
    spots = compute(analyze(text, config=AI, is_markdown=True))
    assert spots[0].line == 3


def test_limit_is_respected(analyze):
    assert len(compute(analyze(MIXED, config=AI), limit=1)) == 1


def test_severity_weighting_counts(analyze):
    """Weight exceeds the raw finding count once any warning is present."""
    spot = compute(analyze(MIXED, config=AI))[0]
    assert spot.weight > spot.issues


def test_payload_is_json_ready(analyze):
    import json

    data = payload(analyze(MIXED, config=AI))
    assert data and json.dumps(data)
    assert set(data[0]) == {
        "line",
        "end_line",
        "words",
        "issues",
        "weight",
        "density",
        "codes",
        "preview",
    }


def test_format_names_the_file_and_the_codes(analyze):
    text = format_hotspots([analyze(MIXED, config=AI)])
    assert "Hotspots" in text
    assert "NB502" in text
    assert "test.txt" in text


def test_format_is_empty_for_clean_text(analyze):
    assert format_hotspots([analyze("The build is green. Tests pass.\n")]) == ""


def test_hotspots_off_by_default(analyze):
    """The flag is opt-in; the JSON payload stays unchanged without it."""
    from nabokov.reporters.json_reporter import result_payload

    assert "hotspots" not in result_payload(analyze(MIXED, config=AI))


def test_json_reporter_includes_hotspots_when_asked(analyze):
    from nabokov.reporters.json_reporter import result_payload

    body = result_payload(analyze(MIXED, config=AI), hotspots=2)
    assert len(body["hotspots"]) <= 2
    assert body["hotspots"][0]["line"] == 3
