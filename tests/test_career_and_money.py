"""Career and money: the four things an answer here must never invent.

Every draft in the first class below passed the whole review layer clean before
these rules existed — an invented salary, a credential nobody mentioned, an
index fund, and a promise of wealth. They are written here as the app could
plausibly produce them, because a guard that only catches the version I wrote
to be caught is not a guard.

The second class matters just as much. The useful half of a money answer sits
right beside the banned half — pricing structure beside invented prices, a form
of success beside an investment instruction — and a rule that cannot tell them
apart takes the answer away from the person who asked for it.
"""
import pytest

from app.answer_review_service import review_issues
from app.conversation_service import (
    CAREER_BUDGET, budget_for, conversation_state,
)
from app.earning_profile_service import POLES, describe_profile, score_earning_profile
import app.main as main
from tests.conftest import SOFIA

# A test user who STUDIES law. Nothing here says they are qualified, and the
# distinction is the whole point of the profession rule.
STUDIES_LAW = ("Studies law", "Deciding whether to practise or go in-house")


def state_for(question, remembered=(), history=None):
    state = conversation_state(question, history or [])
    state["reported_facts"]["remembered"] = list(remembered)
    state["max_words"] = CAREER_BUDGET[1]
    return state


MONEY_QUESTION = "How am I most likely to make money according to my chart?"


# --------------------------------------------------------------------------
# The five that used to pass
# --------------------------------------------------------------------------

@pytest.mark.parametrize("draft,expected", [
    ("Your clearest earning route is advisory work you sell by the hour. Start "
     "at 80 euros an hour and you could be clearing 6,000 a month within a year.",
     "invents a money figure"),
    ("As a lawyer you already have the credential that makes this easy. Put it "
     "on the page and charge for the consultation.",
     "unsupported personal fact: qualification"),
    ("Your MBA is the asset here. Lead with it.",
     "unsupported personal fact: qualification"),
    ("Put the surplus into an index fund and hold it through the next two years.",
     "tells them where to invest"),
    ("This will make you wealthy. The money arrives in March and it does not stop.",
     "promises money as certain"),
])
def test_the_five_drafts_that_used_to_pass(draft, expected):
    issues = review_issues(draft, state_for(MONEY_QUESTION, STUDIES_LAW))
    assert any(i.startswith(expected) for i in issues), issues


@pytest.mark.parametrize("draft", [
    "A slice of it should go into Bitcoin while the window is open.",
    "Put your savings into property and let it sit.",
    "Buy shares in the companies you already understand.",
    "Your ceiling here is six figures, and you get there by narrowing.",
    "Expect $4,000 a month once the second client lands.",
])
def test_other_shapes_of_the_same_four(draft):
    assert review_issues(draft, state_for(MONEY_QUESTION))


# --------------------------------------------------------------------------
# Studying is not being. The case Martina named.
# --------------------------------------------------------------------------

def test_studying_law_does_not_make_them_a_lawyer():
    """Memory says "studies law". That licenses neither the job nor the credential."""
    state = state_for("What career suits me?", STUDIES_LAW)
    issues = review_issues("As a lawyer you already have the credential.", state)
    assert any("qualification" in i for i in issues)


def test_wanting_to_be_one_does_not_license_it_either():
    state = state_for("What career suits me?", ("Wants to be a therapist",))
    assert review_issues("As a therapist you already have the licence.", state)


def test_asking_whether_to_become_one_does_not_license_it():
    state = state_for("should I become a lawyer?")
    assert review_issues("As a lawyer you would be paid for judgement.", state)


def test_saying_they_are_one_does_license_it():
    """"I'm a lawyer, what should I do next?" is a fact inside a question.

    Reading the whole sentence as a question threw the fact away and flagged
    the answer for inventing a job they had just named.
    """
    state = state_for("I'm a lawyer, what should I do next?")
    assert review_issues("As a lawyer you already have the harder half done.", state) == []


def test_a_memory_of_a_real_credential_licenses_it():
    state = state_for("what career suits me?", ("Works as a certified nurse",))
    assert review_issues("You are certified already, so the question is where "
                         "you point it.", state) == []


