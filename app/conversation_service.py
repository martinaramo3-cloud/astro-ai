"""Keep reported facts, prior replies and internal astrology in distinct channels."""
import re
from app.question_router import classify_question, conversational_cue, requested_detail


def normalize_history(history, question):
    turns = []
    for item in history or []:
        item = item if isinstance(item, dict) else item.model_dump()
        if item.get('role') in ('user', 'assistant') and isinstance(item.get('content'), str):
            turns.append({'role': item['role'], 'content': item['content']})
    # Older clients include the newly submitted message in history as well as question.
    if turns and turns[-1]['role'] == 'user' and turns[-1]['content'].strip() == question.strip():
        turns.pop()
    while turns and turns[0]["role"] == "assistant":
        turns.pop(0)
    return turns


def astrology_requested(question: str) -> bool:
    q = question.casefold().replace('’', "'").strip()
    if re.search(r"\b(?:no astrology|without (?:the )?(?:astrology|jargon)|plain (?:english|language)|simpler|non.technical)\b", q):
        return False
    if re.fullmatch(r'(?:but |and |ok,? |okay,? )?why[?!. ]*', q):
        return True
    return bool(re.search(
        r"\b(?:explain (?:the )?astrology|astrological (?:reasoning|reason|explanation)|"
        r"what in (?:my|their|our|his|her|the) chart|which (?:planets?|transits?|aspects?|houses?)|"
        r"(?:why|how).{0,45}(?:chart|transit|planet|aspect)|"
        r"(?:explain|show|tell|interpret|analy[sz]e|analysis|focus).{0,65}(?:chart|planet|transit|aspect|houses?|jupiter|venus|saturn)|"
        r"(?:what|how).{0,35}(?:saturn|venus|mars|moon|jupiter|mercury|chiron|pluto|neptune|uranus|retrograde)|"
        r"(?:saturn|venus|mars|moon|jupiter|mercury|chiron|pluto|neptune|uranus).{0,35}(?:mean|affect|square|trine|opposition|conjunct)|"
        r"technical (?:reading|analysis|explanation))\b", q, re.S))


SOCIAL_OPENERS = {'hi','hey','hello','thanks','thank you','ok','okay','bye'}


def is_social_turn(question, cue=None):
    """A greeting or a laugh rather than a question, however it was classified."""
    if cue is None:
        cue = conversational_cue(question)
    return bool(cue) or question.strip().lower().rstrip('!.?') in SOCIAL_OPENERS


def conversation_state(question, history=None, known_profile=None):
    turns = normalize_history(history, question)
    users = [m['content'] for m in turns if m['role'] == 'user']
    answers = [m['content'] for m in turns if m['role'] == 'assistant']
    latest_topic = classify_question(question)
    def starts_topic(message, prior):
        explicit = bool(re.search(r'\b(?:new question|different question|change (?:the )?subject|switch topics)\b', message, re.I))
        question_like = '?' in message or bool(re.match(r'(?:what|when|where|will|can|should|how|do|is|are|tell me about)\b', message, re.I))
        candidate = classify_question(message)
        return explicit or (question_like and candidate not in ('general', prior) and prior != 'general')

    original = users[0] if users else question
    prior_topic = classify_question(original)
    for previous in users[1:]:
        if starts_topic(previous, prior_topic):
            original = previous
            prior_topic = classify_question(previous)
    new_topic = starts_topic(question, prior_topic)
    followup = bool(users and answers) and not new_topic
    topic = prior_topic if followup else latest_topic
    technical = astrology_requested(question)
    if not followup:
        original = question
    statements = []
    available = 12000
    for utterance in reversed(users + [question]):
        if available <= 0:
            break
        text = utterance[:min(2000, available)]
        statements.append(text)
        available -= len(text)
    statements.reverse()
    cue = conversational_cue(question)
    detail = requested_detail(question)
    # A provisional budget, used when nobody supplies a tier (the summary and
    # compatibility paths). apply_tier replaces it once the tier is known.
    max_words = 400 if detail == 'detailed' else (300 if technical else (200 if followup else 300))
    if is_social_turn(question, cue):
        max_words = 30
    return {
        'kind': 'follow_up' if followup else 'new_question',
        'latest_message': question,
        'original_question': original,
        'topic': topic,
        'mode': 'astrology_on_request' if technical else 'everyday',
        'recent_turns': turns[-12:],
        'previous_assistant_responses': answers[-3:],
        'reported_facts': {'saved_profile': known_profile or {}, 'user_statements': statements,
                           'note': 'Verbatim reports, not independently verified. Questions and hypotheticals are NOT asserted facts. Prior assistant text is NOT biographical evidence.'},
        'recap_requested': bool(re.search(r'\b(?:recap|summari[sz]e|repeat (?:that|your answer)|remind me)\b',question,re.I)),
        'max_words': max_words,
        'max_paragraphs': 7 if detail == 'detailed' else 5,
        'conversation_cue': cue,
    }


