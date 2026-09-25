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
           "provider stopped before", "answer ends mid-sentence",
           # Money. An invented figure, a credential they may not hold and a
           # promise of wealth are all wrong about someone's life in the way
           # this list exists for; where to put their savings is the one thing
           # the safety floor names outright.
           "invents a money figure", "tells them where to invest",
           "promises money as certain")


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

# ---------------------------------------------------------------------------
# Career and money: four things an answer here must never invent.
#
# All four of these passed review clean before this section existed — an
# invented salary, a qualification nobody mentioned, an index fund, and a
# promise of wealth. The prompt's one line about never directing investments
# sits inside a twenty-thousand-character safety floor, arriving behind the
# whole chart, and that is precisely the instruction that loses. So they are
# rules here instead of requests there.
#
# Each one is drawn as narrowly as it can be, because the useful half of a
# money answer lives right next to the banned half: pricing structure next to
# invented prices, a form of success next to an investment instruction.
# ---------------------------------------------------------------------------

# A figure the person gave first is theirs, and repeating it back is fine. One
# appearing for the first time in the answer is a forecast about their income
# that nothing calculated it.
#
# Pricing STRUCTURE carries no digits — "paid per project", "a monthly
# retainer", "a share of what it earns" — so nothing here can reach it. That
# is deliberate: structure is the useful, sayable half.
MONEY_FIGURE = re.compile(
    r"[€$£¥]\s?\d[\d,.]*"
    r"|\b\d[\d,.]*\s?(?:euros?|dollars?|pounds?|usd|eur|gbp)\b"
    r"|\b\d[\d,.]*\s?k\s+(?:a|an|per)\s+(?:month|year|week|day|hour)\b"
    r"|\b\d[\d,.]*\s+(?:a|an|per)\s+"
    r"(?:month|year|week|day|hour|project|client|session|engagement|head)\b"
    r"|\b(?:five|six|seven|eight)[\s-]figures?\b",
    re.I)

# Professions you cannot claim without a credential, and the credentials
# themselves. The FIELDS are deliberately absent — no "law", no "medicine", no
# "architecture" — because studying something is not being it. A memory that
# says "studies law" must never license "as a lawyer" or "you already have the
# credential", and it cannot, because neither word appears in it.
QUALIFICATION_TERM = (
    r"lawyer|attorney|solicitor|barrister|"
    r"doctor|physician|surgeon|nurse|dentist|pharmacist|veterinarian|"
    r"engineer|architect|accountant|auditor|actuary|"
    r"psychologist|psychiatrist|therapist|counsellor|counselor|"
    r"teacher|professor|lecturer|"
    r"licen[cs]ed|certified|accredited|chartered|board.certified|"
    r"qualified|credentials?|credentialled|credentialed|"
    r"degree|diploma|doctorate|masters|"
    r"bar (?:exam|admission)|called to the bar|"
    r"mba|jd|phd|cpa|cfa|acca"
)
_QUALIFICATION_TERM_RE = re.compile(r"\b(?:" + QUALIFICATION_TERM + r")\b", re.I)
# The claim, not the word. "A qualified yes" is ordinary English and stays;
# "you are qualified" is a statement about their life and needs evidence.
QUALIFIED_CLAIM = re.compile(
    r"\b(?:as an?|your|you(?:'re| are| have| already have|'ve)(?:\s+(?:an?|the))?)"
    r"\s+(?:\w+[\s-]){0,2}(?:" + QUALIFICATION_TERM + r")\b", re.I)

# Where to put money. Naming one of these in an astrology answer is investment
# advice whatever the sentence around it is doing.
INVESTMENT_VEHICLE = re.compile(
    r"\b(?:index fund|tracker fund|mutual fund|hedge fund|"
    r"s&p ?500|nasdaq|ftse|dow jones|"
    r"crypto(?:currency)?|bitcoin|ethereum|altcoins?|nfts?|"
    r"401\(?k\)?|roth|sipp|"
    r"brokerage account|treasury (?:bills|bonds)|government bonds|"
    r"stock market|the markets)\b", re.I)
