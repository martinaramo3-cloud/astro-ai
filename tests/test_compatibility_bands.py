"""Bands cut from what the engine actually produces, not from guessed numbers.

The old thresholds put "obsessive" at 21 and "toxic" at 13. Measured against a
thousand fictional pairs, the tenth percentile for attraction is 23 and for
toxicity 18.5 — so almost every pair cleared both, and 95.8% of all couples
were classified a "toxic attraction". The label fired for nearly every two
people alive, which made it meaningless and, to the person reading it, untrue.
"""
import pytest

from app.compatibility_service import RULES, _bucketize_index, _classify_relationship


def test_every_index_is_banded():
    """Only attraction and toxicity had bands; emotional and long_term were
    computed and then never described. Friendship joined them as its own axis."""
    assert set(RULES["index_thresholds"]) == {
        "attraction", "emotional", "long_term", "toxicity", "friendship"}


@pytest.mark.parametrize("index, value, band", [
    # Percentiles of 1,000 fictional pairs.
    ("attraction", 20.0, "low"), ("attraction", 38.5, "typical"),
    ("attraction", 52.0, "high"), ("attraction", 80.0, "exceptional"),
    ("toxicity", 18.0, "low"), ("toxicity", 36.0, "typical"),
    ("toxicity", 55.0, "high"), ("toxicity", 90.0, "exceptional"),
    ("emotional", 2.0, "low"), ("emotional", 12.5, "typical"),
    ("long_term", 1.0, "low"), ("long_term", 10.0, "typical"),
])
def test_bands_sit_where_the_data_sits(index, value, band):
    assert _bucketize_index(index, value) == band


def test_a_median_pair_is_not_remarkable():
    """The median pair used to come out obsessive and toxic."""
    median = {"attraction": 38.5, "emotional": 12.5, "long_term": 10.0, "toxicity": 36.2}
    assert _bucketize_index("attraction", median["attraction"]) == "typical"
    assert _bucketize_index("toxicity", median["toxicity"]) == "typical"
    assert _classify_relationship(median) == ["nothing that stands out either way"]


def test_high_pull_with_high_friction_is_now_rare():
    """It needs the top quarter for attraction and the top tenth for friction —
    about 5% of pairs, not 96%."""
    ordinary = {"attraction": 38.5, "emotional": 12.5, "long_term": 10.0, "toxicity": 36.2}
    assert "high pull with high friction" not in _classify_relationship(ordinary)
    extreme = {"attraction": 60.0, "emotional": 12.5, "long_term": 10.0, "toxicity": 70.0}
    assert "high pull with high friction" in _classify_relationship(extreme)


def test_every_matching_description_is_kept():
    """A pair can have real long-term potential and real friction. Returning
    whichever was listed first threw away half the reading."""
    both = {"attraction": 55.0, "emotional": 20.0, "long_term": 20.0, "toxicity": 65.0}
    matched = _classify_relationship(both)
    assert "strong relationship potential" in matched
    assert "high pull with high friction" in matched
    assert isinstance(matched, list)


def test_no_label_calls_anybody_toxic():
    """Describe the friction, never label the people."""
    for classifier in RULES["classifiers"].values():
        assert "toxic" not in classifier["label"].lower(), classifier["label"]


def test_eighth_house_is_depth_not_a_point_in_its_favour():
    """Intensity says how deep an exchange goes, not whether it is enjoyable,
    mutual or sustainable."""
    assert not any("8th" in flag for flag in RULES["green_flags"])
    assert any("8th" in marker for marker in RULES["neutral_markers"])


# ── An ordinary pair still gets a specific reading ─────────────────────────

from app.compatibility_service import _relative_shape  # noqa: E402


@pytest.mark.parametrize("indices, leads", [
    ({"attraction": 32, "emotional": 19, "long_term": 8, "toxicity": 30}, "emotional closeness"),
    ({"attraction": 31, "emotional": 9, "long_term": 16, "toxicity": 28}, "staying power"),
    ({"attraction": 46, "emotional": 8, "long_term": 6, "toxicity": 30}, "pull and chemistry"),
])
def test_four_in_five_pairs_still_have_something_to_be(indices, leads):
    """81.9% of pairs now classify as "nothing that stands out". Without a
    relative read, that becomes "it could be anything" — the one thing a
    reading must never be."""
    assert _relative_shape(indices)["leads_on"] == leads


