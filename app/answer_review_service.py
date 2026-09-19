"""Review a complete draft before display; one bounded repair, never a retry loop.

This is defense in depth, not a semantic fact checker. Explicitly reported facts
still need attribution and subject checking by the model's shared instructions.
"""
import json
import re
from difflib import SequenceMatcher
from app.conversation_service import conversation_state

JARGON = re.compile(r'\b(?:saturn|jupiter|venus|mars|mercury|neptune|uranus|pluto|chiron|ascendant|midheaven|natal|synastry|retrograde|conjunction|sextile|trine|opposition|chart ruler|\d+(?:st|nd|rd|th) house|moon|sun)\b', re.I)
STOCK = re.compile(r'\b(?:the chart shows|the energy is|emotional weather|the universe is|this is not a guarantee|what you(?:\'re| are) (?:actually|really) asking)\b', re.I)
# These words describe biography only when asserted/possessed. A conditional or
# clarifying question is not an assertion, and discussion of the topic is allowed.
BIOGRAPHY = {
    'children': r'children|kids|son|daughter|baby|parenthood',
    'marriage': r'husband|wife|spouse|married|marriage',
    'pregnancy': r'pregnant|pregnancy',
    'employment': r'job|boss|employer|career|workplace|unemployed',
    'finances': r'debt|salary|income|financial struggles|financial problems',
    'housing': r'roommate|flatmate|living alone|live alone|living with',
    'health': r'depression|bipolar|adhd|autism|diagnosis|trauma|ptsd|anxiety disorder',
    'orientation': r'gay|lesbian|bisexual|straight|sexual orientation',
}


def _sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]


def _normal(text):
    return re.sub(r'[^\w\s]', '', text.casefold())


def _asserted(sentence):
    s = sentence.strip().casefold()
    return not ('?' in s or re.match(r"(?:if|whether|suppose|for example|i (?:don't|do not) know|we (?:don't|do not) know)\b",s) or re.search(r"\b(?:doesn't|don't|not|never|can't|cannot)\s+(?:mean|assume|tell|know|prove|establish|have|has|show|indicate)",s))


