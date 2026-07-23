"""AI-likeness score — one composite 0–100 number for before/after reporting.

The idea (a transparent, weighted estimate the editor can print before and
after a rewrite) is adapted from lakshitha-dev/ai-humanizer-skill's score.py
(MIT); the signals and thresholds are nabokov's own calibrated ones.

Honesty contract, printed with every score: this estimates the *statistical*
family of signals only (rhythm, tell density, artifacts, vocabulary range).
It is a gauge of "did the edit move the measurable signals", not a detector
verdict — a low score does not mean a trained classifier will read the text
as human.

Components (weights adapted from the source script; higher = more AI-like):

- **burstiness** (25) — sentence-length CV. Detector literature puts AI text
  near 0.20 and human near 0.60+; risk scales linearly between them.
- **punct rhythm** (10) — punctuation-segment length CV (see
  ``readability.segment_lengths``). LLM prose places a comma or dash every
  clause, so segment lengths cluster; human prose mixes long unpunctuated
  runs with short asides. This separates texts that sentence-level CV ties:
  in the 2026-07 Pangram gap experiment, an LLM rewrite and a
  detector-passing humanized text tied on sentence CV (0.50 vs 0.52) but
  split cleanly here (0.58 vs 0.73). Bands calibrated on that small corpus —
  treat as a coarse signal, hence the low weight.
- **tell density** (40) — span-level NB5xx findings per 100 words, saturating
  at 4/100w. Document-level metric rules and artifact rules are excluded
  here — they have their own components.
- **artifacts** (cap 15) — NB519 fingerprints and NB513 inconsistent curly
  quotes, 6 points each.
- **diversity** (10) — MATTR below NB528's calibrated 0.55/0.45 cutoffs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from .analyzer import AnalysisResult

# Document-level metric rules: their signal is already carried by the
# burstiness/diversity components or is a density verdict, not a span tell.
_DOC_LEVEL = {"NB506", "NB508", "NB509", "NB527", "NB528", "NB529", "NB530"}
_ARTIFACT = {"NB513", "NB519"}

_MIN_WORDS = 25
_MIN_SENTENCES = 3

# burstiness bands from the detector literature; MATTR bands from NB528
_CV_AI, _CV_HUMAN = 0.20, 0.60
_SEG_CV_AI, _SEG_CV_HUMAN = 0.45, 0.75  # punctuation-segment CV, gap-experiment corpus
_MATTR_FLAT, _MATTR_HUMAN = 0.45, 0.55
_TELL_SATURATION = 4.0  # tells per 100 words


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute(result: AnalysisResult) -> dict:
    """Score one analyzed file. Requires the NB5 checks to have been run."""
    stats = result.stats
    if stats.words < _MIN_WORDS or stats.sentences < _MIN_SENTENCES:
        return {
            "score": None,
            "note": (
                f"too short to score ({stats.words} words, {stats.sentences} "
                f"sentences; need {_MIN_WORDS}+/{_MIN_SENTENCES}+) — "
                "statistical signals mean nothing on short text"
            ),
        }

    cv = stats.burstiness
    burst = _clamp((_CV_HUMAN - cv) / (_CV_HUMAN - _CV_AI), 0, 1) * 25

    seg_cv = stats.seg_burstiness
    seg_risk = _clamp((_SEG_CV_HUMAN - seg_cv) / (_SEG_CV_HUMAN - _SEG_CV_AI), 0, 1) * 10

    nb5 = [i for i in result.issues if i.code.startswith("NB5")]
    tells = [i for i in nb5 if i.code not in _DOC_LEVEL | _ARTIFACT]
    density = len(tells) / stats.words * 100
    tell_risk = _clamp(density / _TELL_SATURATION, 0, 1) * 40

    artifact_count = sum(1 for i in nb5 if i.code in _ARTIFACT)
    artifact_risk = min(artifact_count * 6, 15)

    mattr = stats.mattr
    div_risk = _clamp((_MATTR_HUMAN - mattr) / (_MATTR_HUMAN - _MATTR_FLAT), 0, 1) * 10

    score = round(_clamp(burst + seg_risk + tell_risk + artifact_risk + div_risk, 0, 100))
    if score < 25:
        band = "reads human"
    elif score < 50:
        band = "leans human"
    elif score < 75:
        band = "leans AI"
    else:
        band = "reads AI"

    return {
        "score": score,
        "band": band,
        "burstiness": cv,
        "burstiness_risk": round(burst),
        "seg_burstiness": seg_cv,
        "seg_risk": round(seg_risk),
        "tells": len(tells),
        "tell_density": round(density, 1),
        "tell_risk": round(tell_risk),
        "artifacts": artifact_count,
        "artifact_risk": artifact_risk,
        "mattr": mattr,
        "diversity_risk": round(div_risk),
    }


def print_score(result: AnalysisResult, out: TextIO) -> None:
    name = result.source.display_name
    r = compute(result)
    if r["score"] is None:
        out.write(f"{name}: {r['note']}\n")
        return
    out.write(f"{name}: AI-likeness {r['score']}/100 ({r['band']})\n")
    out.write(
        f"  burstiness {r['burstiness']:.2f} -> {r['burstiness_risk']}/25 · "
        f"punct rhythm {r['seg_burstiness']:.2f} -> {r['seg_risk']}/10 · "
        f"tells {r['tells']} ({r['tell_density']}/100w) -> {r['tell_risk']}/40 · "
        f"artifacts {r['artifacts']} -> {r['artifact_risk']}/15 · "
        f"diversity {r['mattr']:.2f} -> {r['diversity_risk']}/10\n"
    )
    out.write("  estimate of statistical signals only — not a detector verdict\n")