# Acronyms that are only acronyms in capitals. Lower-cased, "ira" is a name and
# "isa" is most of a verb.
INVESTMENT_VEHICLE_CASED = re.compile(r"\b(?:ETFs?|IRA|ISA)\b")
# An instruction to move money somewhere. Forms of success are not instructions
# and must survive this: "owning a business", "equity in a company you help
# build", "a stake in the thing you make" are answers to what the upside looks
# like, which is half of what was asked for. So is "invest in yourself".
INVESTMENT_INSTRUCTION = re.compile(
    r"\b(?:put|move|park|place|allocate|sink|pour|funnel)\b[^.!?]{0,40}?"
    r"\binto\b[^.!?]{0,30}?"
    r"\b(?:stocks?|shares|equities|property|real estate|gold|bonds?|funds?|"
    r"the market|markets)\b"
    r"|\binvest(?:ing)?\s+in\s+"
    r"(?:stocks?|shares|equities|property|real estate|gold|bonds?|funds?|"
    r"the market|markets|commodities)\b"
    r"|\bbuy(?:ing)?\s+(?:stocks?|shares|equities|gold|bonds)\b", re.I)

# Managing their money, which is not the same ban as naming an investment and
# was the hole left by only writing the first one. "Keep your savings liquid
# through that window" names no fund and promises nothing, and is still the
# chart telling someone what to do with their savings.
#
# Declining is not enough on its own — the answer has to go somewhere. The
# prompt sends it to where the effort goes instead.
MONEY_MANAGEMENT = re.compile(
    r"\bkeep\b[^.!?]{0,30}\b(?:savings|cash|money|funds?|capital)\b[^.!?]{0,20}\bliquid\b"
    r"|\b(?:stay|staying|sit|sitting|remain|remaining)\s+liquid\b"
    r"|\bliquid(?:ity)?\s+(?:through|during|until|over|across)\b"
    r"|\b(?:build|keep|hold|grow)\b[^.!?]{0,25}"
    r"\b(?:cash buffer|buffer|reserve|cushion|emergency fund|rainy.?day fund|runway)\b"
    r"|\b(?:avoid|don'?t|do not|hold off on|postpone|delay)\b[^.!?]{0,25}"
    r"\b(?:big|large|major|significant)\s+(?:purchases?|buys?|spending|"
    r"financial (?:decisions?|commitments?))\b"
    r"|\b(?:pay(?:ing)? (?:off|down)|clear(?:ing)?)\b[^.!?]{0,20}"
    r"\b(?:debt|debts|loans?|credit card|mortgage)\b"
    r"|\b(?:save|set aside|put aside|hold back|squirrel away)\b[^.!?]{0,20}"
    r"\b(?:more|money|cash|savings|a bit|some of)\b"
    r"|\b(?:tighten|cut back on|rein in)\b[^.!?]{0,20}"
    r"\b(?:spending|costs|outgoings|budget|expenses)\b", re.I)

# Work named as a job title rather than as a route. "Consulting, advising,
# teaching, curating" is the list the whole section exists to avoid: it names
# four professions and says nothing about what is offered, who buys it, or how
# the money moves — which is the part somebody can act on.
OCCUPATION = re.compile(
    r"\b(?:consult(?:ing|ancy)|advis(?:ing|ory)|coach(?:ing)?|mentor(?:ing|ship)|"
    r"teach(?:ing)?|lectur(?:ing|e)|tutor(?:ing)?|train(?:ing)?|"
    r"curat(?:ing|ion)|writ(?:ing)?|speak(?:ing)?|"
    r"design(?:ing)?|build(?:ing)?|manag(?:ing|ement)|"
    r"strategy|facilitat(?:ing|ion)|produc(?:ing|tion)|"
    r"freelanc(?:ing|e)|contract(?:ing)?|brand(?:ing)?)\b", re.I)
