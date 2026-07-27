# AI-text detection: what the evidence supports

Research date: 2026-07-27. Scope: how AI-generated text is detected, how reliable
each method is, and the one question that decides what nabokov can do — **does a
human-edited AI draft stay detectable?**

**Method caveat, and it is a large one.** This came from a fan-out research
workflow that hit session limits twice and had to be resumed. Its verification
panels failed entirely on the first run, and on the second run the *synthesis*
step failed, so the report below was assembled by hand from the raw claim
buckets. What survived is:

- **11 claims confirmed 3-0** by adversarial verification (2-0 for one),
- **4 claims refuted**, listed here because a killed claim is a finding,
- **10 claims that never got verified** — flagged inline, never load-bearing.

Every quantitative figure carries its source and its status. Where a number is
vendor self-reported, it says so.

---

## The bottom line for nabokov

Three things are now established well enough to act on:

1. **Pangram is genuinely hard to beat, and that is measured independently** —
   not vendor marketing.
2. **The two evasion routes people reach for first do not work on it.** Word and
   synonym swaps cost it ~3 points. Commercial "humanizer" rewriting costs it
   almost nothing, while it destroys GPTZero.
3. **Nobody has published whether it catches a human-edited draft.** That is the
   single biggest gap in the literature, and it is exactly nabokov's use case.

So "beat Pangram by editing" is not a solved problem that nabokov is failing at.
It is an unmeasured one, and the measurements that exist point the wrong way.

---

## 1. Pangram, from vendor-independent sources

**NBER Working Paper 34223** (Jabarian & Imas, Sept 2025) audited 1,992 matched
human/AI passages across six genres and four frontier models (GPT-4.1, Claude
Opus 4, Claude Sonnet 4, Gemini 2.0 Flash). The authors declare no financial or
personal conflicts. *(confirmed 3-0)*

| Genre | Pangram FPR on human text |
|---|---|
| Blog, novel, resume | 0.0000 |
| News | 0.0008 |
| Amazon review | 0.0050 |
| Restaurant review | 0.0075 |

AUROC was 1.0000 for the vast majority of medium-to-long categories and never
below 0.9979 even on short passages. Originality.ai scored high but lower
across the board; GPTZero lower still (~0.96 on short passages); a RoBERTa
baseline performed at or below chance.

**The RAID shared task** (arXiv 2501.08913) scored detectors on a hidden test
set the organizers controlled. Pangram reached **99.3% TPR at a fixed 5% FPR**
across 8 domains and 11 LLMs, and **97.7%** with 11 adversarial attacks applied.
*(confirmed 3-0)*

Three labels that matter on that number, all from the verified claim itself:

- It is **not vendor self-report** — labels and scoring were the organizers'.
- It is **not a blind API probe** either. Pangram tuned on the task's training
  set, mining it for high-error examples and retraining to convergence.
- The metric is TPR at a threshold searched per detector *and per domain* to hit
  exactly 5% FPR, so it says nothing about false positives at the shipping
  default threshold.

The organizers also warn that the near-ceiling results are an **in-distribution
artifact**. Every domain, generator and attack was disclosed in advance. On
unseen models, detectors still generalize poorly. *(confirmed 3-0)*

### Pangram's own numbers, clearly labelled

Pangram's technical report (arXiv 2402.14873) claims 99% accuracy on a
1,976-document benchmark. It also reports zero false positives on TOEFL essays
and on ELLIPSE (3,907 essays), and 0.09% on ICNALE (5,600 essays) — its rebuttal
to the non-native-writer bias finding. **This is vendor self-reported**: Emi and Spero
are Pangram Labs, and the benchmark and its AI-side generations were built by
the vendor. The report's headline "over 38 times lower error rates" is never
pinned to a named competitor or a single metric. *(unverified, 3 votes)*

---

## 2. What does not work

### Word and synonym swaps

The most important single table for nabokov. In the RAID shared task, averaged
over all 26 submissions, the hardest attacks were homoglyph (49.2% TPR),
paraphrase (60.6%) and synonym swap (61.3%). Those averages are dragged down by
systems scoring near 3%. **Against the best detectors the cost is small:**
*(confirmed 3-0)*

| Attack | Pangram | Leidos v1.0.2 |
|---|---|---|
| Baseline | ~99.3% | 99.4% |
| Synonym swap | **96.2%** | 98.6% |
| Paraphrase | **91.6%** | 92.3% |

Automated synonym substitution costs the best detector about 3 points; automated
paraphrase about 8. Cosmetic attacks — whitespace, case swap, zero-width space,
alternative spelling — are neutralized by simple text normalization.

The same edits *wreck* statistical detectors: synonym swap costs Binoculars 36.1
points and GLTR 31.4, while costing GPTZero only 5.5 and **improving**
Originality by 11.5 and RoBERTa-L by 22.7. *(confirmed 3-0)*

> **This corrects a claim in the skills.** "Word swaps move neither family" is
> wrong as stated — they move statistical detectors enormously, in both
> directions. It is right about the case that matters here: they barely move
> Pangram.

### Commercial humanizers

Running every AI passage through StealthGPT's humanizer endpoint barely degraded
Pangram: FNR 0.0000–0.0500 across all genre × model cells, worst case 0.0500.
The same rewrite **largely destroyed GPTZero** (FNR ~0.25–0.77, e.g. 0.7730 on
Claude Opus 4 novels) and degraded Originality.ai to ~0.02–0.21.
*(confirmed 3-0)*

