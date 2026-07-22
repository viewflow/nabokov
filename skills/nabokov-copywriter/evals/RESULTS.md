# Eval results — 2026-07-22

Five with-skill runs across all four goals, plus two no-skill baselines on the
fabrication-critical cases. Fabrication (assertion A) is graded objectively; copy
quality is read qualitatively.

Per case (structure used, and how the fabrication line held):

- **sell, facts absent (skill):** pass. Named PAS, invented nothing, asked six
  questions for the missing specifics.
- **sell, facts absent (baseline):** partial. Slipped an unstated "free" claim,
  which it self-flagged; otherwise clean.
- **sell, facts present (skill):** pass. PAS; cut the draft's unsupported
  "reliable" and declined to compute a "34 min saved" figure. Numbers exact.
- **sell, facts present (baseline):** pass. Comparable to the skill run; numbers
  and names exact.
- **reach (skill):** pass. BAB, with the 40→6 result as the shareable hook.
- **provoke (skill):** pass. Stance-first, and it rejected PMHS to avoid
  manufacturing pain the facts didn't give.
- **trust (skill):** pass. QUEST in its grounded-exposition variant, no invented
  customers or competitor tool names.

**7/7 held the fabrication line.** No invented numbers, prices, testimonials,
customers, or outcomes. Additions were disclosed synonyms, framing, and mechanism
that follow from a given fact.

**The delta the skill buys (vs. a plain agent):**
- Facts-absent: with-skill invented nothing and refused to soften "sign up" toward
  "free"; the baseline slipped an unstated "free" claim.
- The provoke run rejected PMHS because its "more pain" beat would force it to
  manufacture agitation the facts didn't supply — the invariant driving structure.
- Every with-skill run named its formula, justified it against the goal, and
  re-linted with the right `--target`.
- Wash on facts-present: a strong model preserves given numbers well either way.
  The skill's value concentrates on missing facts and non-obvious goal→formula
  choices.

**Known false positive (harness, not the skill):** a strict security monitor may
flag `nabokov --target social` as "publishing to social media." It is a local
readability preset; nothing is sent anywhere.