# Three or more of them in a run, which is the list itself rather than a
# sentence that happens to use two of the words.
OCCUPATION_LIST = re.compile(
    r"\b\w*(?:consult|advis|coach|mentor|teach|lectur|tutor|train|curat|writ|"
    r"speak|design|manag|facilitat|produc|freelanc|manag)\w*\b"
    r"(?:\s*(?:,|/|, and|, or| and | or )\s*"
    r"\b\w*(?:consult|advis|coach|mentor|teach|lectur|tutor|train|curat|writ|"
    r"speak|design|manag|facilitat|produc|freelanc|brand)\w*\b){2,}", re.I)
# The two halves that turn a job title into a route somebody can act on.
WHO_PAYS = re.compile(
    r"\b(?:pays?|paid|paying|buys?|buying|hires?|hiring|commissions?|retains?|"
    r"retained|who (?:pays|buys|hires)|customers?|the buyer)\b", re.I)
HOW_CHARGED = re.compile(
    r"\bper (?:project|engagement|session|day|seat|head|report|case|piece)\b"
    r"|\bretainer\b|\bday rate\b|\bflat fee\b|\bby the (?:hour|day|project)\b"
    r"|\b(?:a )?(?:percentage|share|cut|slice) of\b|\bcommission\b|\broyalt(?:y|ies)\b"
    r"|\bsubscription\b|\blicen[cs]e fee\b|\bup ?front\b|\bon delivery\b"
    r"|\bcharge(?:s|d)? (?:for|by|per)\b|\bprice(?:d|s)? (?:by|per|as)\b"
    r"|\bsalar(?:y|ied)\b|\bwage\b|\bequity\b|\bstake in\b", re.I)

# Money promised rather than read. A window is a stretch of time in which
# something is more available; it is not an event with a payout attached.
PROMISED_WEALTH = re.compile(
    r"\b(?:this|that|it|the chart)\s+will\s+make\s+you\s+"
    r"(?:rich|wealthy|money|a fortune)\b"
    r"|\byou\s+will\s+(?:be|become|end up)\s+"
    r"(?:rich|wealthy|a millionaire|financially free)\b"
    r"|\byou(?:'ll| will)\s+never\s+"
    r"(?:worry about|have to worry about|struggle for)\s+money\b"
    r"|\bthe money (?:will )?(?:arrives?|is coming|comes in|lands|shows up)\b"
    r"|\b(?:wealth|financial success|the money) is "
    r"(?:guaranteed|certain|assured|inevitable|coming)\b"
    r"|\bguaranteed (?:income|return|profit|payday|wealth)\b", re.I)


# Wanting to be a thing is not being it — the distinction the whole
# qualification rule exists for. "Should I become a lawyer?", "I'm studying to
# be a lawyer" and a memory reading "wants to be a lawyer" all license nothing.
ASPIRING = re.compile(
    r"\b(?:become|becoming|train(?:ing)? (?:to be|as)|stud(?:y|ying|ies) (?:to be|for)|"
    r"want(?:s|ed)? to be|hopes? to be|thinking about|considering|"
    r"plan(?:s|ning)? to be|if i (?:were|was)|once i)\b", re.I)


def _licensing_clauses(text):
    """The parts of something they said that actually claim a fact.

    Split at clause boundaries rather than sentence ones, because "I'm a
    lawyer, what should I do next?" is a single sentence carrying both a fact
    and a question, and treating the whole thing as a question threw the fact
    away — which flagged the answer for inventing a job they had just named.
    """
    for clause in re.split(r"[,;:—–]|\b(?:but|and then|so)\b", text):
        clause = clause.strip()
        if clause and _asserted(clause) and not ASPIRING.search(clause):
            yield clause


def _stated(state) -> str:
    """Facts they have claimed: this thread, the saved profile, and memory.

    Memory belongs here now that it is live. Without it, an answer resting on
    something said in an earlier conversation looks invented to this file and
    gets rejected for it.
    """
    facts = state['reported_facts']
    said = [c for text in facts['user_statements'] for c in _licensing_clauses(text)]
    said += [c for text in (facts.get('remembered') or []) for c in _licensing_clauses(text)]
    # "Should I leave my job?" is a question, so no clause of it survives the
    # filter above — and the answer then got flagged for inventing a job they
    # had just said they had. A possessive is a claim of possession wherever
    # it appears. "my" only, never "I have": "do I have kids?" must keep
    # licensing nothing, which is what the filter exists for.
    everything = ' '.join(facts['user_statements'] + list(facts.get('remembered') or []))
    said += re.findall(r"\bmy\b[\w\s'’-]{0,30}", everything, re.I)
    return ' '.join(said) + ' ' + json.dumps(facts['saved_profile'], ensure_ascii=False)