def review_issues(answer, state):
    issues=[]
    if not answer.strip(): return ['empty answer']
    if getattr(answer, 'incomplete', False):
        issues.append('provider stopped before the answer was complete')
    # Legacy providers/tests may not supply stop metadata. Catch substantial
    # prose that visibly ends mid-thought, without rejecting casual short chat.
    ending = answer.rstrip().rstrip('\"\'”’)*_')
    if len(answer.split()) >= 20 and ending and ending[-1] not in '.!?…':
        issues.append('answer ends mid-sentence')
    if len(answer.split()) > state['max_words']: issues.append('too long for this turn')
    if len([p for p in answer.split('\n\n') if p.strip()]) > state['max_paragraphs']: issues.append('too many paragraphs')
    if state['mode'] == 'everyday' and JARGON.search(answer): issues.append('technical astrology in an everyday reply')
    if STOCK.search(answer): issues.append('stock or poetic phrasing')
    user_reports=state['reported_facts']['user_statements']
    reported=' '.join(s for text in user_reports for s in _sentences(text) if _asserted(s))
    saved=state['reported_facts']['saved_profile']
    pronoun_evidence=' '.join(user_reports) + ' ' + json.dumps(saved,ensure_ascii=False)
    known_text=reported + ' ' + json.dumps(saved,ensure_ascii=False)
    for sentence in _sentences(answer):
        if not _asserted(sentence): continue
        for category,terms in BIOGRAPHY.items():
            if re.search(r'\b(?:'+terms+r')\b',sentence,re.I) and not re.search(r'\b(?:'+terms+r')\b',known_text,re.I):
                if re.search(r"\b(?:your|her|his|their|you(?:'re| are| have)|(?:she|he|they) (?:is|are|has|have)|[\w]+['’]s)\b",sentence,re.I):
                    issues.append('unsupported personal fact: '+category)
        # An age is a fact only when supplied for the right person. Do not infer
        # anyone's biography from a sign, or assign the user's age to a friend.
        for age in re.findall(r'\b(\d{1,3})[- ]year[- ]old\b|\b(?:you are|you\'re|she is|he is|they are) (\d{1,3})\b',sentence,re.I):
            number=next(v for v in age if v)
            if not re.search(r'\b'+number+r'\b',known_text): issues.append('unsupported age')
        if re.search(r"\b(?:he|she|they|your (?:ex|friend|partner))\s+(?:is coming back|is going to|will|definitely|certainly|secretly|still (?:loves|wants|misses)|(?:loves|wants|misses|intends|plans))\b",sentence,re.I):
            if not re.search(r'\b(?:may|might|could|possible|reported|said|told|according to)\b',sentence,re.I):
                issues.append('unqualified claim about another person')
    if re.search(r"\b(?:he|she|they)['’](?:s|re) (?:coming back|going to|in love)",answer,re.I) and not re.search(r"\b(?:may|might|could|possible|said|told)\b", answer,re.I):
        issues.append('unqualified claim about another person')
    # Pronouns in quoted user reports can establish usage; names and charts cannot.
    if re.search(r'\b(?:she|her|he|him|his)\b',answer,re.I) and not re.search(r'\b(?:she|her|he|him|his|boyfriend|girlfriend|husband|wife|man|woman)\b',pronoun_evidence,re.I):
        issues.append('unsupported gendered pronouns')
    if state['kind']=='follow_up' and not state['recap_requested']:
        old=[s for text in state['previous_assistant_responses'] for s in _sentences(text) if len(s.split())>=6]
        for sentence in _sentences(answer):
            if len(sentence.split())<6: continue
            current=_normal(sentence)
            if any(SequenceMatcher(None,current,_normal(prior)).ratio() >= .77 for prior in old):
                issues.append('repeats a previous assistant sentence or conclusion'); break
    return list(dict.fromkeys(issues))


def safe_reply(state):
    q=state['latest_message'].casefold()
    if re.search(r'\b(?:kill myself|suicide|end my life)\b',q):
        return "I'm sorry you're going through this. Are you in immediate danger? If you might act on this now, contact emergency help or someone you trust who can stay with you."
    if state['mode']=='astrology_on_request':
        return "I couldn't give a reliable explanation from this draft. Which part of the previous answer would you like me to explain?"
    if state['topic'] in ('relationship','compatibility'):
        return "I don't have enough reliable information to say what they intend. What have they actually said or done?"
    return "I don't have enough reliable information to be specific about that yet. Can you tell me a little more about the situation?"


def reviewed_answer(generate, prompt, context, *, on_repair=None, **kwargs):
    state=context.get('conversation') or conversation_state(context.get('question',''),context.get('history',[]))
    answer,tokens=generate(prompt,**kwargs)
    problems=review_issues(answer,state)
    if not problems:
        return answer,tokens
    repair=prompt+'\n\nDRAFT REVIEW — revise once, return only the replacement answer.\n'+json.dumps({
        'problems':problems,'draft':answer,
        'instruction':'Write a complete replacement, not a continuation. Finish every sentence. Answer the latest message. Remove repetitions and unsupported claims. Use only reported facts for biography, neutral wording for unknowns, and the requested presentation mode. Do not add new personal facts or new chart data.'},ensure_ascii=False)
    try:
        if on_repair: on_repair()
        repair_kwargs = dict(kwargs)
        if any('complete' in issue or 'mid-sentence' in issue for issue in problems) and 'max_output_tokens' in repair_kwargs:
            repair_kwargs['max_output_tokens'] = min(4000, max(1600, repair_kwargs['max_output_tokens'] * 2))
        revised,extra=generate(repair,**repair_kwargs)
    except Exception:
        # Do not serve an unsafe draft if a correction cannot be generated.
        return safe_reply(state),tokens
    tokens+=extra
    return (revised if not review_issues(revised,state) else safe_reply(state)),tokens
