"""Run four answers through the review layer as one thread, and print what it flags.

The answers below are reconstructed from the fragments Martina quoted, not
copied from her session — she reported the problems, not the transcripts. To
check the real ones, replace the strings in ANSWERS with the actual text.

    ./venv/bin/python training/area3/check_thread.py
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "t.db"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.answer_review_service import review_issues  # noqa: E402
from app.conversation_service import conversation_state  # noqa: E402
from app.question_router import asks_for_timing  # noqa: E402

QUESTIONS = [
    "How am I most likely to make money according to my chart?",
    "Does my chart show potential for major financial success?",
    "What career suits me?",
    "Should I pay off my debt before starting a business?",
]

ANSWERS = [
    # 1 — memory, and the timing paragraph for the first time (which is fine).
    "Your clearest earning route is work that carries your name rather than "
    "being one contributor among many. Retained advisory work fits best: "
    "companies pay you to decide what should happen before anyone builds it, "
    "charged per engagement rather than by the hour. Given you are graduating "
    "in May without a job lined up, the first version of this is smaller than "
    "it sounds — two clients, not twenty.\n\n"
    "On timing, late October 2026 into early 2027 is the pressure window: a "
    "long transit crosses the same degree twice, so it is a stretch of time "
    "rather than a single date.",

    # 2 — timing paragraph again, second memory, savings advice.
    "There is real potential here, and it concentrates in the same place: work "
    "that is signed rather than anonymous. The Albania and New York question "
    "matters more than it looks, because one of those cities prices this kind "
    "of work far higher than the other.\n\n"
    "Timing again: the stretch from late October 2026 into the early part of "
    "2027 is when the pressure concentrates, since that slow transit passes "
    "the same point more than once before it clears. Good timing to have "
    "already built some cushion.",

    # 3 — timing a third time, and an unasked-for feelings question.
    "The career that suits you is one where the decision is the product. You "
    "are paid per engagement by founders and heads of department who cannot "
    "afford to get it wrong, and the work is scoped by the decision rather "
    "than by hours spent.\n\n"
    "Late October 2026 into early 2027 remains the window to plan around: "
    "that transit crosses the same degree twice, so treat it as a season "
    "rather than a day. If part of this question is about wanting to feel "
    "financially safe rather than about the mechanics of earning, that's "
    "worth sitting with.",

    # 4 — the debt verdict.
    "Pay it off first. The chart is clear: that window rewards a clean start, "
    "and carrying the debt into it would drag on everything you build. Late "
    "October 2026 into early 2027 is when the pressure lands, and you want to "
    "walk into it owing nothing.",
]


def main() -> None:
    history: list[dict] = []
    for number, (question, answer) in enumerate(zip(QUESTIONS, ANSWERS), start=1):
        state = conversation_state(question, history)
        state["max_words"] = 620
        # Memory is in play for this person, so review must count it as things
        # they told us — the same as the live path does.
        state["reported_facts"]["remembered"] = [
            "Graduating in May without a job lined up",
            "Choosing between Albania and New York",
        ]
        if asks_for_timing(question):
            state["expects_a_date"] = True

        issues = review_issues(answer, state)
        print(f"\n{number}. {question}")
        print(f"   kind={state['kind']}  topic={state['topic']}")
        if issues:
            for issue in issues:
                print(f"   FLAGGED  {issue}")
        else:
            print("   flags nothing")

        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
