"""What an astrologer must not decide, and what it must not keep saying.

Four answers in one thread, tested live. Every one of these got through the
review layer as it stood, and each had a rule that should have covered it:

  a savings clause in the past tense, past a pattern that only knew "build"
  a timing window explained in all four answers, under a whole-answer measure
  a feelings question on a question about arithmetic, with no rule at all
  "pay it off first", decided from a chart, with no rule at all

The debt one is the serious one. Whether to clear a debt before starting a
business turns on the interest rate, what the debt costs monthly, and how the
business would be funded. A chart holds none of that, so a verdict is a guess
wearing a verdict's clothes — and it is the kind of guess that costs somebody
real money.
"""
import pytest

from app.answer_review_service import review_issues
from app.conversation_service import conversation_state

DEBT_QUESTION = "Should I pay off my debt before starting a business?"
MONEY_QUESTION = "How am I most likely to make money according to my chart?"

WINDOW_GIVEN = ("Your clearest earning route is work that carries your name. "
                "Late October 2026 into early 2027 is the pressure window: a "
                "long transit crosses the same degree twice, so it is a "
                "stretch of time rather than a single date.")
THREAD = [{"role": "user", "content": MONEY_QUESTION},
          {"role": "assistant", "content": WINDOW_GIVEN}]


def state_for(question, history=None, remembered=(), timing=False):
    state = conversation_state(question, history or [])
    state["max_words"] = 620
    state["reported_facts"]["remembered"] = list(remembered)
    if timing:
        state["expects_a_date"] = True
    return state


# --------------------------------------------------------------------------
# A financial decision is not the chart's to make
# --------------------------------------------------------------------------

def test_the_chart_does_not_settle_the_debt_question():
    draft = ("Pay it off first. The chart is clear: that window rewards a "
             "clean start, and carrying the debt into it would drag on "
             "everything you build.")
    issues = review_issues(draft, state_for(DEBT_QUESTION))
    assert any("decides a financial question" in i for i in issues), issues


def test_no_verdict_is_not_enough_on_its_own():
    """Leaning hard without saying the word is the same answer."""
    draft = ("The window from October favours starting things, so there is a "
             "real case for moving sooner rather than later, and your "
             "appetite for risk is high right now.")
    issues = review_issues(draft, state_for(DEBT_QUESTION))
    assert any("without saying what the chart cannot see" in i for i in issues), issues


def test_the_right_shape_of_answer_passes():
    """Say what the chart cannot see, name a couple of the things that decide
    it, point at someone who can do the arithmetic — then give the chart's
    part, clearly as one input."""
    draft = ("This one the chart cannot answer, and I would not want it to: "
             "it turns on the interest rate, what the debt costs you monthly, "
             "and how the business would be funded. A financial adviser can "
             "run those numbers with you in an afternoon. What I can add, as "
             "one input among those: the appetite for starting something is "
             "high from late October, and you are better at building with a "
             "clean deck than at carrying two things at once.")
    assert review_issues(draft, state_for(DEBT_QUESTION)) == []


@pytest.mark.parametrize("question", [
    "Should I take a loan to start this?",
    "Is this a good year to buy a flat?",
    "Should I use my savings for the deposit?",
    "Should I remortgage this year?",
])
def test_the_rule_covers_the_other_money_decisions(question):
    assert review_issues("Yes, the timing supports it and the chart backs it.",
                         state_for(question))


def test_an_ordinary_career_question_is_not_held_to_this():
    """Only questions with arithmetic behind them. "What career suits me?"
    is not one, and must not be made to recite a disclaimer."""
    draft = ("The career that suits you is one where the decision is the "
             "product. You are paid per engagement by founders who cannot "
             "afford to get it wrong.")
    assert review_issues(draft, state_for("What career suits me?")) == []


# --------------------------------------------------------------------------
# One window, explained once
# --------------------------------------------------------------------------

