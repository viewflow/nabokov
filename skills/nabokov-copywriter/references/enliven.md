# Enliven — the cinematic pass

The job: make the reader see it. Flat copy states; enlivened copy shows, so the
scene plays in the reader's head. Every technique here works on the user's real
facts. None of them licenses inventing one. When a technique needs a detail you
don't have, that's a question for the user, not a blank to fill.

## Show, don't tell

Naming a feeling or a quality is the weakest way to convey it. The reader believes
what they can picture, not what they're told to conclude.

- "The customer was thrilled" → the thing the customer *did* that showed it: the
  same-day reply, the reorder, the referral. Use the one the user actually saw.
- "Our onboarding is fast" → "You paste one key and send a test charge before your
  coffee's cold." (Only if it's true — if setup takes an hour, don't.)
- "The dashboard is powerful" → the specific thing it let a real user do.

The move is: find the abstraction, ask "what concrete thing demonstrates this?",
and if the user gave you that thing, write it instead of the label. If they
didn't, ask. A show-don't-tell rewrite that invents the demonstrating detail is
the exact failure this skill exists to prevent.

## Sensory and concrete detail

Abstractions live in the intellect; details live in the body. Where the domain has
real texture — a product you can hold, a place, a physical process — reach for the
sense the reader would actually use. Coffee has an aroma and an aftertaste; a CLI
has the moment the first green check appears. Pull the detail from the real thing,
not from a stock image of it. A B2B API has no smell; forcing sensory language
onto it reads worse than plain.

## Strong verbs

A precise verb carries a sentence that a weak verb plus an adverb only props up.
"Ran quickly" → "sprinted". "Made the process faster" → "cut the wait". "Is a
solution for" → "solves". nabokov's NB301 (adverbs) and NB304 (an action buried in
a noun behind a light verb — "made an improvement" → "improved") point at exactly
these; act on them here. Strong verbs are free energy: no new claim, more force.

## Metaphor, on a short leash

A grounded metaphor clarifies; a decorative one is slop. The test: does it come
from the real domain, and does it make the idea *more* concrete? "Your inbox is a
to-do list other people write" — grounded, sharpens the point. "A symphony of
seamless synergy" — decorative, delete. Budget roughly one live metaphor per few
paragraphs, and only when it earns its place. This is the "don't go full GPT" line
from the brief made operational.

## Rhythm (Gary Provost)

Vary sentence length or the prose drones. Provost's demonstration is the model: a
run of equal-length sentences reads like a stuck record; mix three-word punches
with long, carrying sentences and the prose finds a pulse. Short sentences land a
point and create urgency. Long ones immerse and build. Read the draft in your head
and listen for the plod — that's where nabokov's NB509 (flat rhythm) fires. Fix it
by splitting one sentence short and letting the next run long, not by chopping
everything into fragments (that's its own AI tell, NB507).

Rhythm lives inside sentences too. Machine prose punctuates on a metronome — a
comma or dash every clause, all clauses the same weight. Human prose
under-punctuates and over-punctuates: a 25-word run with no comma at all, then a
two-word aside. When you build a long sentence, let it run loose on "and" and
"so" instead of slicing it into balanced comma'd clauses; `--score` prints a
punct-rhythm number that drops when every segment comes out the same size.

## Human noise — carefully

Real writing has a little texture: a first-person aside, a small honest doubt, a
plain aside that a machine wouldn't risk. A touch of it signals a person wrote
this. But it cuts against the de-slop pass, which strips hedge-stacks and filler.
So add human noise as *deliberate voice*, and use it sparingly. Never let it
become the reflexive hedging ("it's worth noting that", "in today's world") that
reads as machine filler. One genuine aside beats five nervous qualifiers. When in
doubt, the linter's NB520 (hedge stack) and NB504 (filler) mark the line.

Noise is syntactic as much as lexical. A parenthetical dropped mid-sentence, a
paragraph that ends flat instead of on a beat, one long sentence left loosely
coordinated where a machine would balance it — these read human because they are
how drafts actually come out. The cheapest source of all of this is the author's
own draft: a line nothing flagged keeps its original wording, word for word.
Their phrasing — slightly off-balance, personally theirs — is the noise you
cannot fake, and paraphrasing it away is how a clean rewrite ends up scoring
100% AI. Never inject errors to fake any of this; looseness is not sloppiness,
and a manufactured typo is fabrication aimed at the reader.

## The order matters

Do these in the SKILL.md pass order: enliven first (this file), then rhythm, then
assemble for the goal. Enlivening changes sentence lengths, so tune rhythm after,
not before. And always re-lint at the end — the floor stays the floor.
