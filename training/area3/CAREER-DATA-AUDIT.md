# What Zoli actually sees when someone asks about career or money

For the astrologer. A list of what the engine calculates and hands to the
writing step today, what it leaves out, and a column for you to say what is
worth adding and what matters most.

Nothing here is about how the answers are *written* — only about what the
writing step has in front of it. If a technique is not in Table A, no amount
of prompting can make an answer use it.

**How to mark it up.** In Tables B and C, fill in the last two columns:

- **Worth adding?** — yes / no / later
- **Rank** — 1 for the thing you would add first, then 2, 3…

Anything you mark 1–3 gets built next.

---

## Table A — what reaches a career or money question today

Every one of these is calculated from the real birth chart and sent on every
career question, provided we have a birth time.

| What it is, in plain language | What it contains |
|---|---|
| The sign on the career point | Midheaven sign and exact degree |
| The rising sign | Ascendant sign and exact degree |
| Every planet, with its house | All 10 planets plus North Node and Chiron: sign, degree, house, retrograde |
| **Rulers of all twelve houses** | For each house: the sign on its cusp, its ruler, and the sign, house and dignity of that ruler. So "what rules the money house and where it went" is there for all twelve |
| Which planets are angular | Angular vs cadent, plus any planet conjunct the Ascendant or Midheaven with its orb |
| Dignities | Domicile, exaltation, detriment, fall, for whichever planets have one |
| Sect | Day or night chart, with the benefic and malefic of sect named |
| Chart ruler | The Ascendant ruler, its sign, house and dignity |
| Aspect patterns | Stelliums, t-squares, grand trines, and which houses or planets they involve |
| Element and modality balance | Counts per element and modality, dominant element, missing elements |
| Moon phase at birth | Phase name and illumination |
| Lunar nodes | North and South Node by sign and house |
| The career planets, picked out | For a career question specifically: Sun, Mercury, Mars, Jupiter, Saturn are pulled forward as "relevant". **Venus and the Moon are not** |
| The tightest natal aspects | The four closest aspects between planets, with orbs |
| Current transits | Every current transit to a natal planet — about 27 of them — with exact orbs |
| **Timed windows, 24 months ahead** | Real start and end dates plus the exact day of each pass, searched two years out for career. Retrograde loops are kept together as one transit with several passes. Each window says which houses the natal planet rules |
| Which house each transiting planet is crossing | The area of life a transit is currently playing out in |
| A computed "what is active" summary | Main topic, tone, whether it looks like a process or an event, the strongest window, and the engine's own reasoning for why |
| Where the current sky is | Moon sign, what is retrograde, the next notable sky events |
| What they have told Zoli before | At most one remembered fact or plan per answer |

**Houses are Placidus and rulerships are traditional.** Both are fixed in the
code right now; say if either should change.

---

## What the three test answers actually used

Traced from the three answers Martina tested, not from logs — so this is a
reading of the evidence rather than a recording.

All three answers rested on the same three things:

| The point that kept coming back | Where it came from |
|---|---|
| "Your name visibly attached to the work" | The career point and the planets on the angles |
| "Late October to late January" | **One** timed window — the top entry in the two-year list |
| A memory about a country she never mentioned | The memory store |

On the test chart, the strongest window computed is a Saturn transit exact on
**17 October 2026** and again on **31 January 2027**. That is "late October to
late January" precisely — so all three answers appear to have led with the
same single window from a two-year list, and then built the rest of the answer
around it.

So the recycling is real, but it is not a shortage of data. Everything in
Table A was available all three times. The answer led with the loudest transit
each time and never went past it. Two things are being fixed for that: answers
now have to open ground the thread has not already covered, and only one
memory reaches an answer at all.

The question for you is a different one: **is what Table A contains the right
material for a career reading in the first place?** That is Tables B and C.

---

## Table B — the natal side