def test_friction_is_never_offered_as_a_strength():
    """A high friction score is not something a pair is good at, and leading
    with it turns an ordinary connection into a warning."""
    shape = _relative_shape({"attraction": 20, "emotional": 5, "long_term": 3, "toxicity": 100})
    assert shape["leads_on"] != "friction"
    assert shape["leads_on_key"] in ("attraction", "emotional", "long_term")


def test_a_level_pair_is_described_as_level():
    shape = _relative_shape({"attraction": 38, "emotional": 12, "long_term": 10, "toxicity": 36})
    assert shape["spread"] < 0.2, "these three are genuinely even, and that is the description"


# ── What must never be said out loud ───────────────────────────────────────

from app.answer_review_service import review_issues  # noqa: E402
from app.conversation_service import conversation_state  # noqa: E402


def _state():
    # The question names him, so "he" in an answer is supported — otherwise the
    # pronoun rule fires and masks what these tests are actually checking.
    state = conversation_state("is he a friend or something else?")
    state["max_words"] = 420
    return state


@pytest.mark.parametrize("draft", [
    "This reads as a toxic attraction between you.",
    "The pull is obsessive.",
    "Your net_score is high.",
    "He is the power_holder here.",
])
def test_internal_scoring_words_never_reach_the_reader(draft):
    assert 'says an internal scoring label out loud' in review_issues(draft, _state())


@pytest.mark.parametrize("draft", [
    "Wait for him to call first.",
    "Don't text him back too quickly.",
    "Let him come to you.",
    "Play it cool for a week.",
])
def test_dating_game_advice_is_rejected(draft):
    assert 'gives dating-game advice instead of something to notice' in review_issues(draft, _state())


@pytest.mark.parametrize("draft", [
    "Wait until Thursday — the window opens then.",
    "It goes hot then cold, and the cold part always follows a real conversation.",
    "Notice whether he keeps the contact going when you are not the one starting it.",
])
def test_real_timing_and_real_observations_still_pass(draft):
    """The line is between a rule for managing someone's interest and a fact
    about when something happens."""
    assert review_issues(draft, _state()) == []


def test_power_and_attachment_never_leave_the_engine():
    """Who 'holds the power' is internal scoring, and the charts cannot
    establish it anyway."""
    import inspect
    import app.main as main
    source = inspect.getsource(main.ask_compatibility)
    assert '"power_profile"' in source and '"attachment_profile"' in source
    assert "not in (" in source, "they should be filtered out of the context"


def test_a_rejected_pronoun_is_rewritten_as_a_name(account):
    """A live test collapsed to the stock apology because the draft said "he"
    about someone whose gender was never stated. The reading was fine; only the
    pronoun was an assumption — so the rewrite is told what to call them."""
    from app.answer_review_service import reviewed_answer
    state = conversation_state("what is this connection actually like?",
                               None, {"user": {"name": "Ana"}})
    state["max_words"] = 420
    state["their_name"] = "Sam"
    seen = []

    def generate(prompt, **kwargs):
        seen.append(prompt)
        return (("The pull is the loudest part, and he goes quiet after closeness.", 10)
                if len(seen) == 1 else
                ("The pull is the loudest part, and Sam goes quiet after closeness.", 10))

    answer, _ = reviewed_answer(generate, "prompt", {"conversation": state})
    assert "Sam" in answer and "reliable information" not in answer
    assert "refer_to_them_as" in seen[1] and "Sam" in seen[1]


def test_the_last_resort_answers_the_question_that_was_asked():
    """It used to ask what the other person had said or done — an answer about
    intentions, to someone asking about two charts."""
    from app.answer_review_service import safe_reply
    state = conversation_state("what is this connection actually like?")
    state["topic"] = "compatibility"
    assert "what have they actually said" not in safe_reply(state).lower()
    assert "connection between the two charts" in safe_reply(state)
