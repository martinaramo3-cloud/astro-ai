"""Review a complete draft before display; one bounded repair, never a retry loop.

This is defense in depth, not a semantic fact checker. Explicitly reported facts
still need attribution and subject checking by the model's shared instructions.
"""
import json
import re
from difflib import SequenceMatcher
from app.conversation_service import conversation_state

# Houses are written in words at least as often as in digits — "your first
# house" sailed through a pattern that only knew "1st house", in the very
# answer that was reported for being full of jargon.
JARGON = re.compile(
    r'\b(?:saturn|jupiter|venus|mars|mercury|neptune|uranus|pluto|chiron|'
    r'ascendant|midheaven|natal|synastry|retrograde|conjunction|sextile|trine|'
    r'opposition|chart ruler|'
    r'(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|'
    r'eighth|ninth|tenth|eleventh|twelfth)\s+house|'
    r'moon|sun)\b', re.I)
STOCK = re.compile(r'\b(?:(?:the|your) chart (?:shows|says|suggests)|the energy is|emotional weather|the universe is|this is not a guarantee|what you(?:\'re| are) (?:actually|really) asking)\b', re.I)

# Three ways an answer says nothing while sounding thorough. None of them trip
# any other rule here — every sentence can be individually defensible while the
# whole reply commits to no version of the person's life and so cannot be wrong.
# The prompt argues against all three, but the prompt also arrives behind
# thousands of characters of chart data, and that argument has been lost before.
#
# A menu of readings offered instead of one.
HEDGE_MENU = re.compile(
    r'\b(?:plausible|possible|likely|potential) (?:shapes|forms|versions|readings|scenarios|situations)\b'
    r'|\ba few (?:possibilities|options|ways this)\b'
    r'|\bcould be (?:any|one) of\b', re.I)
# The reading made conditional on whether anything happened, so no week could
# contradict it. "if you..." is a normal conditional about their choices and is
# deliberately not matched — only conditionals about whether events occurred.
BOTH_BRANCHES = re.compile(
    r'\bif (?:something|anything|nothing|none of (?:this|that|it))\b'
    r'|\bif (?:that|this|none of it) (?:did not|didn\'t|does not|doesn\'t) (?:happen|land|apply)\b', re.I)
# Asking them to supply the very thing they came to ask, or to validate the
# reading for you. A closing question naming a specific person or event is a
# real question and is not caught here — that distinction is the whole point.
HANDS_BACK = re.compile(
    r'\b(?:did|has|have|was|is)\s+(?:anything|something|any of (?:this|that|it))\b'
    r'|\bwhat\s+(?:actually\s+|specifically\s+)?(?:came up|happened|stood out|landed|went on)\b'
    r'|\bdoes (?:that|this|any of (?:this|that))\s+(?:land|resonate|ring|sound|match|fit|track)\b'
    r'|\bare you (?:just )?(?:checking|testing|going off)\b', re.I)
# Narrating its own limits. "I don't have memory of a storyline between chats"
# is both a worse product and untrue — it is handed the shape of every other
# conversation. Nobody asked what it cannot do, and saying so breaks the thing
# they came for.
# Narrow on purpose. The first version matched any "I don't have…", which
# rejected "I don't have a date for that yet, but the shape of it is clear" —
# a good answer — and pushed it all the way to the stock apology. This catches
# talk about the machinery: memory, chats, access, being a model.
SELF_NARRATION = re.compile(
    r"\b(?:memory|memories) (?:of|between|across|from)\b"
    r"|\bno (?:memory|record|access)\b"
    r"|\bbetween (?:chats|conversations|sessions)\b"
    r"|\byour other (?:chats|conversations)\b"
    r"|\bas an? (?:ai|language model|assistant)\b"
    r"|\bi (?:don't|do not|can't|cannot) (?:carry|retain|store|keep) "
    r"(?:memory|context|conversations|chats)\b"
    r"|\bi (?:don't|do not|can't|cannot) (?:have )?access\b", re.I)

# Correcting them about what it said. It does not have its own previous
# answers outside the open thread, so it is not in a position to, and the trade
# is bad even when it is right: it wins a point and loses the conversation.
LITIGATES = re.compile(
    r"\bi (?:never|didn'?t|did not) (?:say|said|tell|told|claim|promise)\b"
    r"|\bthat'?s not what i (?:said|meant)\b"
    r"|\bi said .{0,30}\bnot\b", re.I)

