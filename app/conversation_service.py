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
    max_words = 500 if detail == 'detailed' else (350 if technical else (260 if followup else 350))
    if cue or question.strip().lower().rstrip('!.?') in {'hi','hey','hello','thanks','thank you','ok','okay','bye'}:
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
