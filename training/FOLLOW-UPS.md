# Follow-ups — deferred, not forgotten

Things found while working, deliberately left for later. Newest first.

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

- **The blind earning-route table.** `training/area3/blind_routes.html` — open
  it in a browser. Twelve invented charts; tab one has the chart details her
  framework asks for and boxes for her own top three, with a download button;
  tab two has the engine's ranking with evidence and counterevidence. Blind and
  in that order on purpose.

  `app/earning_routes_service.py` implements her document as written: the six
  routes, the weight table, the five dimensions, and all six rules — trace
  money from the 2nd and its ruler first, two independent signals with one on
  the money house to call a route strong, never count the same aspect twice,
  condition changes how a route works rather than whether it exists, rank at
  most three, and the person's own facts never count as chart evidence (they
  cannot even reach the function).

  **Two numbers and one method are mine, not hers**, and the engine says so in
  its own output:
  - a "close" connection is 4° — her document says close without a number
  - two routes read as complementary within 0.03 of each other
  - **routes are ranked on how unusual a score is for that route, not on the
    raw total.** This one matters most and she should push back on it if she
    disagrees. Her evidence column names five houses for business and one for
    partnerships, so business has five chances at the 5-point evidence.
    Ranked on the raw total, business came first for 46% of a thousand charts
    and partnerships never came first at all; employment came first 3% of the
    time. Her weights are untouched and the raw score is still what the audit
    trail shows — only the comparison between routes changed. With it, the six
    routes rank first 14–20% each.

  Also new, and the gap the earlier audit found: **aspects to the Midheaven
  and the angles are now calculated** (`app/angle_aspects_service.py`), because
  her weight table awards points for a planet conjunct the MC and nothing in
  the system could see one.

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
