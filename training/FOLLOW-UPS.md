# Follow-ups — deferred, not forgotten

Things found while working, deliberately left for later. Newest first.

---

## Waiting on the co-founder (24 September 2026)

- **Which earning patterns she would name, and how she would weight them.**
  `app/earning_profile_service.py` scores a chart on five spectrums — the named
  person or the one behind it; a few clients or many buyers; their own money or
  other people's; judgement sold as advice or a thing sold as a product; a
  steady build or work in waves. Those five are mine, chosen because they are
  what a person can act on, and she may want different ones entirely.

  The house weights inside it are hers already, lifted from the money table she
  wrote for the city rankings — the one table in the codebase an astrologer
  actually authored. Everything else (which houses pull which way, the planet
  tilts) is assembled by analogy and marked as such in the output.

  Bands are calibrated over a thousand invented charts
  (`training/area3/distribution.py`), so the thresholds are measured rather
  than guessed. Across those charts the five spectrums split between 43/57 and
  58/42, and a third of charts have nothing pronounced at all — which is the
  honest outcome, not a failure.

  **Not wired into any answer.** A test enforces that.

- **Calibration table review and friendship weights.** The twelve-pair table is
  in `training/area2/`. Section 1 is blind — chart contacts with an empty
  column for her own lean — and section 2 has the scores. Friendship runs at
  equal weights until she adjusts them from her disagreements.
- **The three-degree contact orb.** Currently `CONTACT_ORB` in
  `app/transit_timing_service.py`. To be made a setting she can change.
- **Whether "Saturn conjunction their Saturn" counts as a connection window.**
  It is a transit to his chart, so it currently ranks as being about the two of
  them — but a Saturn return is arguably his alone, the way hers is hers.
- **Power and attachment stay internal.** Not sent to the model at all. Hers to
  decide whether they are ever readable.
- **Friendship-based leans are not live.** Built and tested, not wired into any
  answer, pending her review.

---

## A saved person never reaches an ordinary question

**Found:** 23 September 2026, while widening the gendered-pronoun evidence rule.

**What happens now.** A normal chat question goes to `/ask-astrologer`, and
that request carries only the user's own birth details:

```python
class AstrologyQuestionRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    question: str
    ...
```

There is no field identifying which saved person the conversation is about.
So even when someone has "Luka — ex boyfriend" saved and selected in the
sidebar, asking "should I text him?" sends nothing about Luka at all.

Only `/ask-compatibility` receives a person, via `profile_id`, and it already
passes their `label` and `relationship_type` through to the review step.

**Why it matters.**

1. The pronoun rule can't use a saved relationship type on ordinary questions,
   so "him" is rejected unless the user happens to have typed a gendered word
   themselves.
2. More broadly, Zoli doesn't know who a conversation is *about* unless the
   user restates it every time — so it can't use the relationship type to
   judge intensity, or the person's name naturally.

**What fixing it involves** (a real change, not a tweak):

- add an optional `profile_id` to `AstrologyQuestionRequest`
- re-check ownership server-side, the way `/ask-compatibility` already does —
  a guessed id must not pull someone else's saved person into an answer
- pass `label` and `relationship_type` into the conversation facts
- send the selected person from the chat page, which currently doesn't

**Deliberately deferred.** Martina's call, 23 September 2026.

---

## Cost of the longer answers

**Found:** 22–23 September 2026, across several routing changes.

Answers got longer in several places on purpose: follow-ups are no longer
capped at tier 3, first-person statements now get a real answer, and
relocation questions get a bigger budget. Each was the right call on its own;
together they push the cost per conversation up.

Nothing is wrong yet. Spend tracking is on `/admin`. Worth a look after a few
days of real use, and the fix would be tuning the ceilings rather than undoing
the routing.

**Added 24 September 2026:** career and money questions now get 820 tokens
instead of 550, about half as much again, on tier-4 questions only. Follow-ups
inside a career thread are unaffected. Same note applies: watch it on `/admin`
rather than pre-emptively trimming.

---

## Not yet done, from earlier

- **Turn on Resend** — forgot-password is still dark without it.
- **Review the six draft scoring tables** for the city rankings. Only the money
  table came from an astrologer; the rest were written by analogy and are
  marked as such in the output.
- **The Descendant / IC question** for the love and home scoring tables.
- **Swiss Ephemeris licence** — 700 CHF, `order@astro.com`.
- **Outside the code:** the domain, the email sender address, and anything
  still named "Zodi" in Vercel, Render or Lemon Squeezy.