def _everything_they_typed(state) -> str:
    """The same sources, unfiltered.

    Money uses this rather than the filtered version. The rule is about
    INVENTING a figure, and a number they typed is not invented by us, whether
    they stated it or asked about it — "should I charge 60 an hour?" makes 60
    theirs. A qualification is the opposite case, which is why it uses the
    filtered text: asking whether to become a lawyer must never license
    answering them as one.
    """
    facts = state['reported_facts']
    return ' '.join(facts['user_statements'] + list(facts.get('remembered') or [])) \
        + ' ' + json.dumps(facts['saved_profile'], ensure_ascii=False)


def money_figures_not_theirs(answer, state) -> list:
    """Amounts in the answer that the person never typed."""
    typed = _everything_they_typed(state)
    theirs = {re.sub(r"[^\d]", "", t) for t in re.findall(r"\d[\d,.]*", typed)}
    lowered = typed.casefold()
    found = []
    for match in MONEY_FIGURE.finditer(answer):
        phrase = match.group(0)
        digits = re.sub(r"[^\d]", "", phrase)
        if digits and digits in theirs:
            continue
        if not digits and phrase.casefold() in lowered:
            continue
        found.append(phrase)
    return found


def qualifications_not_theirs(answer, state) -> list:
    """Credentials the answer hands them that nothing they said supports."""
    stated = _stated(state)
    found = []
    for sentence in _sentences(answer):
        if not _asserted(sentence):
            continue
        for match in QUALIFIED_CLAIM.finditer(sentence):
            term = _QUALIFICATION_TERM_RE.search(match.group(0))
            if term and not re.search(
                r"\b" + re.escape(term.group(0)) + r"\b", stated, re.I
            ):
                found.append(match.group(0))
    return found


def career_offenders(answer, state) -> list:
    """The exact words to name in a repair, since naming them is what works."""
    words = money_figures_not_theirs(answer, state) + qualifications_not_theirs(answer, state)
    for pattern in (INVESTMENT_VEHICLE, INVESTMENT_VEHICLE_CASED,
                    INVESTMENT_INSTRUCTION, PROMISED_WEALTH, MONEY_MANAGEMENT,
                    OCCUPATION_LIST):
        words += [m.group(0) for m in pattern.finditer(answer)]
    return sorted(set(words))


# These words describe biography only when asserted/possessed. A conditional or
# clarifying question is not an assertion, and discussion of the topic is allowed.
BIOGRAPHY = {
    'children': r'children|kids|son|daughter|baby|parenthood',
    'marriage': r'husband|wife|spouse|married|marriage',
    'pregnancy': r'pregnant|pregnancy',
    # "career" is deliberately absent. It is the name of a topic, not a fact
    # about anyone — "the career that suits you", on a question that asked
    # exactly that, was being rejected as invented biography.
    'employment': r'job|boss|employer|workplace|unemployed',
    'finances': r'debt|salary|income|financial struggles|financial problems',
    'housing': r'roommate|flatmate|living alone|live alone|living with',
    'health': r'depression|bipolar|adhd|autism|diagnosis|trauma|ptsd|anxiety disorder',
    'orientation': r'gay|lesbian|bisexual|straight|sexual orientation',
}


# Words too common to say anything about what an answer is ABOUT. Everything
# else of four letters or more counts as ground covered.
_COMMON = frozenset("""the a an and or but of to in on at for with from by as is are was
were be been being it its this that these those you your yours i me my we our they them
their he she his her not no so if then there here what when where which who whom how why
all any both each few more most other some such only own same too very can will just
should now about into through during before after above below up down out off over under
again further once does did do done has have had having would could may might must shall
need want get gets got way ways thing things much many make makes made take takes new one
two three because while whose said say says like also still even yet ever never always
often sometimes than something anything nothing really quite rather instead already""".split())