# Which problems are bad enough to replace the answer entirely. Everything else
# — length, jargon, a stock phrase, a hedge — is a quality problem worth one
# rewrite, and after that a flawed answer still beats "I don't have enough
# reliable information to be specific about that yet", which is what the person
# actually received. These are the ones that are wrong about someone's life.
SERIOUS = ("empty answer", "unsupported personal fact", "unsupported age",
           "unqualified claim about another person", "unsupported gendered pronouns",
           # A sentence that stops halfway is unservable whatever it says, and
           # the rewrite already gets double the tokens to finish it.
           "provider stopped before", "answer ends mid-sentence")


def _serious(issues) -> list:
    return [i for i in issues if i.startswith(SERIOUS)]

# Words that establish how to refer to someone, found in the user's own
# messages or in a saved person's label and relationship type. "ex boyfriend"
# licenses "him"; "my ex", "my friend" and "my manager" license nothing,
# because none of them says a gender.
#
# "partner" is deliberately absent: it is gender-neutral and would license a
# guess rather than evidence an answer.
#
# Assistant text is never part of the evidence. Its own earlier guess must not
# become the licence for the next one.
GENDERED_EVIDENCE = re.compile(
    r"\b(?:she|her|hers|he|him|his|"
    r"boyfriend|girlfriend|bf|gf|husband|wife|fianc[e\u00e9]|fianc[e\u00e9]e|"
    r"man|woman|guy|girl|dude|lad|bloke|"
    r"dad|father|mum|mom|mother|brother|sister|son|daughter|"
    r"uncle|aunt|grandad|grandpa|grandma|granny|nephew|niece)\b", re.I)

# Anything a reader could put in a diary. Deliberately loose about the form —
# "around the 17th", "late October", "mid-December", "2026-10-17" all count.
DATE_MENTIONED = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\b"
    r"|\b\d{1,2}(?:st|nd|rd|th)\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b(?:next|this|late|early|mid)[- ](?:week|month|year|spring|summer|autumn|fall|winter)\b"
    r"|\bin (?:a|two|three|four|six) (?:days?|weeks?|months?)\b"
    r"|\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)

# Internal scoring words. They are how the engine thinks, not how a person
# should be spoken to about someone they know — and "toxic" said about a
# relationship somebody is actually in is a verdict, not a reading.
SCORING_LABELS = re.compile(
    r"\btoxic\b|\bobsessive\b|\bhigh pull with high friction\b"
    r"|\bvolatile, with little\b|\bnothing that stands out\b"
    r"|\battraction[_ ]band\b|\btoxicity[_ ]band\b|\brelationship[_ ]classifier\b"
    r"|\bnet[_ ]score\b|\bpower[_ ]holder\b|\battaches[_ ]first\b", re.I)

# Dating-game advice. Narrow on purpose: "wait until Thursday" is legitimate
# timing and this app gives it constantly — what is banned is a rule about
# managing another person's interest.
DATING_RULES = re.compile(
    r"\bwait for (?:him|her|them) to\b"
    r"|\bdon'?t (?:text|call|message|reach out|double.text) (?:him|her|them) (?:first|back)\b"
    r"|\blet (?:him|her|them) (?:come to you|chase|make the first move)\b"
    r"|\bplay (?:it )?(?:cool|hard to get)\b"
    r"|\bmake (?:him|her|them) (?:want|miss|chase)\b"
    r"|\bdon'?t seem too (?:available|eager|keen)\b", re.I)

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
    # Something was calculated that the answer is not allowed to lose. Used by
    # the city ranking: the whole value of that answer is the places it names,
    # and an answer that drifts into a paragraph about transits has thrown away
    # a hundred and fifty-seven chart calculations.
    required = state.get('must_mention') or []
    if required and not any(
        re.search(re.escape(name.split(',')[0].strip()), answer, re.I) for name in required
    ):
        issues.append('drops the calculated ranking it was asked to report')
    if SELF_NARRATION.search(answer):
        issues.append('narrates its own limits instead of answering')
    if LITIGATES.search(answer):
        issues.append('argues about what it said instead of answering')
    # They asked when, and there are calculated windows sitting in the request.
    # An answer with no date in it has left the only checkable thing out.
    if state.get('expects_a_date') and not DATE_MENTIONED.search(answer):
        issues.append('a timing question answered without a date')
    if SCORING_LABELS.search(answer):
        issues.append('says an internal scoring label out loud')
    if DATING_RULES.search(answer):
        issues.append('gives dating-game advice instead of something to notice')
    if HEDGE_MENU.search(answer):
        issues.append('offers a menu of possibilities instead of one reading')
    if BOTH_BRANCHES.search(answer):
        issues.append('covers both branches, so nothing could contradict it')
    # Only the closing question: a hand-back mid-answer is usually a real
    # clarifying question, but ending on one leaves them holding the question
    # they came to ask.
    closing = _sentences(answer)[-1] if _sentences(answer) else ''
    if closing.endswith('?') and HANDS_BACK.search(closing):
        issues.append('ends by asking them to supply what they asked about')
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
    if re.search(r'\b(?:she|her|he|him|his)\b',answer,re.I) and not GENDERED_EVIDENCE.search(pronoun_evidence):
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
        # Only reached when a draft could not be made safe twice over. It used
        # to ask what the other person had said or done, which answers a
        # question about intentions — not the one about the two charts that
        # was actually asked.
        return ("I can read the connection between the two charts, but I couldn't "
                "put this one into words I'd stand behind. Ask me again, or tell me "
                "what you most want to know about it.")
    return "I don't have enough reliable information to be specific about that yet. Can you tell me a little more about the situation?"


