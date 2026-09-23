"""Regressions from the September feedback. All provider calls are stubbed.

These verify data and routing, not whether a model writes a good answer.
"""
from datetime import datetime, timezone

import pytest

import app.ai_service as ai
import app.main as main
import app.transit_service as transits
import app.transit_timing_service as timing
from app.question_router import classify_question, classify_tier, conversational_cue
from tests.conftest import SOFIA


HISTORY = [
    {"role": "user", "content": "When will my next relationship become official?"},
    {"role": "assistant", "content": "Saturn is activating your relationship ruler."},
]


@pytest.mark.parametrize("message, cue", [
    ("\\", "possible_mistype"),
    ("\\\\", "possible_mistype"),
    ("HAHAHAA", "shared_laughter"),
    ("hahahahaha!!", "shared_laughter"),
    ("LMAOOO", "shared_laughter"),
    ("😂😂", "shared_laughter"),
])
def test_social_signals_get_a_brief_reply_even_without_history(message, cue):
    assert conversational_cue(message) == cue
    assert classify_tier(message, []) == 1


@pytest.mark.parametrize("message", [
    "?", "...", "😭", "why?", "haha I'm actually really hurt",
    "HAHA should I text my ex?", "what does / mean?", "C:\\Users\\name",
])
def test_meaningful_messages_are_not_reduced_to_laughter_or_a_mistype(message):
    assert conversational_cue(message) is None
    assert classify_tier(message, HISTORY) != 1


@pytest.mark.parametrize("message", ["\\", "HAHAHAA", "hey"])
def test_social_reply_keeps_history_without_forcing_chart_data(client, account, message):
    user, headers = account()
    response = client.post("/ask-astrologer", headers=headers, json={
        **SOFIA, "user_id": user["id"], "question": message, "history": HISTORY,
    })
    assert response.status_code == 200
    context = response.json()["context"]
    assert context["history"] == HISTORY
    assert context["answer_tier"] == 1
    assert context["conversation_cue"] == conversational_cue(message)
    assert "sky_now" not in context
    assert "personal_planets" not in context
    assert "predictive_timeline" not in context


@pytest.mark.parametrize("question", [
    "wdym", "I don't understand", "I dont understand", "what does that mean?",
    "why?", "how?", "what happened?", "use simpler language",
    "be more detailed ure being vague!", "tell me how, who, what",
    "who is the person that I'm going to date?", "rank European cities for my solar return",
])
def test_explanations_keep_full_context(question):
    assert classify_tier(question, HISTORY) == 4
    assert main.answer_ceiling(question, 4) > main.ANSWER_CEILING[4]


@pytest.mark.parametrize("question, expected", [
    ("What should I focus on this month?", "general"),
    ("Will my business become profitable?", "career"),
    ("Explain that", "general"),
    ("Tell me about us", "compatibility"),
    ("When will my love life change?", "relationship"),
])
def test_topics_match_words_not_fragments(question, expected):
    assert classify_question(question) == expected


@pytest.mark.parametrize("question, tier", [("hi", 1), ("buy the jacket?", 2), ("so yes??", 3)])
def test_small_answers_keep_existing_ceilings(question, tier):
    assert classify_tier(question, HISTORY) == tier
    assert main.answer_ceiling(question, tier) == main.ANSWER_CEILING[tier]