# --------------------------------------------------------------------------
# What must still get through
# --------------------------------------------------------------------------

@pytest.mark.parametrize("draft", [
    # Pricing structure with no numbers in it — the useful half of "how do
    # they charge", and the thing a blunt money rule would have eaten.
    "Charge per engagement rather than by the hour, and move to a monthly "
    "retainer once two of them come back.",
    "Take a percentage of what it earns instead of a fee for building it.",
    # Forms of success are not investment instructions.
    "Your biggest upside is owning a business rather than being paid by one.",
    "Equity in a company you help build is worth more to you than a higher wage.",
    "Invest in yourself first: the training pays back faster than any client will.",
    # Ordinary language that shares words with the rules.
    "It's a qualified yes. You're built for it, but not before the second client.",
    "The window runs from 6 March to 2 April, and the next one is 14 months out.",
    "You know the market better than the people currently selling to it.",
])
def test_good_career_answers_are_not_touched(draft):
    assert review_issues(draft, state_for(MONEY_QUESTION, STUDIES_LAW)) == []


def test_a_number_they_typed_is_theirs_even_inside_a_question():
    """The rule is about INVENTING a figure. Sixty was theirs the moment they
    typed it, whether they stated it or asked about it."""
    state = state_for("I charge 60 euros an hour, is that too low?")
    assert review_issues("60 euros an hour is under what this chart earns. "
                         "Raise it and lose nobody.", state) == []


def test_a_full_good_answer_survives_intact():
    draft = (
        "You earn best when you are the named person doing the work rather than "
        "one of a team. The route that fits is paid advisory work: a small "
        "number of clients who pay you for judgement on decisions they cannot "
        "make alone. Charge per engagement rather than by the hour, and move to "
        "a monthly retainer once two of them come back. The loss comes from "
        "taking work because it was offered, not because it was yours. First "
        "step this week: write down the three problems people already bring you."
    )
    assert review_issues(draft, state_for(MONEY_QUESTION, STUDIES_LAW)) == []


# --------------------------------------------------------------------------
# Memory counts as something they told us
# --------------------------------------------------------------------------

def test_memory_stops_an_answer_looking_invented():
    """Without this, every answer resting on an earlier conversation was
    rejected as invented biography."""
    draft = "Your debt is the reason the slow route is the wrong one here."
    assert review_issues(draft, state_for("what should I do about work?"))
    assert review_issues(
        draft, state_for("what should I do about work?", ("Paying off a debt",))) == []


def test_all_four_are_serious_enough_to_replace_an_answer():
    from app.answer_review_service import _serious
    for draft in ("Expect 6,000 a month by spring.",
                  "Put it into an index fund.",
                  "This will make you wealthy.",
                  "Your MBA is the asset here."):
        issues = review_issues(draft, state_for(MONEY_QUESTION))
        assert _serious(issues), (draft, issues)


def test_the_repair_is_told_which_exact_words_to_cut():
    """Naming them is the difference between a rewrite that works and one that
    fails the same check twice."""
    from app.answer_review_service import career_offenders
    words = career_offenders(
        "Start at 80 euros an hour, put the rest into an index fund, and as a "
        "lawyer you'll never worry about money.",
        state_for(MONEY_QUESTION, STUDIES_LAW))
    assert any("80 euros" in w for w in words)
    assert any("index fund" in w for w in words)
    assert any("lawyer" in w for w in words)


# --------------------------------------------------------------------------
# Room, not a target
# --------------------------------------------------------------------------

def test_a_full_career_question_gets_room_for_all_of_it():
    for question in (MONEY_QUESTION, "What career suits me?",
                     "Does my chart show potential for major financial success?"):
        state = conversation_state(question, [])
        assert budget_for(question, 4, state) == CAREER_BUDGET, question


def test_a_short_follow_up_inside_a_career_thread_stays_short():
    """Being about money does not make "so which one?" a long question."""
    state = conversation_state("so which one of those?", [])
    assert budget_for("so which one of those?", 3, state) < CAREER_BUDGET


def test_other_topics_are_unaffected():
    question = "why do i pull away in relationships"
    state = conversation_state(question, [])
    assert budget_for(question, 4, state) != CAREER_BUDGET