def reviewed_answer(generate, prompt, context, *, on_repair=None, fallback=None, **kwargs):
    """`fallback` is a already-correct answer to serve if the draft can't be
    fixed — a rendered calculation, say. Without one a failed repair falls back
    to a generic apology, which for a ranking someone waited on is worse than a
    plain report: the numbers were right, only the prose was wrong."""
    state=context.get('conversation') or conversation_state(context.get('question',''),context.get('history',[]))
    answer,tokens=generate(prompt,**kwargs)
    problems=review_issues(answer,state)
    if not problems:
        return answer,tokens
    # Naming the exact words is the difference between a rewrite that works and
    # one that fails the same check twice. "Technical astrology in an everyday
    # reply" does not say which phrase to cut; a list does.
    offending=sorted({m.group(0) for pattern in (JARGON,STOCK,SELF_NARRATION,LITIGATES,
                                                 HEDGE_MENU,BOTH_BRANCHES,
                                                 SCORING_LABELS,DATING_RULES)
                      for m in pattern.finditer(answer)})
    repair=prompt+'\n\nDRAFT REVIEW — revise once, return only the replacement answer.\n'+json.dumps({
        'problems':problems,'draft':answer,
        **({'remove_these_exact_words':offending} if offending else {}),
        # The calculated days, handed over rather than described. "You left the
        # date out" produced no date twice; the days themselves do.
        # A name beats a pronoun and beats "they". The draft was rejected for
        # assuming a gender; the rewrite needs to know there is an alternative.
        **({'refer_to_them_as': state.get('their_name') or 'they/them'}
           if any('gendered pronouns' in p for p in problems) else {}),
        **({'cite_one_of_these_dates':state['dates_available']}
           if state.get('dates_available') and
           any('without a date' in p for p in problems) else {}),
        'instruction':'Write a complete replacement, not a continuation. Finish every sentence. Answer the latest message. Remove repetitions and unsupported claims. Use only reported facts for biography, neutral wording for unknowns, and the requested presentation mode. Do not add new personal facts or new chart data.'},ensure_ascii=False)
    try:
        if on_repair: on_repair()
        repair_kwargs = dict(kwargs)
        if any('complete' in issue or 'mid-sentence' in issue for issue in problems) and 'max_output_tokens' in repair_kwargs:
            repair_kwargs['max_output_tokens'] = min(4000, max(1600, repair_kwargs['max_output_tokens'] * 2))
        revised,extra=generate(repair,**repair_kwargs)
    except Exception:
        # Do not serve an unsafe draft if a correction cannot be generated.
        return (fallback or safe_reply(state)),tokens
    tokens+=extra
    remaining = review_issues(revised, state)
    if not remaining:
        return revised, tokens
    # Only step in front of the answer when what's left could mislead them
    # about their own life. A clumsy reading is still a reading.
    if _serious(remaining) or fallback:
        return (fallback or safe_reply(state)), tokens
    return revised, tokens