def test_a_window_explained_again_in_fresh_words():
    """The whole-answer measure cannot see this: the rest of the answer is
    genuinely new, so only a quarter of it is recycled and the general rule
    passes it. The window still got its own paragraph four answers running."""
    draft = ("The career that suits you is one where the decision is the "
             "product. You are paid per engagement by founders who cannot "
             "afford to get it wrong, and the work is scoped by the decision "
             "rather than by hours. On timing, the stretch from late October "
             "2026 into the early part of 2027 is when the pressure "
             "concentrates — that slow transit passes the same point more "
             "than once, so treat it as a season rather than a day.")
    issues = review_issues(draft, state_for("What career suits me?", THREAD))
    assert any("timing window already given" in i for i in issues), issues


def test_re_explaining_is_caught_even_when_it_is_brief():
    """Length is not the only tell. Re-deriving why a window is a window is
    the part that was already given, however few words it takes."""
    draft = ("You are paid per engagement by founders. Late October, because "
             "that transit crosses twice.")
    assert any("timing window already given" in i
               for i in review_issues(draft, state_for("What career suits me?", THREAD)))


@pytest.mark.parametrize("draft", [
    "The career that suits you is one where the decision is the product. You "
    "are paid per engagement by founders who cannot afford to get it wrong. "
    "Same window as before, so plan the launch around it.",
    "You are paid per engagement by people who cannot afford to get it wrong. "
    "Late October still, as before.",
])
def test_a_clause_referring_back_is_exactly_right(draft):
    assert review_issues(draft, state_for("What career suits me?", THREAD)) == []


def test_asking_when_is_a_request_to_say_it_again():
    """The dates ARE the answer. An answer that withheld them to avoid
    repeating itself would be useless."""
    draft = ("Late October 2026 into early 2027 is the window, and it is a "
             "stretch of time rather than a date because the transit crosses "
             "the same degree twice before it clears.")
    state = state_for("when exactly is that window?", THREAD, timing=True)
    assert review_issues(draft, state) == []


def test_the_first_telling_is_allowed():
    assert review_issues(WINDOW_GIVEN, state_for(MONEY_QUESTION)) == []


# --------------------------------------------------------------------------
# Savings advice, in any tense
# --------------------------------------------------------------------------

def test_the_cushion_clause_that_got_through():
    """Her exact words. The pattern knew "build" and not "built"."""
    issues = review_issues("Good timing to have already built some cushion.",
                           state_for(MONEY_QUESTION))
    assert any("manage their savings" in i for i in issues), issues


@pytest.mark.parametrize("draft", [
    "Good timing to have already built some cushion.",
    "You will have kept a reserve by then, which helps.",
    "Having a safety net before that window is the difference.",
    "You had set aside enough savings, which is why this lands softly.",
])
def test_every_tense_of_it(draft):
    assert review_issues(draft, state_for(MONEY_QUESTION))


# --------------------------------------------------------------------------
# Feelings, only when they brought them
# --------------------------------------------------------------------------

def test_no_feelings_question_on_a_practical_money_question():
    draft = ("If part of this question is about wanting to feel financially "
             "safe rather than about the mechanics of earning, that's worth "
             "sitting with.")
    issues = review_issues(draft, state_for(MONEY_QUESTION))
    assert any("feelings on a practical money question" in i for i in issues), issues


def test_but_follow_it_when_they_raised_it():
    """The feelings question is real and stays. It just needs them to have
    brought feeling into it first."""
    draft = ("That fear is doing some work here, and it's worth sitting with "
             "rather than solving in one afternoon. The earning route itself "
             "is steadier than it feels from inside.")
    assert review_issues(draft, state_for("I'm scared I'll never make enough money")) == []


def test_a_relationship_question_is_untouched():
    """This gate is for money questions. Feelings are the subject elsewhere."""
    draft = "How does that land for you — is it worth sitting with?"
    state = state_for("why do I pull away in relationships?")
    assert not any("feelings" in i for i in review_issues(draft, state))


# --------------------------------------------------------------------------
# The prompt says all of it too
# --------------------------------------------------------------------------

def test_the_prompt_carries_these_rules():
    import app.main as main
    # Flattened, because these sentences wrap across lines in the prompt.
    prompt = " ".join(main.build_ask_astrologer_system().split())
    assert "NEVER decide a financial question with arithmetic behind it" in prompt
    assert "a guess wearing a verdict's clothes" in prompt
    assert "Explain a window ONCE in a conversation" in prompt
    assert "do not ask about their feelings" in prompt
    assert "point them to someone who can look at the actual numbers" in prompt