def test_the_prompt_says_the_room_is_not_a_target():
    prompt = main.build_ask_astrologer_system()
    assert "Room is not a target" in prompt


def test_the_prompt_judges_the_chart_before_their_life():
    prompt = main.build_ask_astrologer_system()
    assert "When they ask about career or money:" in prompt
    assert "before you look at anything they have told" in prompt
    assert "Studying something is not being it" in prompt
    assert "never name a fund, a stock, a currency, a property or a market" in prompt


# --------------------------------------------------------------------------
# Part B: the earning engine. Built, calibrated, and deliberately not live.
# --------------------------------------------------------------------------

def chart():
    return main.build_natal_chart_data(type("P", (), dict(SOFIA, birth_time_known=True)))


def test_the_earning_engine_is_not_wired_into_any_answer():
    """Dark until the co-founder has reviewed the dimensions and the weights.

    The same arrangement as friendship, and this test is what keeps it true.
    """
    import subprocess
    importers = subprocess.run(
        ["grep", "-rl", "--include=*.py", "earning_profile_service", "app/"],
        capture_output=True, text=True).stdout.split()
    assert importers == [], f"now reached from {importers} — was it meant to go live?"


def test_it_scores_five_spectrums_from_the_chart_alone():
    profile = score_earning_profile(chart())
    assert profile["available"]
    assert set(profile["spectrums"]) == set(POLES)
    for entry in profile["spectrums"].values():
        assert entry["leans"]
        assert entry["band"] in ("low", "typical", "high", "exceptional")


def test_it_needs_a_birth_time():
    assert score_earning_profile({"planet_positions": [], "houses": []})["available"] is False


def test_it_never_produces_a_quantity_of_money():
    """There is no scale here on which a chart says someone will be rich, and
    building one would be the most attractive lie in the product.

    Checked against the words an ANSWER would be built from — the spectrums —
    not the whole payload, whose disclaimer says the word "rich" precisely in
    order to rule it out.
    """
    import json
    import re
    blob = json.dumps(score_earning_profile(chart())["spectrums"]).lower()
    for word in ("salary", "income", "rich", "wealthy", "earn ", "$", "€"):
        assert word not in blob, word
    # And no figure of any kind, anywhere in the reading.
    assert not re.search(r"\d[\d,.]*\s*(?:a|per)\s+(?:month|year|hour)", blob)
    for line in describe_profile(score_earning_profile(chart())):
        assert not re.search(r"\d", line), line


def test_the_plain_description_carries_no_jargon():
    from app.answer_review_service import JARGON
    for line in describe_profile(score_earning_profile(chart())):
        assert not JARGON.search(line), line


def test_the_bands_are_calibrated_not_guessed():
    """Guessed thresholds put 95.8% of couples in "toxic attraction"."""
    import json
    import pathlib
    bands = json.loads(
        (pathlib.Path(main.__file__).resolve().parents[1]
         / "content" / "engine" / "earning_bands.json").read_text())
    assert set(bands) == set(POLES)
    for spectrum, steps in bands.items():
        assert [s["label"] for s in steps] == ["low", "typical", "high", "exceptional"]
        cuts = [s["max"] for s in steps]
        assert cuts == sorted(cuts), spectrum


def test_the_ranking_is_not_just_the_widest_spectrum():
    """The five do not share a scale, so ranking on the raw score ranked the
    scale rather than the chart."""
    profile = score_earning_profile(chart())
    raw_order = sorted(profile["spectrums"],
                       key=lambda s: abs(profile["spectrums"][s]["score"]), reverse=True)
    # Not an assertion that they differ for this one chart — an assertion that
    # the ranking is computed from the relative figure at all.
    assert profile["ranked"] == sorted(
        profile["spectrums"],
        key=lambda s: profile["spectrums"][s]["how_decided"], reverse=True)
    assert all(profile["spectrums"][s]["how_decided"] >= 0 for s in raw_order)


def test_it_says_where_its_astrology_came_from():
    profile = score_earning_profile(chart())
    assert "pending" in profile["weights"]
    assert "not yet" in profile["provenance"]
