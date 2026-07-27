# Text quality measurement: what the essay-scoring literature supports

Research date: 2026-07-27. Scope: which features from the automated essay
scoring (AES) and writing-assessment literature predict human quality
judgments, which of those a spaCy-based linter can compute, and which are
worth building.

**Method caveat.** Five parallel searchers, one per angle, no adversarial
verification step. That was a deliberate cost decision, so every claim here
carries the confidence its searcher assigned rather than a verification
verdict. Two consequences worth knowing:

- The shared WebSearch budget ran out early. Most retrieval fell back to the
  ERIC, OpenAlex, and Crossref APIs and to guessing URLs. Coverage of ACL
  Anthology and ETS Research Reports is thinner than a full search would give,
  and Perelman's construct-validity critiques are missing entirely.
- One searcher caught a WebFetch PDF summary **fabricating** results: an
  invented "84% accuracy on a WSJ corpus of 2000 articles" for Barzilay &
  Lapata. It discarded the summary and read the PDF pages directly, which is
  where the real numbers below come from. Treat any figure in this file that
  is not marked as directly read with corresponding suspicion.

Where a number came from an abstract rather than a full text, it says so.
Where a sign or direction was inferred rather than quoted, it says that too.

---

## The bottom line for nabokov

**Most of this literature does not transfer to what nabokov does, and the
reason is the same in every case: it measures the wrong end of the scale.**

Every validated correlation below comes from student or L2 exam essays, where
the variance being explained is basic writing competence. nabokov edits prose
by adults who already write fluently. The features that separate a weak essay
from a middling one are, for that population, range-restricted to the point of
uselessness. No study anyone found tests whether these relationships hold,
flatten, or reverse once competence stops being the bottleneck. That gap is
the most important finding here, and it disqualifies more candidate features
than any other consideration.

Three things survive that filter. All three now ship as `--stats` metrics,
alongside a fourth from Tier 2 — and **no new rule**, because the one rule
worth trying was measured against this repo's prose and killed:

1. **Adjacent-paragraph lexical overlap** is the highest-correlating feature
   nabokov could newly compute from the parse alone (r=.40 with quality, r=.42
   with coherence). It needs nothing but a lemma set per paragraph, and it
   measures the exact failure the editor skill currently says no linter can
   catch. Several e-rater features correlate higher — usage r=.64, vocabulary
   r=.58, grammar r=.56 — but every one of them needs a reference corpus or a
   grammar checker, and organization (r=.46) is a length proxy by the section
   below. Style, at r=.50, is roughly what NB302, NB528 and NB201 already do.
2. **Dependency distance** predicts rated quality independently of the
   character-counting readability index, costs one pass over the parse, and
   has ablation evidence behind it.
3. **The Heylighen–Dewaele formality score** is a published, validated
   combination of precisely the part-of-speech ratios nabokov already computes
   ad hoc.

And one finding reframes everything else.

---

## The length confound

Start here, because it explains why most AES features are worth less than
their correlations suggest.

- Word count **alone** explained 39% of the score variance on 2,820 SAT essays
  (R²=.39). Reaching a second page added 1.5%; first-person usage added 1.1%.
  — Kobrin, Deng & Shaw (2007), *Journal of Applied Testing Technology* 8(1).
- Attali & Burstein state it plainly: "the simplest form of automated scoring
  which considers only essay length could yield agreement rates that are almost
  as good as human rates." They treat this as the reason human-machine
  agreement is an insufficient validity criterion.
- e-rater's two most heavily weighted features — Organization and Development,
  together about 45% of total model weight — correlated with word count so
  strongly that a later ETS factor analysis (N=30,600 essays) **replaced them
  with raw text length**. — Quinlan, Higgins & Wolff (2009), ETS RR-09-01,
  citing Attali & Powers (2008).
- Human raters themselves correlate r=.63–.75 with token count.
  — Kundu & Barbosa (2024), arXiv:2409.13120.

**Confidence: high.** Read from primary sources.

So when a paper reports that some discourse feature predicts quality, the
prior should be that it is partly measuring length. For nabokov this is not a
feature to copy. It is a reason to discount most of what follows.

