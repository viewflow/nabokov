"""Author style profile — a measurable voice signature extracted from a corpus.

Classic stylometry (Mosteller-Wallace, Burrows' Delta) identifies authors by
the statistics they can't consciously control: function-word rates,
punctuation habits, rhythm. This module runs that machinery in reverse — not
to identify an author but to *record* their signature, so an editor (human
or LLM) can pull a rewrite back toward the author's own distribution instead
of drifting into model idiolect.

A profile is honest data, not a persona: favorite words, connectors, and
rhythm norms the author demonstrably has. It never invents facts, biography,
or opinions — reusing an author's *words* is the opposite of fabricating
their *claims*.

Corpus size matters: function-word rates stabilize from roughly 5-10k words.
``build_profile`` records the corpus size so consumers can judge how much to
trust the numbers.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

from .readability import burstiness, segment_lengths, sentence_lengths

if TYPE_CHECKING:
    from .source import SourceFile

# Sentence-initial discourse markers worth tracking individually: which of
# these an author leans on (and how hard) is a strong, stable tell.
CONNECTORS = (
    "and", "but", "so", "because", "or", "yet", "now", "then", "still",
    "instead", "indeed", "actually", "anyway", "however", "moreover",
    "meanwhile", "obviously", "surprisingly", "notice", "consider",
    "in fact", "of course", "for example", "at first", "in practice",
)  # fmt: skip

_CONTENT_POS = ("NOUN", "VERB", "ADJ", "ADV")

# Burrows' Delta settings: block size for variance estimation, how many
# most-frequent function words enter the measure, and the minimum blocks
# for a standard deviation worth trusting.
_DELTA_CHUNK = 1000
_DELTA_WORDS = 100
_MIN_DELTA_CHUNKS = 5
_POS_TRIGRAMS_STORED = 150
_PUNCT_MARKS = {
    "em_dash": "—",
    "en_dash": "–",  # noqa: RUF001 - the en dash is the mark being counted
    "semicolon": ";",
    "colon": ":",
    "paren_open": "(",
    "question": "?",
    "exclamation": "!",
    "ellipsis": "…",
    "comma": ",",
}


def available_profiles() -> list[str]:
    """Names of the profiles bundled with the package."""
    from importlib import resources

    return sorted(
        p.name.removesuffix(".json")
        for p in resources.files("nabokov.profiles").iterdir()
        if p.name.endswith(".json")
    )


@lru_cache(maxsize=8)
def load_profile(spec: str) -> dict:
    """Load a profile by bundled name ("paulgraham") or filesystem path.

    Raises ValueError with the list of bundled names when the spec resolves
    to nothing.
    """
    path = Path(spec)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    from importlib import resources

    bundled = resources.files("nabokov.profiles").joinpath(f"{spec}.json")
    if bundled.is_file():
        return json.loads(bundled.read_text(encoding="utf-8"))
    raise ValueError(
        f"unknown style profile {spec!r} — pass a .json path or one of: "
        + ", ".join(available_profiles())
    )


def _cv(values: list[int | float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return statistics.pstdev(values) / mean if mean else 0.0


def build_profile(sources: list[SourceFile], name: str) -> dict:
    """Extract the signature from a corpus of one author's texts."""
    from .analyzer import load_nlp
    from .checks.base import paragraph_ranges

    nlp = load_nlp()

    n_words = 0
    n_sentences = 0
    function_counts: Counter[str] = Counter()
    content_counts: Counter[str] = Counter()
    content_docfreq: Counter[str] = Counter()
    bigram_counts: Counter[str] = Counter()
    bigram_docfreq: Counter[str] = Counter()
    opener_counts: Counter[str] = Counter()
    connector_counts: Counter[str] = Counter()
    punct_counts: Counter[str] = Counter()
    all_sentence_lengths: list[int] = []
    all_segment_lengths: list[int] = []
    paragraph_sentences: list[int] = []
    punchline_endings = 0
    fragments = 0
    # Burrows' Delta needs per-word variance measured over comparable-size
    # blocks — natural docs vary from 300 to 13k words, so we chunk the
    # concatenated corpus instead (chunks may span doc boundaries).
    delta_chunks: list[dict[str, float]] = []
    chunk: Counter[str] = Counter()
    chunk_n = 0
    pos_trigrams: Counter[str] = Counter()

    for source in sources:
        doc = nlp(source.analysis_text)
        doc_content: set[str] = set()
        doc_bigrams: set[str] = set()

        words = [t for t in doc if not (t.is_punct or t.is_space)]
        n_words += len(words)
        for mark_name, mark in _PUNCT_MARKS.items():
            punct_counts[mark_name] += source.analysis_text.count(mark)

        for t in doc:
            if t.is_punct or t.is_space:
                continue
            chunk_n += 1
            if t.is_alpha and t.is_stop:
                function_counts[t.lower_] += 1
                chunk[t.lower_] += 1
            elif t.is_alpha and t.pos_ in _CONTENT_POS:
                lemma = t.lemma_.lower()
                content_counts[lemma] += 1
                doc_content.add(lemma)
            if chunk_n == _DELTA_CHUNK:
                delta_chunks.append(dict(chunk))
                chunk.clear()
                chunk_n = 0
        for a, b in pairwise(doc):
            if a.is_alpha and b.is_alpha and not (a.is_stop and b.is_stop):
                bigram = f"{a.lower_} {b.lower_}"
                bigram_counts[bigram] += 1
                doc_bigrams.add(bigram)

        for sent in doc.sents:
            tokens = [t for t in sent if not (t.is_punct or t.is_space)]
            if not tokens:
                continue
            pos = [t.pos_ for t in tokens]
            for i in range(len(pos) - 2):
                pos_trigrams[" ".join(pos[i : i + 3])] += 1
            n_sentences += 1
            opener_counts[tokens[0].lower_] += 1
            two = " ".join(t.lower_ for t in tokens[:2])
            for c in CONNECTORS:
                if (tokens[0].lower_ == c) or (two == c):
                    connector_counts[c] += 1
                    break
            if sent.root.pos_ not in ("VERB", "AUX") and sent.text.rstrip().endswith(
                (".", "!", "?", "…")
            ):
                fragments += 1

        all_sentence_lengths.extend(sentence_lengths(doc))
        all_segment_lengths.extend(segment_lengths(doc))

        for start, end in paragraph_ranges(doc.text):
            span = doc.char_span(start, end, alignment_mode="expand")
            if span is None:
                continue
            sents = [
                n for s in span.sents if (n := sum(1 for t in s if not (t.is_punct or t.is_space)))
            ]
            if not sents:
                continue
            paragraph_sentences.append(len(sents))
            if sents[-1] <= 8:
                punchline_endings += 1

        for t in doc_content:
            content_docfreq[t] += 1
        for b in doc_bigrams:
            bigram_docfreq[b] += 1

    # trailing partial block: keep if at least half a chunk, scaled to rate
    if chunk_n >= _DELTA_CHUNK // 2:
        delta_chunks.append({w: c * _DELTA_CHUNK / chunk_n for w, c in chunk.items()})

    docs = len(sources)
    per_1000 = 1000 / n_words if n_words else 0.0
    min_df = max(2, docs // 4)  # a signature repeats across texts; topic words don't

    def rated(counter: Counter, top: int, docfreq: Counter | None = None) -> dict[str, float]:
        items = counter.most_common()
        if docfreq is not None:
            items = [(k, v) for k, v in items if docfreq[k] >= min_df]
        return {k: round(v * per_1000, 2) for k, v in items[:top]}

    profile: dict = {
        "name": name,
        "corpus": {"docs": docs, "words": n_words, "sentences": n_sentences},
        "rhythm": {
            "sentence_mean": round(
                sum(all_sentence_lengths) / max(1, len(all_sentence_lengths)), 1
            ),
            "sentence_cv": round(burstiness(all_sentence_lengths), 2),
            "segment_cv": round(burstiness(all_segment_lengths), 2),
            "paragraph_mean_sentences": round(
                sum(paragraph_sentences) / max(1, len(paragraph_sentences)), 1
            ),
            "paragraph_cv": round(_cv(paragraph_sentences), 2),
            "punchline_ending_share": round(
                punchline_endings / max(1, len(paragraph_sentences)), 3
            ),
            "fragment_share": round(fragments / max(1, n_sentences), 3),
        },
        "punctuation_per_1000_words": {
            k: round(v * per_1000, 2) for k, v in sorted(punct_counts.items())
        },
        "function_words_per_1000": rated(function_counts, 60),
        "sentence_openers_per_1000_sentences": {
            k: round(v * 1000 / max(1, n_sentences), 1) for k, v in opener_counts.most_common(15)
        },
        "connectors_per_1000_sentences": {
            k: round(v * 1000 / max(1, n_sentences), 1)
            for k, v in connector_counts.most_common()
            if v
        },
        "favorite_words_per_1000": rated(content_counts, 40, content_docfreq),
        "favorite_bigrams_per_1000": rated(bigram_counts, 25, bigram_docfreq),
    }

    if len(delta_chunks) >= _MIN_DELTA_CHUNKS:
        stats: dict[str, list[float]] = {}
        for w, _ in function_counts.most_common(_DELTA_WORDS):
            vals = [c.get(w, 0.0) for c in delta_chunks]
            mean = sum(vals) / len(vals)
            std = statistics.pstdev(vals)
            if std > 0:
                stats[w] = [round(mean, 3), round(std, 3)]
        profile["delta"] = {
            "chunk_words": _DELTA_CHUNK,
            "chunks": len(delta_chunks),
            "words": stats,
        }

    total_tri = sum(pos_trigrams.values())
    if total_tri:
        profile["pos_trigrams"] = {
            tri: round(count / total_tri, 5)
            for tri, count in pos_trigrams.most_common(_POS_TRIGRAMS_STORED)
        }

    return profile


# Delta on a short text is noise: rare function words legitimately miss.
MIN_SCORED_WORDS = 300


def delta_distance(profile: dict, doc) -> float | None:
    """Burrows' Delta between a spaCy doc and the profile's author.

    The mean absolute z-score of the document's function-word rates against
    the author's per-1000-word means and deviations. Lower = closer to the
    author. None when the profile predates the delta section or the text is
    too short to score.
    """
    d = profile.get("delta")
    if not d:
        return None
    n_words = sum(1 for t in doc if not (t.is_punct or t.is_space))
    if n_words < MIN_SCORED_WORDS:
        return None
    counts: Counter[str] = Counter(t.lower_ for t in doc if t.is_alpha and t.is_stop)
    zs = [
        abs((counts.get(w, 0) * 1000 / n_words - mean) / std)
        for w, (mean, std) in d["words"].items()
    ]
    return sum(zs) / len(zs) if zs else None


def pos_divergence(profile: dict, doc) -> float | None:
    """Jensen-Shannon divergence (base 2, 0..1) between POS-trigram
    distributions of the doc and the profile. Syntax only — topic-blind."""
    import math

    stored = profile.get("pos_trigrams")
    if not stored:
        return None
    n_words = sum(1 for t in doc if not (t.is_punct or t.is_space))
    if n_words < MIN_SCORED_WORDS:
        return None
    counts: Counter[str] = Counter()
    for sent in doc.sents:
        pos = [t.pos_ for t in sent if not (t.is_punct or t.is_space)]
        for i in range(len(pos) - 2):
            counts[" ".join(pos[i : i + 3])] += 1
    total = sum(counts.values())
    if not total:
        return None
    # Renormalize both over the union of keys; the stored top-150 covers the
    # bulk of the author's mass, so the truncation error is small and equal
    # in direction for every comparison.
    keys = set(stored) | set(counts)
    p_sum = sum(stored.get(k, 0.0) for k in keys)
    q_sum = total
    js = 0.0
    for k in keys:
        p = stored.get(k, 0.0) / p_sum if p_sum else 0.0
        q = counts.get(k, 0) / q_sum
        m = (p + q) / 2
        if p:
            js += 0.5 * p * math.log2(p / m)
        if q:
            js += 0.5 * q * math.log2(q / m)
    return js


def render_card(profile: dict) -> str:
    """The profile as a compact voice card — for humans and for LLM editors."""
    c, r = profile["corpus"], profile["rhythm"]
    p = profile["punctuation_per_1000_words"]

    def top(d: dict, n: int) -> str:
        return ", ".join(f"{k} ({v})" for k, v in list(d.items())[:n])

    lines = [
        f"# Voice card — {profile['name']}",
        f"Corpus: {c['docs']} texts, {c['words']:,} words, {c['sentences']:,} sentences.",
        "",
        f"**Rhythm.** Average sentence {r['sentence_mean']} words, length variety "
        f"{r['sentence_cv']} (sentence CV), punctuation looseness {r['segment_cv']} "
        f"(segment CV). Paragraphs average {r['paragraph_mean_sentences']} sentences "
        f"(CV {r['paragraph_cv']})"
        + (
            " — implausibly high; the source texts likely lack blank-line paragraph "
            "breaks, so treat the paragraph numbers as unreliable"
            if r["paragraph_mean_sentences"] > 25
            else ""
        )
        + f"; {r['punchline_ending_share']:.0%} end on a short "
        f"beat; {r['fragment_share']:.1%} of sentences are verbless fragments.",
        "",
        "**Punctuation per 1000 words.** "
        + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in p.items() if v > 0)
        + ".",
        "",
        f"**Sentence-initial connectors (per 1000 sentences).** "
        f"{top(profile['connectors_per_1000_sentences'], 12)}.",
        "",
        f"**Common sentence openers (per 1000 sentences).** "
        f"{top(profile['sentence_openers_per_1000_sentences'], 12)}.",
        "",
        f"**Favorite words (per 1000 words, recurring across texts).** "
        f"{top(profile['favorite_words_per_1000'], 25)}.",
        "",
        f"**Favorite pairs.** {top(profile['favorite_bigrams_per_1000'], 15)}.",
        "",
        "Use this card to keep edits inside the author's distribution: prefer these "
        "connectors and words over generic ones, match the rhythm numbers, and never "
        "invent facts or opinions on the author's behalf.",
    ]
    if "delta" in profile:
        d = profile["delta"]
        lines.insert(
            2,
            f"Stylometry: Burrows' Delta baseline over {d['chunks']} blocks of "
            f"{d['chunk_words']} words; POS-trigram signature stored (NB704 active).",
        )
    if c["words"] < 10_000:
        lines.insert(2, "")
        lines.insert(
            3,
            f"⚠ Small corpus ({c['words']:,} words) — rates are noisy below ~10k words.",
        )
    return "\n".join(lines) + "\n"
