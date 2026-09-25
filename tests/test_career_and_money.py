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


def test_suggesting_a_profession_is_not_claiming_one():
    """The distinction that broke production. Once the career engine went
    live, every "what career suits me" answer was written from a payload
    containing the words therapy, teaching, law and publishing — and one rule
    could not tell "you would make a good therapist" from "as a lawyer you
    already have the credential". It was marked serious, so the answer became
    the stock apology.

    A chart may suggest work all day. What it may not do is tell somebody they
    already hold a job or a credential.
    """
    state = state_for("should I become a lawyer?")
    # Conditional: a suggestion, and the whole point of the feature.
    assert review_issues("As a lawyer you would be paid for judgement.", state) == []
    assert review_issues("You would make a very good therapist.", state) == []
    assert review_issues("The work suits a teacher more than an engineer.", state) == []
    # Present tense: a claim about their life, and still caught.
    assert review_issues("As a lawyer you are paid for judgement.", state)
    assert review_issues("You are a teacher and it shows.", state)


def test_a_credential_is_caught_however_it_is_phrased():
    """A profession can be suggested. A credential cannot."""
    state = state_for("should I become a lawyer?")
    for draft in ("As a lawyer you would already have the credential.",
                  "You would be qualified for this.",
                  "Your degree would carry it."):
        assert review_issues(draft, state), draft


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
# A route, not a job title
# --------------------------------------------------------------------------

def test_a_list_of_professions_is_not_an_answer():
    """"Consulting, advising, teaching, curating" names four professions and
    says nothing about what is sold, to whom, or how the money moves."""
    draft = ("Consulting, advising, teaching, curating — any of these would "
             "suit the chart, and you would do well at all of them.")
    issues = review_issues(draft, state_for("What career suits me?"))
    assert any("job titles" in i for i in issues), issues


def test_naming_work_without_a_buyer_or_a_price():
    draft = ("The shapes that suit you are advising and teaching, and to a "
             "lesser degree curating. Each of them lets you work from judgement "
             "rather than from process, which is where you are strongest. You "
             "would find all three comfortable and the chart supports every one "
             "of them without much friction, so pick whichever appeals most.")
    # Only on the money half. "What career suits me" is answered with what the
    # work IS, where a buyer and a price are not the point — demanding them
    # there rewrote correct answers.
    issues = review_issues(draft, state_for(MONEY_QUESTION))
    assert any("who pays" in i for i in issues), issues
    assert not any("who pays" in i
                   for i in review_issues(draft, state_for("What career suits me?")))


def test_a_real_route_passes():
    draft = ("Advising beats teaching for you, for one reason: you are paid "
             "for a decision, not for hours in a room. Charge per engagement. "
             "The buyers are founders and heads of department, who pay when "
             "the cost of being wrong is high. Your risk is agreeing to build "
             "what you should have been retained to specify.")
    assert review_issues(draft, state_for("What career suits me?")) == []


def test_a_short_leaning_answer_is_not_asked_for_a_payment_model():
    """Demanding a buyer and a price from "advising, not teaching" is how a
    good short reply becomes a bad long one."""
    assert review_issues("Advising, not teaching.",
                         state_for("so which of those?")) == []


def test_other_topics_are_not_asked_who_pays():
    state = state_for("why do I keep leaving relationships?")
    assert review_issues("You are drawn to writing and to teaching people, and "
                         "both of those are where you go when the other thing "
                         "gets hard. That is the pattern worth watching here.",
                         state) == []


# --------------------------------------------------------------------------
# Declining investment advice is not a cue to give savings advice
# --------------------------------------------------------------------------

@pytest.mark.parametrize("draft", [
    "Keep your savings liquid through that window and you will be fine.",
    "Build a cash buffer before October.",
    "Hold off on any major purchases until spring.",
    "Pay down the debt before that window opens.",
    "Set aside more than usual through those months.",
    "Tighten your spending until the pressure passes.",
])
def test_the_chart_does_not_manage_their_money(draft):
    issues = review_issues(draft, state_for(MONEY_QUESTION))
    assert any("manage their savings" in i for i in issues), issues