| Technique | Status | Note | Worth adding? | Rank |
|---|---|---|---|---|
| Midheaven sign and degree | **Sent** | | | |
| **Ruler of the Midheaven, and where it sits** | **Sent** | Inside the full house-ruler table: its sign, house and dignity are all there | | |
| Rulers of the 2nd, 6th, 8th, 10th | **Sent** | Same table, all twelve houses | | |
| Planets sitting in the 2nd, 6th, 8th, 10th | **Sent, but not grouped** | Every planet carries its house number, so it is derivable — nothing hands over "here is what is in the money houses" as a set | | |
| **Aspects to the Midheaven** | **Now calculated** | Was the largest hole; built 25 September 2026 in `app/angle_aspects_service.py` for the earning-route engine. Not yet in ordinary answers | | |
| Aspects to the Ascendant | **Now calculated** | Same change. Descendant and IC too, which were never stored at all | | |
| Planets *conjunct* the angles | **Sent** | Conjunctions only, within 8° | | |
| Jupiter and Saturn by sign, house, dignity | **Sent** | | | |
| North Node by sign and house | **Sent** | | | |
| **Part of Fortune** | **Not calculated** | Absent from the codebase entirely | | |
| Other Arabic Parts (Spirit, Substance) | **Not calculated** | | | |
| Dignity beyond domicile/exaltation/detriment/fall | **Not calculated** | No terms, triplicities, faces or decans | | |
| Almuten of the chart or of the 10th | **Not calculated** | | | |
| Fixed stars on the angles or the MC | **Not calculated** | | | |
| Antiscia | **Not calculated** | | | |
| Sect | **Sent** | | | |
| Whether a planet is combust, cazimi or under the beams | **Not calculated** | | | |
| Retrograde status at birth | **Sent** | | | |
| House system | **Placidus, fixed** | Not configurable | | |
| Rulership system | **Traditional, fixed** | Not configurable | | |

---

## Table C — the timing side

| Technique | Status | Note | Worth adding? | Rank |
|---|---|---|---|---|
| Transits to natal planets | **Sent** | Windows with real dates, 24 months out for career, retrograde passes kept together | | |
| Transits through the natal houses | **Sent** | | | |
| **Transits to the Midheaven or Ascendant** | **Partly** | The angles are included as points to transit, so a transit *to* the MC is found — but see Table B: natal aspects to the MC are not, so the chart's own promise about it is missing | | |
| **Secondary progressions** | **Not calculated** | The prediction engine has a slot named "progression" with a weight attached to it. Nothing ever fills that slot from a real chart | | |
| **Solar return charts** | **Not calculated for a career question** | Solar returns exist only inside the "where should I live" feature, for comparing cities. A person's own solar return is never read | | |
| Lunar returns | **Not calculated** | Slot exists, never filled | | |
| **Annual profections** | **Not calculated** | Same: the engine will boost a transit that lands on the profected house, and knows what to do with a time lord — but nothing ever works out which house or which lord, so that boost has never once applied to a real person | | |
| Zodiacal releasing | **Not calculated** | | | |
| Firdaria | **Not calculated** | | | |
| Saturn return, specifically flagged | **Not flagged** | It appears as an ordinary transit, with no special weight | | |
| Jupiter return | **Not flagged** | Same | | |
| Eclipses on career points | **Partly** | Upcoming eclipses reach the answer as sky events; nothing checks whether one lands on the career point | | |

---

## The three that look most consequential

Ours, not yours — argue with them.

1. **Aspects to the Midheaven are not calculated at all.** For a career
   reading this seems like the largest single hole: the career point has a
   sign and a ruler, but nothing about what aspects it. A planet squaring the
   MC is invisible to the whole system.

2. **Profections are scaffolded but never computed.** The engine is already
   written to raise the weight of a transit landing on the profected house,
   and to recognise a time lord. Both are dead code because nothing works out
   the profected house from a birth date. This may be the cheapest real
   addition on the list.

3. **Nothing ranks earning patterns.** Now superseded by your own framework:
   `training/area3/blind_routes.html` implements the six routes and the weight
   table, calibrated against a thousand invented charts and switched off until
   you have reviewed the blind table.

---

*Placidus houses, traditional rulerships. Every chart used in testing is
invented — random dates, times and cities — except Martina's own test account.*