# How long an answer may be, as (provider tokens, review words) together.
#
# The same budget is enforced in two different units — the provider stops the
# model at a token count, draft review rejects a word count — and when the two
# disagree you get one of two bugs: a reply chopped off mid-sentence because
# review was happy with 300 words the ceiling could never produce, or an
# expensive one, where review trips on ordinary output and spends a second
# billed call rewriting. So both numbers live here, side by side.
#
# Words are set just ABOVE what the tokens can physically produce (roughly
# three words per four tokens), not at the length the tier is meant to be:
# length is already enforced by TIER_DIRECTIVE in the prompt and by the ceiling
# itself. This is the backstop for a runaway answer, and it is the costly one.
BUDGETS = {
    1: (90, 75),
    2: (130, 105),
    3: (110, 90),
    4: (550, 420),
}
# "wdym", "why?", "explain that" — a request to be clearer, which is answered
# in MORE words than the first attempt used, not fewer. A second, shorter,
# prettier sentence is a refusal. So this sits just above a full tier 4 answer
# rather than below it, and it is opt-in: someone has to ask.
EXPLANATION_BUDGET = (620, 470)
DETAILED_BUDGET = (760, 570)
# Seven ranked cities with local arrival times is a table, not a paragraph.
RELOCATION_BUDGET = (900, 690)
# A greeting. The tokens stop the model at roughly the same place the word
# limit would have rejected it, so "hi" can never cost a rewrite — the cheapest
# turn in the app stays the cheapest turn in the app.
SOCIAL_BUDGET = (60, 48)


def budget_for(question, tier, state=None, detail=None):
    """The one answer to "how long may this be", in both units."""
    from app.question_router import detect_relocation_request
    if detail is None:
        detail = requested_detail(question)
    if state is not None and is_social_turn(state['latest_message'], state['conversation_cue']):
        return SOCIAL_BUDGET
    if detect_relocation_request(question):
        return RELOCATION_BUDGET
    tier_budget = BUDGETS.get(tier, BUDGETS[4])
    # These are floors, not overrides: asking for an explanation of a full
    # answer must never end up with less room than the answer itself had.
    if detail == 'detailed':
        return max(DETAILED_BUDGET, tier_budget)
    if detail == 'explanation':
        return max(EXPLANATION_BUDGET, tier_budget)
    if state is not None and state['mode'] == 'astrology_on_request':
        return max(EXPLANATION_BUDGET, tier_budget)
    if state is not None and state['kind'] == 'follow_up':
        return BUDGETS[3]
    return tier_budget


def apply_tier(state, tier, detail=None):
    """Let the tier decide the size, now that the tier is known.

    conversation_state runs before the question has been classified, so it can
    only guess. Once the tier exists it is the better answer — and it is the
    same budget the token ceiling is drawn from, so the two agree by
    construction rather than by coincidence.
    """
    if tier not in BUDGETS:
        return state
    _, words = budget_for(state['latest_message'], tier, state, detail)
    state['max_words'] = words
    state['max_paragraphs'] = 1 if tier <= 2 and words <= 110 else (7 if detail == 'detailed' else 5)
    return state


def attach_conversation(context, question=None, history=None, known_profile=None):
    question = question if question is not None else context.get('question','')
    context['history'] = normalize_history(history if history is not None else context.get('history',[]), question)
    context['conversation'] = conversation_state(question, context['history'], known_profile)
    return context


def relevant_history_question(state):
    """Resolve a follow-up's calculation topic without treating a reply as a fresh forecast."""
    if state['kind'] != 'follow_up':
        return state['latest_message']
    for turn in reversed(state['recent_turns']):
        if turn['role'] == 'user' and classify_question(turn['content']) == state['topic']:
            return turn['content']
    return state['original_question']