def test_it_is_a_rewrite_not_a_replacement():
    """Out of scope rather than wrong about their life. Replacing a good money
    answer with the stock apology over one clause costs more than the clause."""
    from app.answer_review_service import _serious
    issues = review_issues("Keep your savings liquid through that window.",
                           state_for(MONEY_QUESTION))
    assert issues and not _serious(issues)


@pytest.mark.parametrize("draft", [
    # Where the effort goes is the redirect, and must survive.
    "Put the effort into the two clients who already pay on time, and say no "
    "to the third.",
    "Price the specification separately from the build, and charge for it first.",
    "The work to hold back from is the build you were never retained to do.",
])
def test_where_the_effort_goes_still_gets_through(draft):
    assert review_issues(draft, state_for(MONEY_QUESTION)) == []


def test_the_prompt_says_redirect_rather_than_substitute():
    prompt = main.build_ask_astrologer_system()
    assert "Redirect, do not substitute" in prompt
    assert "A transit is not a forecast of their bank balance" in prompt


def test_the_prompt_says_what_a_route_is():
    prompt = main.build_ask_astrologer_system()
    assert '"Consulting" is a word' in prompt
    assert "Name the buyer as specifically as you can" in prompt


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
    # The instruction moved from words to code: the ranking is computed with
    # their life out of scope, and the prompt now points at the result.
    assert "before anything this person has told" in prompt
    assert "Studying something is not being it" in prompt
    assert "never name a fund, a stock, a currency, a property or a market" in prompt


# --------------------------------------------------------------------------
# The production regression: "what career suits me" returned the stock reply
# --------------------------------------------------------------------------

def test_the_drafts_that_returned_the_stock_apology_are_served():
    """Reported live, 25 September 2026.

    The career engine put the words therapy, teaching, law and publishing in
    front of the model on every "what career suits me" question — that is the
    themes payload doing its job. The qualification rule, built to stop Zoli
    awarding a credential nobody mentioned, read "you would make a good
    therapist" as a claim that they are one. It is marked serious, so it
    survived the rewrite and the person got "I don't have enough reliable
    information to be specific about that yet" for asking what career suited
    them — about a chart that was sitting right there.
    """
    from app.answer_review_service import reviewed_answer, safe_reply
    for draft in (
        "You would make a very good therapist, and the chart points there "
        "twice over. Teaching sits close behind, and the two read better as "
        "one job than as a choice. Hold it lightly: only one thing points at each.",
        "As a therapist you would be working with exactly what you are good "
        "at, and teaching sits close behind it. The complication is that what "
        "governs your work is not comfortably placed.",
        "The work that suits you is film, photography and therapy — anything "
        "working with what cannot be measured directly. Teaching and advising "
        "sit close behind, where people come to you for expertise.",
    ):
        state = state_for("What career suits me?")
        answer, _ = reviewed_answer(lambda p, **k: (draft, 0), "p",
                                    {"question": "What career suits me?",
                                     "conversation": state})
        assert answer.strip() != safe_reply(state).strip(), draft
        assert answer.strip() == draft.strip()


def test_a_chart_question_never_says_there_is_not_enough_information():
    """We always have the chart. Saying otherwise is untrue and is the least
    useful sentence in the product."""
    from app.answer_review_service import safe_reply
    reply = safe_reply(state_for(MONEY_QUESTION))
    assert "enough reliable information" not in reply
    assert "chart" in reply


def test_a_style_failure_costs_the_sentence_not_the_answer():
    """A rewrite that still trips a style rule serves the best draft with the
    offending sentence removed."""
    from app.answer_review_service import reviewed_answer, safe_reply
    draft = ("You earn best being paid for judgement rather than hours, from "
             "clients who cannot afford a wrong answer. Consulting, advising, "
             "teaching, curating — any of those. Charge per engagement and "
             "move to a retainer once two of them come back. The first step "
             "is writing down the three problems people already bring you.")
    state = state_for(MONEY_QUESTION)
    answer, _ = reviewed_answer(lambda p, **k: (draft, 0), "p",
                                {"question": MONEY_QUESTION, "conversation": state})
    assert answer.strip() != safe_reply(state).strip()
    assert "Consulting, advising, teaching, curating" not in answer
    assert "per engagement" in answer
