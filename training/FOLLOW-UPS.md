# Follow-ups — deferred, not forgotten

Things found while working, deliberately left for later. Newest first.

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
