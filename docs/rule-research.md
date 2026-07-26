# Candidate rules for nabokov: technical docs and READMEs

Research date: 2026-07-26. Sources cited inline; every substantive claim links to
a primary source I actually read. Where I could not read a source, I say so.

**Method caveat.** The `/deep-research` workflow failed twice on API 529s before
any agent ran, so this was gathered single-threaded. It has real citations but
**not** the 3-vote adversarial verification the workflow would have applied.
Treat the FP-risk judgments as mine, not as verified findings.

---

## The finding that should change the plan

Most "README checklist" advice is convention repeated between blog posts. The one
large empirical study of README *content* contradicts a lot of it.

Prana et al. hand-annotated **4,226 sections across 393 randomly sampled GitHub
repositories** into eight categories. Share of README **files** containing at
least one section of each category:

| Category | % of files | A "missing X" rule would fire on |
|---|---|---|
| What | **97.0%** | 3% |
| How | **88.5%** | 11.5% |
| References | 60.8% | 39% |
| Who | 52.9% | 47% |
| Contribution | **27.8%** | **72%** |
| Why | **25.7%** | **74%** |
| When | **21.4%** | **79%** |
| Other | 6.9% | 93% |

Source: [Categorizing the Content of GitHub README Files](https://link.springer.com/article/10.1007/s10664-018-9660-3)
(arXiv: [1802.06997](https://arxiv.org/abs/1802.06997); numbers from Table 3 of the
[author PDF](https://soarsmu.github.io/papers/2019/Prana2019CategorizingGithubReadme.pdf)).

**Consequence.** A rule demanding a Contributing / Why / When section fires on
72–79% of real-world READMEs. Under nabokov's precision-over-recall philosophy
that is disqualifying — those are not defects, they are the norm. Only **What**
and **How** are near-universal enough to lint for.

This kills more proposed rules than it creates, which is the useful outcome.

I could not verify the separate claim that README content correlates with project
popularity — [the study](https://www.sciencedirect.com/science/article/abs/pii/S0164121223002017)
is paywalled (403). **Do not build on it.**

---

## The one architectural decision behind everything in Group B

`source.py` blanks markup length-preservingly and analyzes only visible prose. So
nabokov currently cannot see code fences, heading syntax, link URLs, or image tags
— by design.

Note that `_blank(match, keep=2)` **already distinguishes** link text from link
URL (it preserves the visible text and blanks the target). The information exists
at blanking time and is thrown away.

**The unlock:** emit a typed span index alongside the blanked text — a list of
`(start, end, kind)` where kind ∈ {heading, fence, inline-code, link-text,
link-url, image-alt}. Length-preservation is untouched, offsets stay valid, and
every Group B rule plus the sharper half of Group A becomes possible. This is one
focused change to `source.py`, not a redesign. Nothing in Group B should be
attempted before it.

---

## Prior art (so nothing gets reinvented)

- **Vale Google style**, 31 rules: `Passive`, `We`, `Will`, `FirstPerson`,
  `Headings`, `HeadingPunctuation`, `LyHyphens`, `OxfordComma`, `Contractions`,
  `Latin`, `Slang`, `Gender`, `GenderBias`, `Acronyms`, `Ellipses`, `EmDash`,
  `Exclamation`, `Ranges`, `Units`, `Spelling`, `WordList` …
  ([repo](https://github.com/errata-ai/Google))
- **Vale Microsoft style**, 22 rules: adds `Accessibility`, `Adverbs`, `Avoid`,
  `ComplexWords`, `Terms`, `HeadingColons`, conditional `Acronyms`
  ([repo](https://github.com/errata-ai/Microsoft))
- **alex** — gendered work-titles, gendered proverbs, ableist language,
  condescending language ("obviously", "everyone knows"), intolerant phrasing
  (master/slave), profanities. Its own README concedes "alex isn't very smart"
  ([repo](https://github.com/get-alex/alex))
- **proselint** — **not syntax-aware**, so it fires inside code blocks; inactive
  since 2018; LWN's Grumpy Editor likened it to "one of the world's worst
  elementary-school teachers criticizing you in front of the entire class about
  irrelevant details" ([LWN](https://lwn.net/Articles/822969/)). Its authors
  self-report a 1:10 false-discovery rate, 20× better than Word
  ([SciPy 2016](https://suchow.io/assets/docs/pacer2016proselint.pdf)) — note that
  is the authors measuring their own tool.

nabokov's spaCy parse and markup blanking already put it ahead of proselint's
core weakness. That is the competitive position to protect: **do not port a rule
whose prior art is known-noisy without adding a parse-based guard.**

---

## GROUP A — prose rules that fit the current architecture

Ranked by (value × precision) / cost.

### A1. NB308 `condescending-simplifier` — **build this first**

Flags words that tell the reader a task is easy: `simply`, `easily`, `obvious(ly)`,
`of course`, `trivial(ly)`, `merely`, `straightforward`, `everyone knows`.

- **Fires:** "Simply run the migration and you're done."
- **Must not fire:** "The API returns a simple object." (adjective, not a claim
  about the reader's effort); "We chose the simplest of the three designs."
- **Detection:** closed word list + POS. Only flag `simply`/`easily` as ADV
  modifying an imperative or a verb of user action; only flag `simple`/
  `straightforward` when they modify the *task*, not a thing.
- **Fix tier:** REPLACE-delete when adverbial and position-safe (reuse
  `deletion_is_safe`); ADVISORY for `obvious`/`trivial`, where cutting the word
  leaves a broken clause.
- **Severity:** warning. **Targets:** off for SOCIAL/ESSAY (voice), on for TECHNICAL.
- **Prior art:** alex (condescending), Microsoft `Avoid`.
- **FP risk:** collision with NB303 on `just` — needs adding to `_DEDUP_WINNERS`
  or it double-reports. This is the single highest-value rule here: it is
  well-supported by both major style guides, and the failure it names (telling a
  stuck reader the thing is easy) is a real harm, not a stylistic preference.

### A2. NB309 `vague-link-text`

Flags `click here`, `read this`, `this document`, `learn more`, bare `here` as
link text.

- **Fires:** "For the config options, [click here](/config)."
- **Must not fire:** "Add the file here, then commit." (not link text)
- **Detection:** *cheap version* — phrase match on `click here` / `read this`
  anywhere in prose; these are bad regardless. *Sharp version* — needs the
  link-text span kind from the markup index.
- **Fix tier:** REWRITE. The replacement must name the destination, which the
  linter does not know. Never REPLACE.
- **Severity:** warning for `click here`, info for bare `here`.
- **Prior art:** Google, WCAG 2.4.4.
- **Source:** [Google — Write accessible documentation](https://developers.google.com/style/accessibility)
- **FP risk:** bare `here` is far too common in ordinary prose — ship only the
  closed multi-word phrases until the markup index lands.

### A3. NB310 `directional-language`

Flags `above`, `below`, `right-hand side`, `as shown above` used to orient the reader.

- **Fires:** "In the diagram above, clients run jobs on clusters."
- **Must not fire:** "values above 50%"; "the panel on the left" in a doc genuinely
  describing spatial UI layout.
- **Detection:** spaCy — `above`/`below` as ADV/ADP attached to a noun like
  diagram/table/section/example. Guard against numeric comparison.
- **Fix tier:** **REWRITE, not REPLACE** — and this is the instructive case.
  Google's fix is "the diagram above" → "the **preceding** diagram", which *moves
  the word to the other side of the noun*. An in-place substitution on the flagged
  span cannot express that. Exactly the trap the tier system exists to catch.
- **Severity:** info. **Targets:** off for SOCIAL/ESSAY.
- **Prior art:** Microsoft `Accessibility`.
- **Source:** [Google — accessibility](https://developers.google.com/style/accessibility)

### A4. NB315 `undefined-acronym`

Flags an acronym used before it is expanded.

- **Fires:** "Configure the FQDN in the settings." (never expanded)
- **Must not fire:** `API`, `HTTP`, `JSON`, `CLI`, `URL` — a closed allowlist of
  acronyms assumed known to a developer audience.
- **Detection:** document-level state; `[A-Z]{2,}` tokens, minus allowlist, minus
  any expanded earlier as "Fully Qualified Domain Name (FQDN)".
- **Fix tier:** ADVISORY. The tool cannot know the expansion.
- **Severity:** info. **Targets:** on for TECHNICAL/ACCESSIBLE, off for SOCIAL.
- **Prior art:** both Vale Google and Microsoft ship `Acronyms`; Microsoft's is a
  *conditional* check, i.e. exactly this definition-before-use pattern.
- **FP risk:** the allowlist *is* the rule. Ship it generous and let config extend
  it. Fits nabokov's closed-list philosophy perfectly.

### A5. NB313 `non-imperative-step`

Flags a numbered/bulleted instruction that is not in the imperative.

- **Fires:** "1. You should click Save." / "1. The user clicks Save."
- **Must not fire:** "1. Click **Save**."; a bulleted list of *facts* rather than
  actions ("- Requires Python 3.12").
- **Detection:** list item whose sentence root is a finite verb with an explicit
  `nsubj` of `you`/`the user`, rather than a bare `VB` imperative. Needs to know
  the sentence was a list item — the list-marker blanking already forces a
  sentence break there, but does not record the fact.
- **Fix tier:** REWRITE (drop the subject, conjugate to base form).
- **Severity:** info. **Targets:** a genuine argument for a new `docs` target.
- **Sources:** [Diátaxis — how-to guides](https://diataxis.fr/how-to-guides/)
  ("conditional imperatives": *If you want x, do y*; a how-to must contain "no
  digression, explanation, teaching");
  [Google — person](https://developers.google.com/style/person) (imperative with
  implied "you": "Click **Submit**").
- **FP risk:** distinguishing an action list from a fact list is the hard part.
  Prototype before committing.

### A6. NB314 `exclusionary-terminology` — **opt-in family, like NB5**

Flags `whitelist`/`blacklist`, `master`/`slave`, `sanity check`, `grandfathered`,
`dummy value`.

- **Fires:** "Add the IP to the whitelist."
- **Must not fire:** "mastering the API"; "a master's degree"; arguably `master`
  as a lone git branch name.
- **Detection:** closed phrase list. **Only flag `master` in the slave-paired or
  explicitly configured collocation** — lone `master` is hopelessly ambiguous.
- **Fix tier:** REPLACE — `whitelist`→`allowlist`, `blacklist`→`denylist`,
  `master/slave`→`primary/replica`. Single tokens, same part of speech, so
  `match_case` handles the capital. One of the cleanest REPLACE candidates in
  the whole list.
- **Severity:** info, **off by default** behind its own flag. This is a values
  choice a project opts into, not a defect — shipping it on by default would be
  nabokov taking a position on the user's behalf.
- **Prior art:** alex.
- **Source:** [IETF draft-knodel-terminology](https://datatracker.ietf.org/doc/draft-knodel-terminology/06/)
  (replacements: primary-secondary, primary-replica, active-standby, writer-reader).

### A7. NB311 `future-tense` — **contested, low priority**

Flags `will` + verb in reference documentation.

- **Rationale:** Vale Google ships `Will.yml`; reference docs conventionally use
  present tense ("the function returns", not "will return").
- **Fix tier:** REWRITE — `will return` → `returns` needs subject-verb agreement
  the lookup cannot supply. Same class of trap as NB302's present-tense passive.
- **Why low priority:** `will` is *correct* for genuinely future events ("the
  deprecation will land in v3"). Static analysis cannot separate "describes
  current behavior in the future tense" from "describes a future event". Medium-
  to-high FP rate on a rule whose payoff is small.

### A8. NB312 `first-person-plural` — **recommend NOT building**

Google does say prefer "you" over "we"
([source](https://developers.google.com/style/person)) and Vale ships both `We`
and `FirstPerson`. But Google explicitly permits "we" for the authoring
organization: *"Example Organization provides A and B, but we don't provide C."*

Separating "we the docs authors addressing you" from "we the organization" needs
discourse-level semantics. nabokov would fire on legitimate usage constantly.
**This is a rule that looks obvious, has real prior art, and should still be
skipped** — precisely the kind of thing precision-first exists to refuse.

---

## GROUP B — structure rules (all blocked on the markup span index)

### B1. NB801 `no-description` — only structure rule with strong evidence

Flags a README whose first prose block is badges/images with no one-line
description of what the project is.

- **Evidence:** 97.0% of real READMEs have a "What" section, so this fires on ~3%.
  That is a genuine outlier rate.
- **Fix tier:** ADVISORY. **Severity:** warning. **Detection:** markup index +
  document position.

### B2. NB802 `no-usage-section`

Flags a README with no install/usage/how content. Fires on ~11.5% by the Prana
data. Defensible, weaker than B1.

### B3. NB806 `image-without-alt-text`

Flags `![](img.png)` — empty alt on a non-decorative image.

- **Fix tier:** ADVISORY (the tool cannot write alt text). **Severity:** info.
- **Detection:** markup index only; no NLP needed. Cheapest rule in Group B.
- **Sources:** [Google — accessibility](https://developers.google.com/style/accessibility)
  ("For every image, provide an alt attribute… if the image is purely decorative,
  use empty alt text" — so empty alt is *legitimate* for decorative images, which
  caps achievable precision), WCAG 1.1.1.

### B4. NB805 `heading-punctuation`

Flags a trailing period or stray colon in a heading. Both Vale Google and
Microsoft ship this (`HeadingPunctuation`, `HeadingColons`). Mechanical, REPLACE
tier, very high precision — but needs heading spans, which are currently blanked.

### B5. NB803 `no-runnable-example`

Flags a README with zero fenced code blocks. Plausible for a library; wrong for a
design-doc or a spec repo. Needs fence spans. **Evidence is convention, not
measurement** — I found no study showing example presence predicts anything.

### ❌ Do NOT build: `missing-contributing`, `missing-why`, `missing-when`

Fire on 72–79% of real READMEs (Prana Table 3). Popular checklist advice,
contradicted by the data.

### ❌ Out of scope: dead-link checking

Needs filesystem and network access. That is a link checker, not a prose linter;
`lychee` already does it well.

---

## Recommended order

1. ~~**NB308 condescending-simplifier**~~ — **shipped**, see `NB308` in RULES.md.
2. **NB315 undefined-acronym** — closed allowlist, fits the philosophy exactly.
3. **NB314 exclusionary-terminology** — clean REPLACE fixes; ship off-by-default.
4. **NB309 vague-link-text** (cheap phrase-only version).
5. **NB310 directional-language** — good REWRITE-tier teaching case.
6. *Then* the `source.py` span index, which unlocks B1/B3/B4 and sharpens A2/A5.

Skip A8 entirely. Treat A7 as optional.

## Where the evidence is thin — stated plainly

- **README section checklists**: mostly fashion. The Prana data contradicts the
  common advice for 3 of 8 categories.
- **README → popularity**: unverified, paywalled. Do not cite it.
- **"No future tense"**: a house convention of Google/Microsoft, not a measured
  readability effect.
- **"Every README needs a code example"**: convention; no study found.
- **proselint's 1:10 false-discovery claim**: self-reported by its authors.
- Google, Microsoft, and Diátaxis **agree** on imperative mood for instructions,
  second person, and descriptive link text. Those three are the safest ground here.
