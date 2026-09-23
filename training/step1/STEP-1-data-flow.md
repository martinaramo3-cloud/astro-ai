# Step 1 — How Zoli builds a request to the AI

*Prepared for Martina, founder of Zoli. Nothing in the app was changed to produce this.*

---

## Context for whoever is reading this

**Zoli** is an AI astrology chat app. Its own code does all the astronomy —
birth charts, transits, chart-to-chart comparisons, timing windows — and then
hands that data to a general-purpose AI model, which writes the reply the user
reads. The model does no astronomy. It never calculates a date; it only reads
dates the code calculated.

**The goal this document is preparing for** is fine-tuning a model so Zoli
answers the way Martina wants, specifically:

1. **Plain language.** Uses the astrology in the background, never says
   "houses", "aspects" or "degrees" to the user. Sun signs and "full moon" are
   fine.
2. **Length matched to the question**, the way a smart friend would — moving
   away from the current four fixed length tiers.
3. **A consistent answer shape**: verdict first → name the real feeling
   underneath → one plain reason from the chart → a concrete next move.
4. **Timing with specific dates**, but only ever from real calculated transit
   data. Never an invented date.

This document describes what the app does *today*, so a training format can be
designed against it.

---

## 1. The files involved

A question travels through five files. In order:

| File | What it does |
|---|---|
| `app/question_router.py` | Reads the question. Decides the **tier** (1–4) and the **topic** (relationship, career, emotional, general…). |
| `app/conversation_service.py` | Decides whether this is a new question or a follow-up, and sets the **word budget**. |
| `app/main.py` | Runs all the astrology and gathers it into one bundle (`chat_context`). |
| `app/ai_context_service.py` | Turns that bundle into the **two blocks of text** that go to the model. |
| `app/ai_service.py` | Sends them to OpenAI or Anthropic and returns the answer. |

One more file runs *after* the model replies:

| File | What it does |
|---|---|
| `app/answer_review_service.py` | Inspects the draft. If it breaks a rule, it asks the model to rewrite once. If the rewrite still fails, it may substitute a safe reply. |

---

## 2. What is actually sent

Every request is **two blocks of text**.

### Block 1 — the standing instructions ("system")

Built by `build_ask_astrologer_system()`, which is simply:

```python
def build_ask_astrologer_system() -> str:
    return _voice_guidance() + "\n\n" + _prompt_preamble()
```

**It is byte-for-byte identical on every request.** That is deliberate — both
providers cache an unchanged prefix, so repeat questions in a session only pay
for the changing half.

**Current size: 17,766 characters.**

Its sections, in order:

1. Who Zoli is; answer the actual question; match their energy
2. **Plain language rule** — reason with the astrology internally, never name
   planets, houses, aspects, retrogrades or rulers unless explicitly asked
3. **FOUR SIZES OF ANSWER** — the four tiers (see §4 below)
4. **Routing** — stakes decide the size, never message length
5. Continuing a conversation — answer the new detail, never repeat a prior
   conclusion
6. Earlier conversations — it gets *titles only* of other chats, not contents
7. Never narrate its own limits ("I don't have memory between chats")
8. Don't argue about what it said; don't reframe what someone brings; don't
   lecture
9. Personal facts — never assume children, marriage, job, pronouns, age
10. **Certainty** — be plain about timing and their own choices; never promise
    another person's behaviour or a guaranteed outcome
11. **Commit to ONE reading** — no menu of possibilities, no covering both
    branches, no ending by asking them what happened
12. **WHEN** — how to answer timing questions using the calculated windows
13. Explaining on request; doing the calculation rather than handing it back;
    business/launch charts read as an entity, not a person
14. Safety floor

The complete text is in the companion file **`01-system-half.txt`**.

### Block 2 — this request only ("user")

Built by:

```python
def build_ask_astrologer_user(chat_context: dict) -> str:
    internal = {k: v for k, v in chat_context.items()
                if k not in {"history", "question", "conversation", "past_conversations"}}
    return (_history_guidance(chat_context)
            + "\n\nINTERNAL CALCULATIONS — use for reasoning, not a default report:\n"
            + json.dumps(internal, ensure_ascii=False)
            + "\n\n" + TIER_DIRECTIVE.get(chat_context.get("answer_tier", 4), TIER_DIRECTIVE[4]))
```

So it is three parts glued together:

**Part 1 — the conversation.** A JSON object:

```json
{
  "kind": "follow_up",
  "latest_message": "when is this thing with him actually going to come to a head?",
  "original_question": "we fought and honestly im done",
  "topic": "general",
  "mode": "everyday",
  "recent_turns": [ … ],
  "reported_facts": { "saved_profile": {…}, "user_statements": [ … ] },
  "recap_requested": false,
  "max_words": 420,
  "max_paragraphs": 5,
  "conversation_cue": null
}
```

