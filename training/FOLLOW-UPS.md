# Follow-ups — deferred, not forgotten

Things found while working, deliberately left for later. Newest first.

---

## Live now, still hers to change (25 September 2026)

The career engine went live on Martina's call after Nicole reviewed the blind
table. Nothing below is blocked by it — these are adjustments to a running
system, and each is one edit:

- **The weights and the theme vocabulary.** Her weight table is applied as
  written; the ten professional themes are mine, keyed on the planets because
  a planet is what says what KIND of work something is. If she wants different
  themes or different weights, they are the tables at the top of
  `professional_themes_service.py` and `earning_routes_service.py`.
- **The orb policy has not been signed off in writing.** It is in use and says
  so in its own output. `app/orb_policy.py`.
- **Ranking on how unusual a score is for that route or theme**, rather than on
  the raw total — mine, and the one to argue with first. Without it one route
  won 46% of charts and two never won at all.
- **Placidus makes the MC ruler and the 10th ruler the same planet.** Counted
  once. If she meant two factors, that is a house-system decision and hers.
- **What Nicole has not sent back yet:** `career-blind-review.csv` from tab one
  of the blind table, and the two ranking columns of the data audit. The first
  is what would let the weights be tuned from where she actually disagrees.

---

## Waiting on the co-founder (24 September 2026)

- **The career data audit.** `training/area3/CAREER-DATA-AUDIT.md` — what the
  engine calculates and sends for a career question, what it leaves out, and
  two columns for her to mark what is worth adding and in what order. Every
  claim in it was checked against the running code.

  The three that look most consequential to us, for her to argue with:
  **aspects to the Midheaven are not calculated at all** (aspects are computed
  between planets only, so a square to the career point is invisible);
  **profections are scaffolded but never computed** (the prediction engine
  already boosts a transit landing on the profected house and understands a
  time lord — both are dead code because nothing works out the profected house
  from a birth date, so the boost has never once applied to a real person);
  and nothing ranks earning patterns, which is the item below.

- **The blind career table.** `training/area3/blind_career.html` — open it in a
  browser. Twelve invented charts. Tab one has the chart details her rules ask
  for and boxes for her own top three professional themes AND top three earning
  routes, with a download button; tab two has the engine's two rankings, the
  timing it chose and why, the profection, and the counterevidence. Blind and in
  that order on purpose.

  Her career and money rules document is implemented in full, and it wins over
  her earlier earning-routes PDF wherever the two differ — different route
  labels, "delivery" replacing "control" as the fifth dimension, and the
  three-point evidence widened from a planet CONJUNCT the MC to any close
  relevant aspect to it.

- **The orb policy needs her approval.** `app/orb_policy.py`, and it is printed
  at the top of the blind table. 8° for a conjunction or opposition between
  planets, 7° square or trine, 5° sextile; 6/5/3° to an angle; 3° to the 2nd
  cusp; two degrees wider when the Sun or Moon is involved. Exactness then
  becomes a weight from 0.2 to 1.0, so a 1° contact counts roughly four times a
  contact at the edge of its allowance — her instruction that an 8° conjunction
  must not quietly equal a 1° one. It governs the career engines only, so
  approving it cannot silently change every other reading in the product.

- **Two calls of mine inside her framework**, both flagged in the engine's own
  output. Routes and themes are ranked on how unusual a score is for THAT route
  or theme rather than on the raw total — without it, one route won 46% of
  charts and two never won at all, because her evidence column names five
  houses for one and one house for another. And under Placidus the MC is the
  10th cusp, so "the MC ruler" and "the 10th ruler" are always the same planet;
  they are counted once. If she meant them as two factors, that is a
  house-system decision and hers.

- **Calibration, 1,000 invented charts** (`training/area3/career_distribution.py`):
  themes rank first 7.6–11.9% each (even is 10%), routes 13.0–22.7% (even is
  16.7%), nothing near 50%. The same timing window is chosen for all four
  question types on only 12% of charts — it was effectively 100% before, because
  every answer led with the largest transit in a two-year list. Timing is called
  unclear on about half of charts, evenly across question types.

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