def _ground(text) -> set:
    """The distinctive words in a piece of text — what it is actually about."""
    return {w for w in re.findall(r"[a-z]+", text.lower())
            if len(w) >= 4 and w not in _COMMON}


# How much of a follow-up may be ground the thread has already covered.
#
# Measured rather than picked. Across realistic career threads, an answer that
# re-argues points already made recycles 71–77% of its distinctive content;
# one that references a point in a clause and then moves on recycles 14%, and
# one that opens genuinely new ground recycles 4–11%. Nothing lands between
# 25% and 71%, so the line sits in the middle of the gap.
REPEATED_GROUND = 0.5
# Below this there is not enough content to measure, and a short leaning
# follow-up — "advising, not teaching" — is supposed to reuse the words.
ENOUGH_TO_MEASURE = 12


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
    saved=state['reported_facts']['saved_profile']
    pronoun_evidence=' '.join(user_reports) + ' ' + json.dumps(saved,ensure_ascii=False)
    known_text=_stated(state)
    # Money. Each of these was written as an answer this app could plausibly
    # produce, and each one passed every rule above it.
    invented_money=money_figures_not_theirs(answer,state)
    if invented_money:
        issues.append('invents a money figure: '+', '.join(invented_money[:3]))
    unlicensed=qualifications_not_theirs(answer,state)
    if unlicensed:
        issues.append('unsupported personal fact: qualification ('+', '.join(unlicensed[:3])+')')
    if (INVESTMENT_VEHICLE.search(answer) or INVESTMENT_VEHICLE_CASED.search(answer)
            or INVESTMENT_INSTRUCTION.search(answer)):
        issues.append('tells them where to invest their money')
    if PROMISED_WEALTH.search(answer):
        issues.append('promises money as certain rather than reading a chart')
    if MONEY_MANAGEMENT.search(answer):
        # Not in SERIOUS. It is out of scope rather than wrong about their
        # life, and replacing a good money answer with the stock apology over
        # one clause costs the person more than the clause does.
        issues.append('tells them how to manage their savings, which no chart knows')
    # Work named rather than routed. Only where routes are actually being
    # given: a question about risk is not required to say who pays.
    if state['topic'] == 'career':
        named = {m.group(0).lower() for m in OCCUPATION.finditer(answer)}
        if OCCUPATION_LIST.search(answer):
            issues.append('lists job titles instead of routes: '
                          + OCCUPATION_LIST.search(answer).group(0))
        # Long enough to actually be giving routes. "Advising, not teaching" is
        # a leaning answer to a narrow follow-up and is supposed to be three
        # words; demanding a payment model from it is how a good short reply
        # gets turned into a bad long one.
        elif (len(answer.split()) >= 40 and len(named) >= 2
                and not (WHO_PAYS.search(answer) and HOW_CHARGED.search(answer))):
            issues.append('names kinds of work without saying who pays or how it is charged')
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
        # The check above only ever caught near-copy-paste. A point re-argued
        # in fresh words — the same three conclusions restated across three
        # answers of a thread — scored 0.46 to 0.72 against its own earlier
        # version and sailed through every time, because nothing compared what
        # the answers were ABOUT, only how they were worded.
        covered=set().union(*[_ground(t) for t in state['previous_assistant_responses']]) \
            if state['previous_assistant_responses'] else set()
        fresh=_ground(answer)
        if covered and len(fresh) >= ENOUGH_TO_MEASURE:
            recycled=len(fresh & covered)/len(fresh)
            if recycled >= REPEATED_GROUND:
                issues.append(
                    f'covers ground already given in this thread ({recycled:.0%} of it) '
                    'instead of adding new')
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
                      for m in pattern.finditer(answer)}
                     # The money ones know which figures were the person's own,
                     # so they are computed rather than matched: telling a
                     # rewrite to delete a number the user supplied is how you
                     # lose the answer they asked for.
                     | set(career_offenders(answer,state)))
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