`mode` is either `everyday` (no astrology vocabulary allowed) or
`astrology_on_request` (they explicitly asked how the chart says it).

**Part 2 — the calculations.** One large JSON object. For the captured
example, 27,801 characters in total, broken down as:

```
  8,435 chars   predictive_timeline   ← dated windows, searched up to 2 years ahead
  6,299 chars   active_transits
  3,896 chars   chart_structure
  2,309 chars   sky_now
  1,554 chars   prediction
  1,390 chars   personal_planets
  1,102 chars   relevant_transits
    570 chars   relevant_planets
    391 chars   sources
    367 chars   relevant_aspects
     41 chars   midheaven
     36 chars   ascendant
      9 chars   question_type
      4 chars   requested_detail
      4 chars   conversation_cue
      4 chars   birth_time_known
      1 char    answer_tier
```

**Part 3 — one sentence naming the tier.** See §4.

The complete text is in the companion file **`02-user-half.txt`**.

---

## 3. Where a real date comes from

This is the most important part for the "timing with real dates" goal.

`predictive_timeline` is produced by `app/transit_timing_service.py`. It scans
forward (24 months for relationship and career questions, 12 for others),
finds every transit that comes within orb of a natal point, and returns
**windows with exact dates**. One entry, exactly as the model receives it:

```json
{
  "transit": "Saturn conjunction your Venus",
  "in_house": 1,
  "natal_rules_houses": [2],
  "importance": 0.85,
  "passes": [
    {"pass": "1 of 2", "window": "2026-09-23 to 2027-03-06",
     "exact": "2026-10-17", "strength": "exact", "retrograde": true},
    {"pass": "2 of 2", "window": "2026-09-23 to 2027-03-06",
     "exact": "2027-01-28", "strength": "exact", "retrograde": false}
  ]
}
```

It is grouped into `active_now`, `starting_soon` and `major_ahead`, plus
`moon_triggers` (single days that light up something already running).

**Every date in an answer must trace to one of these.** The standing
instructions say so explicitly, and tell the model never to soften a
calculated date into "sometime in the autumn".

---

## 4. The four length tiers (the thing to move away from)

The tiers exist in **three separate places**, which matters if they are to be
removed.

### (a) Described in the standing instructions

An abridged version of the section:

```
FOUR SIZES OF ANSWER. Decide which one you are writing before you write a word.
The emotional stakes of the question decide it — never the length of their
message.

TIER 1 — greetings, small talk, one word. "hi", "hey", "morning", "thanks".
One line. Warm, a little knowing. No reading, no follow-up question.

TIER 2 — a quick decision with low stakes. An outfit, a purchase, whether to
go out, what to eat.
The verdict lands inside the first three words. Then one short reason. Two
sentences at most, one if you can manage it.

TIER 3 — mid-thread, they already have an answer from you. "so yes??", "and
the boots", "wait really", "ok but".
One line. Rapid-fire is the entire point.

TIER 4 — the real ones. Heartbreak, love, whether he means it, work fear,
feeling stuck, "am I crazy for feeling this".
Three to four short paragraphs, never more, in this shape:
  1. A verdict on its own short line. "No. Not today."
  2. The reason it holds, in plain words.
  3. Close on a direction rather than a summary.
```

Note that TIER 4 already encodes most of the answer shape Martina wants —
verdict first, reason, next move. The missing piece in the current wording is
"name the real feeling underneath", which used to be there and was removed
earlier (it was the "mind-reading" step).

### (b) A sentence appended to every request

```python
TIER_DIRECTIVE = {
    1: "ANSWER AS TIER 1. One line. Warm, a little knowing. No reading, no "
       "list of what you can do, no follow-up question.",
    2: "ANSWER AS TIER 2. The answer lands inside the first few words, then "
       "one short reason. Two sentences at the absolute most, one is better. "
       "No paragraph of context, no chart tour.",
    3: "ANSWER AS TIER 3. They are mid-thread and already have your answer. "
       "Respond to the new detail only and add one thing they didn't have. A "
       "few sentences. Do not restart the reading or repeat the prior answer.",
    4: "ANSWER AS TIER 4. A real question that deserves a real answer: the "
       "answer, why it holds, and what to do with it. Room to breathe, but "
       "finish when you are done rather than filling the space.",
}
```

### (c) Enforced in code — a hard token ceiling

This is the part a fine-tuned model **cannot** override, and the part that
needs a decision before the tiers are removed.