A related caution from the same corner: ETS's own researchers found e-rater's
named features collapse into just **three** latent factors (conventions,
word usage, and discourse fluency) with **no factor corresponding to content
or genuine organization** at all. Their recommendation was to go build those.
Deane (2013) argues AES correlates with human scores not because it measures
argument quality but because fluency of low-level text production proxies for
the cognitive resources left over for higher-order composition. That is a
real construct, but a different one from what the rubric claims to assess.

---

## Cohesion: the local/global split

This is the richest result in the research, and the naive reading of it is
wrong in a way that matters.

### The observational finding

In the TAACO validation study (Crossley, Kyle & McNamara 2016, *Behavior
Research Methods*; N=313 persuasive essays, 8 expert raters), **local**
cohesion indices correlated **negatively** with expert quality ratings:

| Local index (adjacent sentences) | r with quality |
|---|---|
| All-lemma TTR | −.29 |
| Bigram TTR | −.17 |
| Content-word TTR | −.17 |
| Pronoun-to-noun ratio | −.15 |
| Verb-synonym sentence overlap | −.11 |

While **global** indices, overlap between adjacent *paragraphs*, were positive
and much stronger:

| Global index (adjacent paragraphs) | r with quality | r with coherence |
|---|---|---|
| All-lemma overlap | **.40** | .37 |
| Noun-lemma overlap | .37 | **.42** |
| Argument-lemma overlap | .37 | — |
| Verb overlap | .35 | — |
| Adverb overlap | .33 | .40 |
| Adjective overlap | .31 | — |

The paper's own conclusion: "coherence for expert raters is a property of
global cohesion and not of local cohesion." A four-variable regression
explained 26% of quality variance, with the global indices entering positive
and the local ones negative.

**Confidence: high.** Tables 3–6 fetched and read directly.

### Why the naive reading is wrong

The tempting conclusion ("repetition between sentences is bad, so strip it")
does not follow, and a companion study shows why.

Crossley & McNamara (2016, *Journal of Writing Research*) **manipulated**
cohesion experimentally: experts inserted local and global ties into real
student essays (repeating key words, disambiguating bare anaphors like "this"
into "this showering"), in a 2×2×2 design over 280 essays with 12 raters.
Adding cohesion **raised** quality (M=2.92 vs 2.69, F(1,34)=14.30, p<.001,
η²p=.296) and coherence (M=3.87 vs 3.59, η²p=.33). Under manipulation, local
lemma overlap turned **positive** (r=.123, p<.05 for coherence).

So the observational negative is a confound, not a causal law. Writers who
lean on local repetition tend to be weaker writers; that is not the same as
local repetition making prose weaker. What holds up under both designs is the
**ranking**: global paragraph-level overlap beats local sentence-level overlap
as a quality signal, in the observational study (.40 vs −.29) and in the
experiment (.489 vs .115).

**This distinction is load-bearing.** A rule that punished sentence-level
repetition would be reading a confounded correlation as a causal one.