def test_clarification_keeps_the_chart_and_conversation_topic(client, account, monkeypatch):
    seen = {}
    def generate(prompt, **kwargs):
        seen.update(kwargs)
        return "A plain explanation.", 25
    monkeypatch.setattr(main, "generate_astrologer_answer", generate)
    user, headers = account()
    response = client.post("/ask-astrologer", headers=headers, json={
        **SOFIA, "user_id": user["id"], "question": "wdym", "history": HISTORY,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["answer_tier"] == 4
    assert result["question_type"] == "relationship"
    assert result["context"]["chart_structure"]["house_rulers"]
    assert result["context"]["personal_planets"]
    assert seen["max_output_tokens"] == main.DETAIL_CEILING["explanation"]


@pytest.mark.parametrize("images", [None, [{"content": b"test", "content_type": "image/png"}]])
def test_stream_endpoint_passes_the_same_ceiling(client, monkeypatch, images):
    seen = []
    monkeypatch.setattr(main, "_prepare_astrologer_call", lambda *args: {
        "chat_context": {"question": "wdym", "answer_tier": 4},
        "model": "test", "effort": None, "images": images, "user_id": 1,
        "image_tokens": 0, "max_output_tokens": 900,
        "question_type": "general", "tier_config": {"label": "test"},
    })
    monkeypatch.setattr(main, "record_usage", lambda *args: None)
    def generate(prompt, **kwargs):
        seen.append(kwargs["max_output_tokens"])
        return "Explanation.", 10
    monkeypatch.setattr(main, "generate_astrologer_answer", generate)
    main.app.dependency_overrides[main.get_current_user] = lambda: {"id": 1}
    try:
        response = client.post("/ask-astrologer/stream", json={**SOFIA, "question": "wdym"})
    finally:
        main.app.dependency_overrides.pop(main.get_current_user, None)
    assert response.status_code == 200
    assert "event: done" in response.text
    assert seen == [900]


def test_openai_stream_uses_the_requested_ceiling(monkeypatch, account):
    user, _ = account()
    seen = []
    def stream(prompt, model, ceiling, usage):
        seen.append(ceiling)
        yield "Text"
    monkeypatch.setattr(ai, "_stream_openai", stream)
    assert list(ai.stream_astrologer_answer("Explain", max_output_tokens=900, user_id=user["id"])) == ["Text"]
    assert seen == [900]


def test_relationship_timing_searches_both_people_and_communication(monkeypatch):
    seen = []
    monkeypatch.setattr(transits, "get_current_transit_positions", lambda: [])
    monkeypatch.setattr(transits, "get_transit_aspects", lambda **kw: [])
    def upcoming(points, **kwargs):
        seen.append((points, kwargs["focus_planets"]))
        return [{"starts": "2026-09-20", "fades": "2026-09-23", "peaks": "2026-09-21",
                 "transit_planet": "Venus", "aspect": "trine", "natal_planet": "Mercury", "peak_orb": 0.1}]
    monkeypatch.setattr(transits, "build_upcoming_transit_timeline", upcoming)
    result = transits.build_relationship_timing([{"planet": "Sun"}], [{"planet": "Moon"}], [])
    assert len(seen) == 2
    assert all("Mercury" in focus for _, focus in seen)
    assert "your Mercury" in result["upcoming_for_you"][0]["what"]
    assert "their Mercury" in result["upcoming_for_them"][0]["what"]


def test_relationship_ruler_window_survives_timeline_trimming(monkeypatch):
    def cycle(point, importance):
        return {"natal_point": point, "natal_house": 6, "importance": importance,
                "transit_planet": "Saturn", "aspect": "trine", "note": "",
                "passes": [{"starts": "2026-09-01", "ends": "2026-09-30",
                            "exact": "2026-09-20", "pass": 1, "of": 1,
                            "strength": "strong", "retrograde": False}]}
    # Mercury is not a default love target, but here it rules the seventh.
    monkeypatch.setattr(timing, "find_transit_cycles", lambda *a, **kw: [
        cycle("Pluto", 100), cycle("Neptune", 90), cycle("Mercury", 50),
    ])
    monkeypatch.setattr(timing, "moon_triggers", lambda *a, **kw: [])
    result = timing.build_predictive_timeline(
        [], "relationship", datetime(2026, 9, 15, tzinfo=timezone.utc),
        limit=2, rules_by_point={"Mercury": [7]},
    )
    first = result["active_now"][0]
    assert "Mercury" in first["transit"]
    assert first["natal_rules_houses"] == [7]


@pytest.mark.parametrize("question, tier", [
    ("should I buy the next size up?", 2),
    ("should I book the trip next week?", 2),
    ("is this coffee place expensive?", 2),
    ("should we go out tonight?", 2),
])
def test_ex_does_not_match_inside_other_words(question, tier):
    """"ex" is a former partner, not the letters in "next", "text", "exam" and
    "expensive". Substring matching sent every one of these to the deepest and
    most expensive tier."""
    assert classify_tier(question, HISTORY) == tier


@pytest.mark.parametrize("question", [
    "should I text him tonight?", "should I reach out to my ex?", "am I crazy for feeling this",
])
def test_genuinely_heavy_questions_still_reach_tier_four(question):
    assert classify_tier(question, HISTORY) == 4


def test_the_prompt_still_explains_how_to_answer_when():
    """The timing engine searches two years ahead and returns real windows with
    exact dates. It was still being sent to the model after a prompt rewrite
    removed every instruction about what it was — so the data arrived and the
    answers went back to having no dates in them at all. The engine being wired
    up is not the same as the model knowing what to do with it."""
    from app.ai_context_service import build_ask_astrologer_system
    prompt = build_ask_astrologer_system()
    for key in ("predictive_timeline", "active_now", "starting_soon",
                "major_ahead", "moon_triggers", "transits_on_asked_date"):
        assert key in prompt, f"nothing tells the model what {key} is"
    # Collapsed, because the prompt is hard-wrapped and the phrase spans lines.
    flat = " ".join(prompt.lower().split())
    assert "sometime in the autumn" in flat, "the rule against softening a date is gone"
    assert "importance" in flat


def test_the_timeline_reaches_two_years_for_the_questions_that_need_it():
    from app.transit_timing_service import HORIZON_MONTHS
    assert HORIZON_MONTHS["relationship"] >= 24
    assert HORIZON_MONTHS["career"] >= 24


@pytest.mark.parametrize("statement", [
    "I feel so close to new york and the US overall ever since I was younger",
    "we faught and honestly im done",
    "i tend to confuse not chasing with being mean lol",
    "im so good with my ex right now its weird",
    "I was updating him about my day and he ignored me",
])
def test_telling_it_about_yourself_gets_a_real_answer(statement):
    """Almost none of these arrive with a question mark, so nothing in the text
    asks for an answer — and they were getting eighty words of agreement. This
    is how the conversations the app exists for actually open."""
    assert classify_tier(statement, HISTORY) == 4


@pytest.mark.parametrize("small", [
    ("i want the black boots tonight", 2),
    ("is this jacket a mistake?", 2),
    ("so yes??", 3),
    ("and the boots", 3),
    ("hi", 1),
    ("thanks", 1),
])
def test_small_things_stay_small(small):
    """A first-person sentence about an outfit is still an outfit. The rule sits
    after the low-stakes check for exactly this reason."""
    question, tier = small
    assert classify_tier(question, HISTORY) == tier