```python
# app/conversation_service.py  — (provider tokens, review words)
BUDGETS = {1: (90, 75), 2: (130, 105), 3: (110, 90), 4: (550, 420)}
EXPLANATION_BUDGET = (620, 470)   # "wdym", "explain that", "why?"
DETAILED_BUDGET    = (760, 570)   # they asked for detail
RELOCATION_BUDGET  = (900, 690)   # a ranked list of cities
SOCIAL_BUDGET      = (60, 48)     # "hi", "thanks", "lol"
```

The first number is sent to the provider as `max_output_tokens` — the model is
physically stopped there. The second is a word limit checked after the fact by
the review step.

One provider-specific detail: **Claude counts its own thinking against
`max_tokens`**, so the Claude path adds headroom on top:

```python
# app/ai_service.py
THINKING_HEADROOM = 1800
ANTHROPIC_MAX_TOKENS = 4000
"max_tokens": min(max_output_tokens + THINKING_HEADROOM, ANTHROPIC_MAX_TOKENS)
```

OpenAI receives the ceiling directly, with no headroom.

### How the tier is chosen

`classify_tier()` in `question_router.py` decides from the text alone where it
can — greetings, low-stakes decisions, short mid-thread replies, emotionally
heavy wording, first-person statements. When it genuinely cannot tell, it
returns `None` and a **cheap model call** (`gpt-4.1-mini`) picks the tier
before the real answer is generated.

---

## 5. The review step (runs after the model answers)

`answer_review_service.py` inspects every draft. If it finds a problem, the
draft goes back to the model once with the problems listed, for a single
rewrite. This matters for fine-tuning because **these rules define what a
"good" answer is, mechanically** — a training set should produce answers that
pass all of them.

The full list of what it rejects:

```
answer ends mid-sentence
argues about what it said instead of answering
covers both branches, so nothing could contradict it
drops the calculated ranking it was asked to report
ends by asking them to supply what they asked about
narrates its own limits instead of answering
offers a menu of possibilities instead of one reading
provider stopped before the answer was complete
repeats a previous assistant sentence or conclusion
stock or poetic phrasing
technical astrology in an everyday reply
too long for this turn
too many paragraphs
unqualified claim about another person
unsupported age
unsupported gendered pronouns
unsupported personal fact: <children|marriage|pregnancy|employment|
                            finances|housing|health|orientation>
```

If the rewrite still fails on a **serious** problem — an invented fact about
someone's life, an unqualified claim about another person, wrong pronouns, or
a sentence that stops halfway — a stock safe reply is substituted instead.
Style problems alone no longer trigger that.

---

## 6. The captured example

Produced by `capture_request.py` in this folder, using a **fictional person**:

- **Ana Dimitrova**, born 2 March 1999, 07:15, Sofia, Bulgaria — invented
- Thread so far: *"we fought and honestly im done"* → *"Good. Say it."*
- New question: *"when is this thing with him actually going to come to a head?"*

Result:

```json
{
  "model_that_would_be_used": "gpt-4.1-mini",
  "answer_tier_chosen": 4,
  "max_output_tokens_allowed": 550,
  "system_half_characters": 17766,
  "user_half_characters": 27801,
  "ratio_data_to_instructions": 1.6
}
```

**About 45,000 characters go in. At most 550 tokens — roughly 410 words — come
out.**

The model's job is overwhelmingly one of *selection*: choose the two or three
things worth saying out of a great deal of data, then say them plainly. That
is the behaviour fine-tuning would be teaching, and it is why the written
instructions have grown to nearly eighteen thousand characters — every rule is
an attempt to steer that selection using words.

---

## 7. Two things to decide before Step 2

**1. What replaces the hard token ceiling.**
A fine-tuned model can learn length from examples and would no longer need the
tier sentence or the tier descriptions. But `max_output_tokens` is enforced in
code, outside the model's control, and would still cut a long answer off
mid-word. Options: keep a single generous ceiling for every answer; keep a
small number of ceilings chosen by the router; or keep the current ones and
let the model be shorter than allowed. This needs a decision.

**2. Whether the standing instructions shrink, and by how much.**
Fine-tuning's main benefit here would be replacing much of those 17,766
characters with learned behaviour — cheaper per request and more consistent.
But some of it is not style at all: the safety floor, the rules about not
inventing biography, and the "never promise another person's behaviour" rule
are liability protection. Those are probably worth keeping in the prompt even
after training, because a fine-tuned model can still drift and a written rule
is auditable.

---

## Companion files

| File | Contents |
|---|---|
| `01-system-half.txt` | The complete standing instructions, 17,766 characters |
| `02-user-half.txt` | The complete per-request block for the captured example |
| `03-summary.json` | Sizes, tier, model, ceiling |
| `capture_request.py` | The script that produced them — reads only, makes no network calls |