The mechanism the field offers, the "reverse cohesion effect", is that
explicit local ties help low-knowledge readers bridge gaps, while for
high-knowledge readers their absence prompts useful inference, and dense
repetition instead reads as unsophisticated. Plausible, cited by both papers,
but the primary source (O'Reilly & McNamara 2007) was not fetched.
**Confidence: medium.**

### Two more cohesion notes

**Task type flips the sign.** For source-based (integrated) writing, local
cohesion indices correlate *positively* with quality; for independent essays
they correlate negatively (Guo, Crossley & McNamara 2013, reported inside the
TAACO paper). **Confidence: medium**, read secondhand.

**Connective density is a dead end.** TAACO reports that connective indices
"demonstrated negligible or negative correlations with essay quality and essay
coherence," and no connective index survived either regression. This is worth
recording as a *negative* result: it argues against ever building a rule that
pushes writers to add transitions, and it is consistent with what NB505 and
NB531 already assume, that a bolted-on connector is a label, not a bridge.

### Entity grid

Barzilay & Lapata (2008), *Computational Linguistics* 34(1) — read directly
after the fabricated summary was caught. Models coherence as the distribution
of entity transitions (subject/object/other/absent) across adjacent sentences.
On sentence-ordering discrimination: 87.2% and 90.4% on two corpora vs 50%
chance, beating an LSA baseline (81.0%/87.3%). On rating summary coherence:
83.8% vs LSA's near-chance 52.5%.

The implementation-relevant detail: **a coreference-free model lost only about
6 points** (81.4%/86.0%), and on the summary task a string-identity model with
no coreference resolver was the *best* performer. Most of the signal is
recoverable from dependency-parsed subject/object roles plus lemma identity —
which is exactly what spaCy gives.

**Confidence: high**, but note the validated task is sentence-ordering
discrimination, not quality scoring. Nobody showed entity-grid coherence
predicts human quality ratings on real prose.

---

## Syntactic complexity: mostly a dead end

The direction-of-effect check came back confirming Biber, and then
complicating him.

**Subordination is a conversational feature, not an academic one.** Biber,
Gray & Poonpon (2011), *TESOL Quarterly* 45(1): "most clausal subordination
measures are actually more common in conversation than academic writing. In
contrast, fundamentally different kinds of grammatical complexity are common
in academic writing: complex noun phrase constituents (rather than clause
constituents) and complex phrases (rather than clauses)." **Confidence: high**
for the claim; abstract only, so no magnitudes.

**But the developmental story does not survive contact with score data.**
Biber, Gray & Staples (2016), *Applied Linguistics* 37(5), on a large TOEFL
corpus: "hypothesized developmental progressions in the use of these
grammatical complexity features were generally **not confirmed** by score-level
differences." Only a multidimensional co-occurrence model predicted score
bands. In a related analysis, only 2 of ~28 Biber-tagger features
significantly tracked holistic score.

**And the effect ceiling is low.** Kyle & Crossley (2017) put traditional
structural syntactic-complexity indices at **R²=.058**, under 6% of variance
in writing quality. Usage-based frequency and association indices more than
doubled that, to R²=.142. **Confidence: high**, from the abstract.

Hwang (2025), on 6,566 timed essays, adds a wrinkle: raw subordination *does*
increase with L2 proficiency, but its composition shifts toward nonfinite
forms — consistent with Biber's finite→nonfinite→phrasal sequence without
supporting a simple "less subordination is better" reading.

Norris & Ortega (2009) and Deng, Lei & Liu (2021) both argue the field's
measures are inconsistently operationalized and that single global ratios are
uninterpretable: two 12-word T-units, one elaborated by an adjective and a
prepositional phrase and the other by a full *because*-clause, score
identically on mean length of T-unit despite being structurally unrelated.

**Verdict for nabokov: do not build L2SCA.** Sub-6% variance explained, T-unit
segmentation that likely needs constituency parsing spaCy does not provide,
progressions unconfirmed against actual scores, and the field's own
methodologists warning the measures are not portable.

**The one survivor** is noun-phrase modifier density (modifiers per noun
phrase). Crossley & McNamara (2014): r=.213 (p=.023) with quality, and
significant growth across a semester (η²p=.122). Guo, Crossley & McNamara
(2013): r=.264 integrated, r=.377 independent, on TOEFL essays. Modest, but
replicated three times and computable from the dependency parse by counting
children of noun heads. **Confidence: medium**, all three numbers read inside
Kyle & Crossley's literature review, not from the underlying papers.

### Dependency distance

Separately and more usefully, Yannakoudakis, Briscoe & Medlock (2011), ACL —
grammatical-relation distance, meaning the longest head-to-dependent token
span per sentence. Adding it moved score prediction from r=.692 to r=.714;
ablating it dropped r from .741 to .712, the second-largest contribution of
any feature family after error rate. **Confidence: high**, tables read
directly.

This one matters because it is cheap, needs no external resource, and measures
something ARI cannot see. ARI counts characters per word and words per
sentence; a sentence of long words is not necessarily hard, and a deeply
nested sentence of short words is.

---

## Lexical sophistication: real, but it needs a corpus

The consistent finding is that **more proficient writers use lower-frequency
words** (Crossley & Kyle 2018, reviewing five studies). TAALES 2.0 reportedly
explained 58% of variance in rated lexical proficiency and 32% in word-choice
scores, though that is an abstract-level figure with sample and population
unverified.

Every one of these features needs a shipped reference corpus: frequency norms
(COCA, BNC, SUBTLEXus), psycholinguistic norms, the Academic Word List, n-gram
association tables. That is a packaging and licensing decision, not a coding
one.

**On concreteness — the check came back inconclusive, not confirming.** I
asked whether higher-rated writing uses *less* concrete words, since that would
cut against NB601. The honest answer: the searcher found lexical sophistication
*defined* as including "less concrete, imageable, and familiar" words, and
inferred the sign from that definition rather than reading a signed
coefficient. It flagged this itself. **Confidence: medium at best, and NB601 is
neither supported nor refuted by anything found here.** Given the
range-restriction problem (these are learner corpora, NB601 targets adult
prose), the question stays open.

**Two solid negative/methodological results:**

- **Raw type-token ratio is unusable and MATTR's design is vindicated.**
  Koizumi (2012): the effect of text length on TTR was η²=0.85, on the Guiraud
  index 0.90, versus 0.17 for MTLD. At 150–200 tokens, TTR η²=0.46 vs MTLD
  η²=0.04 (not significant). Length-robust windowed measures need **≥100
  tokens** to stabilize. nabokov already uses MATTR with a 100-token window,
  so this confirms the existing choice rather than prompting a change, but
  NB528 should not fire below that floor.
- **Mutual information beats t-score for collocation quality.** MI correlated
  rho=.344 with rated lexical richness; t-score showed no reliable relationship
  with any of eight proficiency measures. Relevant only if collocation work is
  ever attempted, and the study measured oral proficiency, not essays.

Also worth recording: TAALES's authors note their tool "does not examine
accuracy of lexical use": a misspelling that lands on another real word
("dual" as "duel") is silently scored as that other word. Any frequency-based
metric inherits this.

---

## Register and formality

**The Heylighen–Dewaele F-score** is the find in this section: a single
formality number from part-of-speech ratios alone.

```
F = (noun% + adjective% + preposition% + article%
     − pronoun% − verb% − adverb% − interjection% + 100) / 2
```

Higher means more formal and informational; lower means more involved and
context-dependent. Reported values: written 62 vs spoken 42; scientific texts
66, newspapers 68, novels 52, family magazines 58. On matched material from
the same speakers across situations: informal conversation 44, oral exam 54,
written exam essay 56.

**Confidence: high for the formula and the reported values, with one real
caveat**: the validation figures quoted are from Dutch word-frequency lists
and French interlanguage. No English validation was retrieved. The formula is
language-general in construction, but that is an argument, not evidence.

This is directly relevant because nabokov's `nominal_density` and
`pronoun_density` are an ad-hoc subset of exactly these ratios. The F-score is
the published, validated combination of the same signal.

**Biber's Dimension 1** (involved vs informational production) decomposes the
same contrast into ~30 co-occurring features: private verbs, that-deletion,
contractions, present tense, and second-person pronouns on the involved side;
nouns, word length, prepositions, type-token ratio, and attributive adjectives
on the informational side. **Confidence: medium**, the feature list and
replication figures came from a secondary thesis, not Biber's monograph.

**Hedges and boosters: no action.** The retrieved evidence (Park & Oh 2018,
Min et al. 2020) reached us only through a secondary paper's paraphrase, with
directional claims and no coefficients. **Confidence: low.** nabokov's NB303,
NB510 and NB520 already cover this ground on other grounds.

---

## Errors and grammar: out of construct

Recorded for completeness, and recommended against.

Error rate is the single strongest predictor in the one study that isolated
it: on the FCE corpus, adding an estimated grammatical error rate moved
prediction from r=.714 to r=.741, the largest single gain, against a human
examiner ceiling of r=.796 (Yannakoudakis et al. 2011). Error-type
distributions are well documented: on the BEA-2019 test set, punctuation
16.7%, uncategorizable/lexical 15.7%, determiners 10.4%, prepositions 8.3%.
Per-category correlation with TOEFL scores runs usage r=.64 > grammar r=.56 >
mechanics r=.38.

But this is grammatical error correction, it is overwhelmingly L2-specific,
and it is a different tool. nabokov is a prose linter, not a grammar checker,
and the categories that matter most here (word choice, multi-token edits) are
the ones the GEC field itself finds hardest: content-word errors scored in
the single digits to low twenties on F0.5 across all ten CoNLL-2014 teams.

Two related warnings against ambition: **dimension-specific scoring is much
weaker than holistic scoring**: holistic PCC ≥.75–.80 versus prompt adherence
PCC=.360 and comparable drops for thesis clarity, persuasiveness, and
organization (Ke & Ng 2019). And **naive LLM scoring is not a shortcut**:
ChatGPT-3.5 correlated r=.21–.23 with human scores where human-human agreement
was r=.72 (Kundu & Barbosa 2024). Both are relevant to any future judge-style
extension of the skills.

---

## Where this touches what nabokov already does

Nothing shipping is contradicted. Three things want adjusting:

1. **Nominal density is ambiguous in a way the current gloss hides.**
   `issue.py:98` glosses it as "high = noun-heavy, flat", which traces to the
   AI-prose synthesis claim that machine text is noun-heavier. Biber's result
   puts the *same* signal at the centre of mature academic writing: complex
   noun phrases are what expert prose compresses into. So a high nominal
   density is evidence of AI drafting **or** of competent academic register,
   and the metric alone cannot separate them. `readability.py` already refuses
   to score it, for the right reason (a direction with no threshold). This
   sharpens that call rather than changing it, but the one-line gloss states
   one interpretation as if it were the only one.
2. **The register block has a published alternative.** `nominal_density` +
   `pronoun_density` reimplement part of a validated formula. Adding the
   F-score alongside them costs almost nothing.

**Already handled, checked rather than assumed:** NB528 gates on
`_MIN_TOKENS = 120`, comfortably above the ≥100-token floor Koizumi's numbers
imply, and `mattr()` falls back to plain TTR only below its window. The
diversity path needs no change.

And one confirmation: the connective evidence supports the existing
skepticism. TAACO found connective density negligible-to-negative for quality,
which is the empirical version of what NB531 already asserts about bolted-on
connectors.

---

## Ranked implementation shortlist

Ranked by evidence strength × spaCy feasibility × fit to nabokov's actual
population, with the false-positive risk that killed the unsourced-statistic
rule assessed up front.

**First, the split — and it is lopsided.** Of 51 findings the searchers
returned, almost every one is a **document-level metric validated against a
holistic score**. The literature does not contain span-level rules with tested
fixes. Nobody has published "flag this clause, suggest this rewrite, here is
the measured effect." One searcher stated this explicitly: building a
rule-with-a-fix out of any of these is a plausible engineering extrapolation,
**not** a literature-backed one. So the honest split is that this research can
tell nabokov what to *measure*, and almost nothing about what to *flag*.

| Feature | Shape | spaCy | L2-only evidence? | Confidence | Verdict |
|---|---|---|---|---|---|
| Adjacent-paragraph lexical overlap | Metric (rule measured, killed) | Easy | No | High | **Shipped** |
| Dependency distance | Metric (does not feed NB201/202) | Easy | Yes (FCE learner corpus) | High | **Shipped** |
| Heylighen–Dewaele F-score | Metric | Easy | No | High formula, no English validation | **Shipped** |
| Noun-phrase modifier density | Metric | Easy | Yes | Medium | **Shipped** |
| Word-frequency band | Metric | Needs corpus | Learner populations | High | Packaging call |
| Entity-grid coherence | Metric, rule candidate | Hard | No | High, but wrong task | Spike first |
| Concreteness / psycholinguistic norms | Metric | Needs corpus | No | Low, sign unverified | Open |
| L2SCA T-unit indices | Metric | Hard, may need constituency | Yes | High | Reject |
| GEC error rate | Metric | Needs resource | Yes | High | Reject |
| Connective density | Rule | Easy | No | Medium | Reject, negative result |

**Read the L2 column before the confidence column.** Two of the four build
recommendations rest on learner evidence. Noun-phrase modifier density was
flagged L2-specific by the searcher outright. Dependency distance was flagged
general, but its supporting study is the Cambridge First Certificate corpus,
which is L2 by construction — I have marked it accordingly rather than trust
the flag. This is the range-restriction caveat from the top of the document,
landing on specific rows: these two are the rows where "does it transfer to
fluent adult prose?" is least answered.

### Tier 1 — worth building

**1. Adjacent-paragraph lexical overlap.** *Shipped as a metric. The rule was
measured and killed.*

The highest-correlating feature reachable from the parse alone (r=.40 quality,
r=.42 coherence), needing only a content-lemma set per paragraph and a set
intersection. No external resource, no new dependency.

**Implementation note, because the obvious formula failed.** Jaccard was tried
first and rejected: dividing by the union punishes a paragraph for being long,
and every document in this repo collapsed to 0.04–0.05 with no room to tell
them apart. Normalising by the *smaller* paragraph instead gives roughly three
times the spread. Validation is a shuffle test — reorder a document's
paragraphs, keeping every word and destroying only adjacency, and the score
drops on every file tried. That is the evidence it reads order rather than
vocabulary, which is the only claim being made for it. Repo prose calibrates to
0.07–0.40 per file.

**The rule did not survive contact with the corpus.** The plan was NB602: flag
a paragraph boundary where adjacent paragraphs share **zero** content lemmas,
since the editor skill says topic jumps are "the most common LLM failure" and
that no linter catches them. Measured against this repo's own hand-written
prose:

| Content-word floor | Zero-overlap pairs | Rate |
|---|---|---|
| ≥5 | 103 / 472 | 21.8% |
| ≥10 | 48 / 382 | 12.6% |
| ≥15 | 30 / 313 | 9.6% |
| ≥20 | 21 / 249 | 8.4% |
| ≥25 | 13 / 181 | 7.2% |

Roughly one adjacent pair in five, in prose written by hand, shares no content
lemma with its neighbour. Tightening the floor never reaches a usable rate, and
by ≥25 it has discarded 60% of the corpus to get to 7.2%. This is the same
shape as the unsourced-statistic rule (262 hits) and `missing-contributing`: a
"defect rate" that is simply the norm. **No NB602.** The metric ships; the
finding does not.

**2. Dependency distance.** *Metric, feeding NB201/NB202.*

Mean and max head-to-dependent token distance per sentence. One pass over the
parse nabokov already builds. Ablation evidence: removing it cost more than
any feature except error rate.

Its value is orthogonal to what exists: it predicted rated quality *on top of*
sentence length, which was already in the model when it was added. ARI counts
characters and words. Note the construct gap, though — Yannakoudakis shows
dependency distance predicts exam score, not that it predicts reading
difficulty. Treating it as a hardness signal for NB201/NB202 is an
extrapolation, and the dependency-locality literature that would justify it
was not retrieved.

*False-positive risk: low as a metric.* If it later gates a finding, it should
sharpen NB201/NB202 rather than add a new code.

### Tier 2 — cheap, weaker evidence

**3. Heylighen–Dewaele F-score.** A document metric costing roughly ten lines
over the part-of-speech counts already computed. It gives a genre-comparable
formality number where the current register block gives three ad-hoc ones.
Caveat: no English validation retrieved.

**4. Noun-phrase modifier density.** A document metric at r=.213–.377,
replicated three times, computable by counting dependents of noun heads.
Modest but honest.

### Tier 3 — waiting on a packaging decision

**5. Word-frequency band metric.** The best-supported lexical finding, but it
requires shipping a frequency corpus. That is a package-size and licensing
call. It also inherits the misspelling problem, and the range-restriction
caveat bites hardest here: the finding is about learners.

### Tier 4 — research spike, do not build blind

**6. Entity-grid coherence, string-identity variant.** Strong results on
sentence-ordering, and the coreference-free version loses only ~6 points. But
no study connects it to human quality ratings on real prose, and it is the
largest build on this list. Worth a spike against the corpus before any
commitment.

### Do not build

- **L2SCA / T-unit complexity indices** — R²=.058, needs constituency parsing,
  developmental claims unconfirmed against score data.
- **Grammatical error correction** — different tool, different construct,
  L2-specific.
- **Any rule that adds connectives** — negligible-to-negative correlation.
- **Anything keyed to document length** — the confound, not the signal.
- **A rule punishing sentence-level repetition** — the negative correlation is
  confounded; the experiment reverses the sign.

---

## What could not be established

- **Whether any of this transfers to fluent adult prose.** The searcher looked
  for a study testing frequency and concreteness relationships outside learner
  populations and did not find one. Every correlation here could be range-
  restricted away in nabokov's actual use case. This is the gap that should
  govern how much weight the shortlist gets.
- **Kyle & Crossley (2018) regression coefficients** — the accessible copy was
  an 8-page partial preprint containing only the introduction and literature
  review. ResearchGate 403, JSTOR paywalled, Semantic Scholar rate-limited.
  The phrasal-beats-clausal *direction* is confirmed; the effect sizes are not.
- **Whether TAASSC's fine-grained indices need constituency parsing.** Not
  confirmed from any fetched source, which is why they are marked hard rather
  than easy.
- **IELTS band-descriptor operationalization:** no paper was found mapping the
  IELTS Writing Task 2 descriptors to computable features. TOEFL and GMAT have
  this through e-rater. Either IELTS lacks an equivalent or it was not
  retrievable from the channels left open.
- **Perelman's construct-validity critiques** — the best-known attack on AES,
  absent because the search budget ran out.
- **Primary sources for hedging-vs-quality** (Park & Oh 2018, Min et al. 2020,
  Hyland & Milton 1997) — all paywalled; only a secondary paraphrase reached
  us.
- **An English validation of the F-score:** formula and non-English values
  only.

---

## Sources

Read directly, full text or substantial portions:

- Attali & Burstein (2006), *Automated Essay Scoring With e-rater V.2*, JTLA 4(3) — https://files.eric.ed.gov/fulltext/EJ843852.pdf
- Barzilay & Lapata (2008), *Modeling Local Coherence*, Computational Linguistics 34(1) — https://aclanthology.org/J08-1001.pdf
- Bryant, Felice & Briscoe (2017), ACL — https://aclanthology.org/P17-1074/
- Bryant et al. (2019), *The BEA-2019 Shared Task on GEC* — https://aclanthology.org/W19-4406/
- Crossley, Kyle & McNamara (2016), *TAACO*, Behavior Research Methods 48(4) — https://www.linguisticanalysistools.org/uploads/1/3/9/3/13935189/10.3758_s13428-015-0651-7.pdf
- Crossley & McNamara (2016), *Say more and be more coherent*, Journal of Writing Research 7(3) — https://files.eric.ed.gov/fulltext/ED565450.pdf
- Crossley & Kyle (2018), *Assessing Writing with TAALES* (preprint) — https://zenodo.org/records/7637966
- Heylighen & Dewaele (1999), *Formality of Language* — http://pespmc1.vub.ac.be/Papers/Formality.pdf
- Ke & Ng (2019), *AES: A Survey of the State of the Art*, IJCAI-19 — https://www.ijcai.org/proceedings/2019/0879.pdf
- Koizumi (2012), *Text Length and Lexical Diversity Measures*, VLI 1(1) — http://www.vli-journal.org/issues/01.1/issue01.1.10.pdf
- Kundu & Barbosa (2024), *Are LLMs Good Essay Graders?* — https://arxiv.org/abs/2409.13120
- Park (2022), *Syntactic complexity in a learner written corpus*, JLLS 18(1) — https://files.eric.ed.gov/fulltext/EJ1325786.pdf
- Quinlan, Higgins & Wolff (2009), ETS RR-09-01 — http://files.eric.ed.gov/fulltext/ED505571.pdf
- Yannakoudakis, Briscoe & Medlock (2011), ACL — https://aclanthology.org/P11-1019/
- Kyle & Crossley (2018) preprint, introduction and literature review only — https://zenodo.org/records/7637920

Abstract or secondary source only — figures from these carry lower confidence:

- Biber, Gray & Poonpon (2011), TESOL Quarterly 45(1) — ERIC EJ926093
- Biber, Gray & Staples (2016), Applied Linguistics 37(5)
- Coxhead (2000), *A New Academic Word List*, TESOL Quarterly 34(2)
- Deane (2013), Assessing Writing 18(1) — ERIC EJ995509
- Deng, Lei & Liu (2021)
- Hwang (2025), *Subordination Sophistication Analyzer*
- Kobrin, Deng & Shaw (2007), JATT 8(1) — ERIC EJ797381
- Kyle, Crossley & Berger (2017), *TAALES 2.0*, Behavior Research Methods
- Kyle & Crossley (2017), *Assessing Syntactic Sophistication in L2 Writing*
- Lu (2010, 2011) — L2SCA
- Norris & Ortega (2009), Applied Linguistics 30(4) — ERIC EJ867273
- Uchihara et al. (accepted), Language and Speech — https://discovery.ucl.ac.uk/10125957/1/LS.pdf