Humanizer evasion is detector-specific, not universal. It buys nothing against
the detector in question.

---

## 3. What has evidence of working — and its caveats

**Human editing roughly halves detection.** An independent multi-institution test
of 14 detectors found 42% accuracy on human-edited AI text versus 74% on
unmodified AI text. Machine paraphrasing dropped overall accuracy to 26%.
*(unverified, 3 votes; 2023 tool versions and ChatGPT-era text — the weakest
generalization in this report)*

**But the amount of editing is the whole story.** From the first workflow run,
Beemo (arXiv 2411.04032, NAACL 2025) reports Binoculars falling from 83.90 AUROC
on human-vs-machine to **61.24** on human-vs-expert-edited. The paper's own
caveat: its expert editors changed **~70% of tokens**, far above the study's own
20–40% guideline. It does not show that word-level edits move scores; it shows
that rewriting most of a draft does. *(unverified — extracted before the
verification panels failed)*

**And who edits matters.** Beemo Table 4: Binoculars reads 79.90 AUROC on
Llama-3.1-70B-edited text and 78.15 on GPT-4o-edited, against 61.24 on
expert-human-edited. A model polishing a model's draft leaves the machine signal
largely intact. *(unverified — same caveat)*

This is the finding the cadence pass in `nabokov-editor` now acts on.

---

## 4. The gap that decides everything

**No published study tests whether Pangram catches a human-edited AI draft.**

- The NBER audit tested only pure-human vs pure-AI and machine-humanized AI —
  **no human-edited drafts**, and no non-native-speaker subgroup analysis.
  *(confirmed 3-0)*
- Pangram's own report contains **no evaluation** of paraphrasing attacks,
  commercial humanizers, or human-edited/hybrid drafts. It tests pure-human vs
  pure-AI only. *(unverified, 3 votes)*
- The RAID shared-task organizers named commercial humanizers and evasion
  prompting as untested gaps in their own evaluation. *(this claim was refuted
  1-2 — the verifiers did not sustain it, so treat the gap as unconfirmed rather
  than as a first-party admission)*

The Springer and Beemo numbers above are the closest available evidence, and
neither tested Pangram.

**So the honest position is: unmeasured, with the surrounding evidence
unfavourable.** The 2026-07 gap experiment recorded in project memory is one
data point on it — a nabokov-copywriter rework that every static signal called
human still read 100% AI to Pangram.

---

## 5. Claims that did not survive verification

Recorded because a killed claim is a finding, and because three of these are
attractive and wrong.

- **"99%+ accuracies are reproducible only at high FPR; most detectors collapse
  at low FPR"** — refuted 0-3.
- **"No current detector can identify at which stage of writing an LLM was
  involved"** — refuted 0-3. Do not cite the stage-detection framing.
- **"Turnitin fell to 45.7%, worse than a coin flip, on obfuscated text"** —
  refuted 0-2.
- **"The RAID organizers admit humanizers are an untested gap"** — refuted 1-2.

## 6. Context worth keeping, not load-bearing here

RAID's authors say their results corroborate the finding that detectors are
biased against non-native English writers. They declare the false-positive
problem unsolved and oppose punitive use of detectors outright. At naive default
thresholds, open-source detectors show dangerously high FPR on human text (GLTR
100% at τ=0.25, LLMDet 97.9%). The four commercial detectors tested were
calibrated below 1.7%. *(confirmed 3-0)*

Generation settings alone break detectors, with no evasion attempted. A
repetition penalty costs up to 32 accuracy points. Switching
generator, decoding or penalty can drive error rates above 95% — GPTZero from
98.8 to 34.6, Binoculars from 99.9 to 0.6. *(confirmed 3-0)*

---

## What this changes in the tool

1. **The skills' "word swaps move neither" line needs the qualifier** — true of
   Pangram, false of statistical detectors.
2. **The cadence pass is the right architecture** and is already shipped: LLM
   diagnoses, human rewrites. The evidence says LLM-rewrites leaves the signal.
3. **Do not build a humanizer mode.** Measured not to work on the target, and it
   costs accuracy.
4. **The missing instrument is a labelled benchmark**, not another rule. Until
   there are Pangram-labelled pairs in `.corpus/`, no rule aimed at this can be
   shown to work.

## Sources

Vendor-independent:

- [NBER WP 34223](https://www.nber.org/papers/w34223)
- [RAID benchmark, ACL 2024](https://arxiv.org/abs/2405.07940)
- [RAID shared task](https://arxiv.org/pdf/2501.08913)
- [Beemo, NAACL 2025](https://arxiv.org/abs/2411.04032)
- [Weber-Wulff et al., Springer](https://link.springer.com/article/10.1007/s40979-023-00146-z)
- [Liang et al., non-native bias](https://arxiv.org/abs/2304.02819)
- [SynthID-Text, Nature](https://www.nature.com/articles/s41586-024-08025-4)

Vendor self-reported:

- [Pangram technical report](https://arxiv.org/abs/2402.14873)

Institutional:

- [Vanderbilt disabling Turnitin's detector](https://www.vanderbilt.edu/brightspace/2023/08/16/guidance-on-ai-detection-and-why-were-disabling-turnitins-ai-detector/)
- [OpenAI retiring its classifier](https://openai.com/index/new-ai-classifier-for-indicating-ai-written-text/)
