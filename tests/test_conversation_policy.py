"""Offline routing/review regressions. No claim of live-model style evaluation."""
import pytest
import app.main as main
from app.conversation_service import conversation_state, astrology_requested
from app.answer_review_service import review_issues, reviewed_answer
from app.ai_context_service import build_ask_astrologer_system
from tests.conftest import SOFIA

QUESTION = 'Do you think my ex is coming back?'
ANSWER = "I can't tell whether they'll come back. Consistent contact would be more meaningful than a chance encounter."
HISTORY = [{'role':'user','content':QUESTION}, {'role':'assistant','content':ANSWER}]
UPDATE = 'I have been seeing him a lot recently. We go to the same university.'
NEW = "Sharing a campus makes chance encounters more likely. I'd pay attention to whether he makes an effort to talk to you. How has he acted when you meet?"


def test_greeting_is_not_a_previous_reading_and_current_message_is_not_duplicated():
    state = conversation_state(QUESTION, [{'role':'assistant','content':'Welcome!'}, {'role':'user','content':QUESTION}])
    assert state['kind'] == 'new_question'
    assert state['recent_turns'] == []


@pytest.mark.parametrize('question, expected', [('why?', True), ('What in my chart shows that?',True), ('Which planets are involved?',True), ('Why is my friend avoiding me?',False), ('Explain without astrology',False)])
def test_explicit_technical_opt_in(question, expected):
    assert astrology_requested(question) is expected


def test_topic_switch_resets_anchor_then_keeps_new_anchor():
    history = HISTORY + [{'role':'user','content':'Different question: will my business grow?'}, {'role':'assistant','content':'Consider what demand you have already seen.'}]
    state = conversation_state('What should I do next?', history)
    assert state['original_question'] == history[-2]['content']


def test_relationship_answer_keeps_internal_calculations(client, account, monkeypatch):
    calls=[]
    def generate(prompt, **kwargs):
        calls.append((prompt, kwargs))
        return ANSWER, 20
    monkeypatch.setattr(main, 'generate_astrologer_answer', generate)
    user, headers=account()
    response=client.post('/ask-astrologer', headers=headers, json={**SOFIA,'question':QUESTION,'user_id':user['id']})
    assert response.status_code == 200
    result=response.json()
    assert result['answer'] == ANSWER
    assert result['context']['conversation']['mode'] == 'everyday'
    assert 'Saturn' in calls[0][0]  # calculated inputs reach the model
    assert 'Saturn' not in result['answer']
    assert len(result['answer'].split()) < 190
    assert 'biograph' in build_ask_astrologer_system().lower()


def test_followup_repair_responds_to_university_context(client, account, monkeypatch):
    calls=[]
    def generate(prompt, **kwargs):
        calls.append(prompt)
        return (ANSWER if len(calls)==1 else NEW), 20
    monkeypatch.setattr(main,'generate_astrologer_answer',generate)
    user,headers=account()
    response=client.post('/ask-astrologer',headers=headers,json={**SOFIA,'question':UPDATE,'history':HISTORY,'user_id':user['id']})
    assert response.status_code==200
    result=response.json()
    assert result['answer']==NEW
    assert result['context']['conversation']['kind']=='follow_up'
    assert len(calls)==2
    assert 'repeats a previous' in calls[-1]


def test_technical_explanation_accepted_only_when_requested():
    answer='Venus represents connection; its current aspect suggests an opening for conversation, not a promised reunion.'
    assert 'technical astrology in an everyday reply' in review_issues(answer,conversation_state(QUESTION))
    assert review_issues(answer,conversation_state('What in my chart shows that?',HISTORY))==[]


@pytest.mark.parametrize('draft', ["Your friend may be focused on her children.", "Their kids need attention.", 'Your friend has a daughter.'])
def test_age_never_establishes_children(draft):
    state=conversation_state('My friend is 22. Why are they distant?')
    assert 'unsupported personal fact: children' in review_issues(draft,state)


@pytest.mark.parametrize('answer', ['They may be busy; have they mentioned what is happening?', 'Do they have children or other responsibilities taking up their time?'])
def test_missing_information_uses_neutral_or_question(answer):
    assert review_issues(answer,conversation_state('My friend is distant.'))==[]


@pytest.mark.parametrize('answer', ['He will come back.', "He's coming back.", 'He still loves you.', 'He is coming back.'])
def test_no_certainty_about_other_person(answer):
    assert 'unqualified claim about another person' in review_issues(answer,conversation_state('Will he come back?'))


def test_user_supplied_pronoun_in_question_is_allowed():
    assert review_issues('He may reach out, but I cannot tell from this alone.',conversation_state('Will he come back?'))==[]


def test_multiple_followups_compare_more_than_last_answer():
    history=HISTORY + [{'role':'user','content':UPDATE},{'role':'assistant','content':NEW},{'role':'user','content':'We talked yesterday.'},{'role':'assistant','content':'What did you talk about, and who started the conversation?'}]
    state=conversation_state('He asked about my classes.',history)
    assert any('repeats' in p for p in review_issues(ANSWER,state))
    assert state['original_question']==QUESTION
    assert review_issues('Asking about your classes gives you a little more to go on. Did he keep the conversation going?',state)==[]


def test_failed_repair_never_serves_invented_biography():
    state=conversation_state('My friend is 22. Why are they distant?')
    calls=[]
    def generate(prompt, **kwargs):
        calls.append(prompt)
        return 'Their children need attention.',10
    result,tokens=reviewed_answer(generate,'prompt',{'conversation':state})
    assert len(calls)==2 and tokens==20
    assert 'children' not in result


def test_stream_does_not_leak_unreviewed_draft(client,account,monkeypatch):
    answers=iter([('Saturn means he definitely will return.',10),(ANSWER,10)])
    monkeypatch.setattr(main,'generate_astrologer_answer',lambda *a,**k:next(answers))
    user,headers=account()
    response=client.post('/ask-astrologer/stream',headers=headers,json={**SOFIA,'question':QUESTION,'user_id':user['id']})
    assert response.status_code==200
    assert 'Saturn means he definitely' not in response.text
    assert "can't tell whether" in response.text


def test_explicit_astrology_endpoint_has_calculations_and_relevant_explanation(client,account,monkeypatch):
    seen=[]
    explanation='Venus represents connection; its aspect is one factor to consider, rather than evidence of what someone intends.'
    def generate(prompt,**kwargs):
        seen.append(prompt)
        return explanation,20
    monkeypatch.setattr(main,'generate_astrologer_answer',generate)
    user,headers=account()
    response=client.post('/ask-astrologer',headers=headers,json={**SOFIA,'question':'What in my chart shows that?','history':HISTORY,'user_id':user['id']})
    assert response.json()['answer']==explanation
    assert 'astrology_on_request' in seen[0]
    assert 'Venus' in seen[0]
    assert len(seen)==1


def test_summary_and_weekly_templates_share_plain_language_policy():
    from app.ai_context_service import build_summary_prompt,build_weekly_horoscope_prompt,build_compatibility_prompt
    for builder in (build_summary_prompt,build_weekly_horoscope_prompt,build_compatibility_prompt):
        prompt=builder({})
        assert 'EVERYDAY mode' in prompt
        assert 'Only saved profile fields' in prompt


def test_original_question_survives_recent_window():
    history=HISTORY + sum(([{'role':'user','content':f'Another detail {i}.'},{'role':'assistant','content':f'Observation {i}.'}] for i in range(9)),[])
    state=conversation_state('And then?',history)
    assert len(state['recent_turns'])==12
    assert state['original_question']==QUESTION


def test_relocation_followup_reuses_return_calculation(client,account,monkeypatch):
    question='Rank top 5 European cities for my 2027 solar return for money'
    user,headers=account()
    first=client.post('/ask-astrologer',headers=headers,json={**SOFIA,'question':question,'user_id':user['id']}).json()
    assert '#5' in first['answer']
    assert 'ASC:' not in first['answer']
    seen=[]
    def generate(prompt,**kwargs):
        seen.append(prompt)
        return 'You only need to be there at the calculated moment, not move there permanently.',20
    monkeypatch.setattr(main,'generate_astrologer_answer',generate)
    history=[{'role':'user','content':question},{'role':'assistant','content':first['answer']}]
    response=client.post('/ask-astrologer',headers=headers,json={**SOFIA,'question':'Do I have to move there?','history':history,'user_id':user['id']})
    result=response.json()
    assert result['context']['where_to_be']['year']==2027
    assert 'not move there permanently' in result['answer']
    assert len(seen)==1
    assert 'relocated_solar_return' in seen[0]


def test_provider_truncation_is_repaired_even_after_full_sentence():
    from app.ai_service import GeneratedText
    state=conversation_state(QUESTION)
    calls=[]
    def generate(prompt,**kwargs):
        calls.append(kwargs['max_output_tokens'])
        return (GeneratedText('Consider reaching out.',incomplete=True) if len(calls)==1 else 'You could reach out and see whether the conversation feels mutual.'),10
    answer,tokens=reviewed_answer(generate,'prompt',{'conversation':state},max_output_tokens=1000)
    assert calls==[1000,2000]
    assert answer.endswith('mutual.') and tokens==20


def test_reported_cutoff_is_detected_without_provider_metadata():
    draft="I can't promise you a yes tonight, honestly — but the odds don't look stacked against you either. If I were you, I'd actually reach out instead of wa"
    assert 'answer ends mid-sentence' in review_issues(draft,conversation_state('Should I reach out tonight?'))


def test_a_real_question_gets_room_without_being_padded():
    state=conversation_state(QUESTION)
    answer=' '.join(['There are several possibilities to consider before deciding what to do next.']*20)
    assert 190 < len(answer.split()) < state['max_words']
    assert review_issues(answer,state)==[]
    # Short is still fine. The budget is a ceiling, never a quota.
    assert review_issues('You could ask directly.',state)==[]
    assert main.answer_ceiling(QUESTION,4,state)==main.ANSWER_CEILING[4]


def test_the_four_tiers_are_four_different_sizes():
    """A single default is the complaint that started the tiers: every answer
    arriving the same shape regardless of what was asked."""
    from app.conversation_service import apply_tier
    ceilings=[main.ANSWER_CEILING[t] for t in (1,2,3,4)]
    assert len(set(ceilings))==4
    assert main.ANSWER_CEILING[1] < main.ANSWER_CEILING[4] / 4

    sizes=[apply_tier(conversation_state(QUESTION),t)['max_words'] for t in (1,2,3,4)]
    assert sizes[0] < sizes[3] / 4, sizes
    assert sizes[1] < sizes[3], sizes

    # A greeting stays a greeting even if it is classified generously.
    greeting=apply_tier(conversation_state('hi'),4)
    assert greeting['max_words']==48


def test_incomplete_repair_is_never_shown():
    from app.ai_service import GeneratedText
    result,tokens=reviewed_answer(lambda *a,**k:(GeneratedText('You could try reaching ou',incomplete=True),10),'prompt',{'conversation':conversation_state(QUESTION)},max_output_tokens=1200)
    assert 'reaching ou' not in result
    assert tokens==20


def test_openai_adapter_preserves_incomplete_status(monkeypatch):
    from types import SimpleNamespace
    import app.ai_service as ai
    response=SimpleNamespace(output_text='A partial answer',status='incomplete',usage=SimpleNamespace(input_tokens=4,output_tokens=8))
    monkeypatch.setattr(ai,'_get_openai_client',lambda:SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs:response)))
    text,usage=ai._openai_response('prompt','test',1200,None)
    assert text.incomplete and usage['total']==12


def test_anthropic_adapter_preserves_max_tokens_stop(monkeypatch):
    from types import SimpleNamespace
    import app.ai_service as ai
    message=SimpleNamespace(content=[SimpleNamespace(type='text',text='A partial answer')],stop_reason='max_tokens',usage=SimpleNamespace(input_tokens=4,output_tokens=8))
    class Stream:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def get_final_message(self): return message
    monkeypatch.setattr(ai,'_get_anthropic_client',lambda:SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=lambda **kwargs:Stream()))))
    text,usage=ai._anthropic_response('prompt','test',None,max_output_tokens=1200)
    assert text.incomplete and usage['total']==12


# The reply that prompted this rule, kept verbatim. Every sentence in it is
# individually defensible; together they cover a conversation that went
# sideways, feelings that grew privately, someone from the past, AND the case
# where nothing happened at all — then ask her what happened. There is no week
# it could be wrong about, which is what makes it worthless.
VAGUE = (
    "Looking back at the past week, the most exact thing in it was romantic — and it "
    "peaked a few days ago rather than today. The flavour is contrast rather than ease. "
    "Plausible shapes — a conversation where you wanted one thing and the other person "
    "wanted a slightly different one; feelings that got noticeably stronger in private "
    "than they looked from outside; a pull toward someone from the past. "
    "If nothing external happened at all, the more likely version is that it was internal. "
    "Did anything specific land this week, or are you checking a hunch?"
)


def test_a_reading_that_cannot_be_wrong_is_rejected():
    problems = review_issues(VAGUE, conversation_state('What happened this week?'))
    assert 'offers a menu of possibilities instead of one reading' in problems
    assert 'covers both branches, so nothing could contradict it' in problems
    assert 'ends by asking them to supply what they asked about' in problems


def test_committing_to_one_reading_passes():
    committed = (
        "The sharpest thing this week was romantic, and it peaked on Tuesday rather "
        "than today — so if it landed, it's already behind you. It reads as wanting "
        "something direct while the situation stayed ambiguous. Did he give you a "
        "straight answer, or leave it open?"
    )
    assert review_issues(committed, conversation_state('What happened with him this week?')) == []


def test_a_specific_closing_question_is_not_a_hand_back():
    """Asking about something you named is a conversation. Asking whether
    anything happened at all is handing back the question they came with."""
    for good in (
        ("It reads as him pulling back. Has he answered your last message?",
         'What happened with him this week?'),
        ("The pressure is on money this week. Did the invoice actually clear?",
         'What happened this week?'),
    ):
        assert review_issues(good[0], conversation_state(good[1])) == []


# Caught in production after the first fix shipped: the same three moves, in
# wording the first set of patterns did not match. Kept verbatim, because the
# lesson is that this failure mode rephrases itself rather than disappearing.
VAGUE_2 = (
    "This week's been about routines and health more than anything dramatic — the kind "
    "of week where your body or daily habits quietly ask for attention. "
    "If something specific stood out — a health thing, a shift in a daily routine, "
    "feeling torn about a decision — that's probably the real story of your week. "
    "What actually came up for you?"
)


def test_the_same_refusal_in_different_words_is_also_rejected():
    problems = review_issues(VAGUE_2, conversation_state('What happened in my week?'))
    assert 'covers both branches, so nothing could contradict it' in problems
    assert 'ends by asking them to supply what they asked about' in problems


@pytest.mark.parametrize('closing', [
    'Does that land for you?',
    'Did anything happen on Tuesday?',
    'What actually came up this week?',
])
def test_validation_seeking_closers_are_rejected(closing):
    answer = 'The sharpest thing this week was work, and it peaked Tuesday. ' + closing
    assert 'ends by asking them to supply what they asked about' in review_issues(
        answer, conversation_state('What happened in my week?'))


@pytest.mark.parametrize('closing', [
    'Has he answered your last message?',
    'Did the invoice actually clear?',
    'Are you still planning to hand in your notice?',
])
def test_specific_closers_still_pass(closing):
    answer = 'The pressure this week was on money, and it peaked Tuesday. ' + closing
    assert review_issues(answer, conversation_state('What happened with him this week?')) == []


def test_a_normal_conditional_about_their_own_choice_is_not_a_branch():
    """"If you want to ask, Tuesday" is advice. "If something happened" is a hedge."""
    answer = 'Tuesday is the window. If you want to ask him, do it then rather than at the weekend.'
    assert review_issues(answer, conversation_state('When should I ask him?')) == []


# From a real conversation: a fight, then five follow-ups, every one of them
# answered in eighty words because being mid-thread forced tier 3 before the
# classifier ran. Depth of a question is not a function of its position.
THREAD = [
    {'role': 'user', 'content': 'we fought and honestly im done'},
    {'role': 'assistant', 'content': 'I believe you, and how done you feel right now. It runs hot and heavy.'},
]


@pytest.mark.parametrize('question', [
    'do u think he will regret it tho?',
    'so no contact any time soon?',
    'There\'s a Sun enters Libra today. What does it mean for me?',
])
def test_a_follow_up_is_not_automatically_a_small_question(question):
    from app.conversation_service import budget_for
    state = conversation_state(question, THREAD)
    assert state['kind'] == 'follow_up'
    tokens, _ = budget_for(question, 4, state)
    assert tokens > main.ANSWER_CEILING[3], f'{question} was flattened to a follow-up budget'


@pytest.mark.parametrize('question', ['so yes??', 'wait really', 'and the boots'])
def test_short_leaning_follow_ups_still_stay_short(question):
    from app.conversation_service import budget_for
    from app.question_router import classify_tier
    assert classify_tier(question, THREAD) == 3
    tokens, _ = budget_for(question, 3, conversation_state(question, THREAD))
    assert tokens == main.ANSWER_CEILING[3]


@pytest.mark.parametrize('question', [
    'what does his chart say?', "what's in her chart?", 'can you read his chart?',
    'what in my chart shows that?',
])
def test_asking_about_a_chart_is_an_astrology_request(question):
    """It is as explicit as asking gets, and it was being answered as ordinary
    conversation inside an 82-word budget."""
    from app.conversation_service import budget_for
    state = conversation_state(question, THREAD)
    assert state['mode'] == 'astrology_on_request'
    tokens, _ = budget_for(question, 3, state)
    assert tokens >= main.ANSWER_CEILING[4]


@pytest.mark.parametrize('draft', [
    "I don't have memory of a storyline between chats — but I hear you right now.",
    "As an AI, I can't know what he's thinking.",
    "I can't see your other conversations, so tell me again.",
])
def test_it_never_narrates_its_own_limits(draft):
    """Announcing what it cannot recall is both worse product and untrue: it is
    handed the title, opening question and subject of every other conversation.
    Nobody asked what it can't do."""
    assert 'narrates its own limits instead of answering' in review_issues(
        draft, conversation_state('why do i keep doing this?'))


@pytest.mark.parametrize('draft', [
    'That urgency is real, but it is the peak, not the answer.',
    'I can see this has been building since September. What changed last week?',
])
def test_answering_from_what_it_has_still_passes(draft):
    assert review_issues(draft, conversation_state('why do i keep doing this?')) == []


def test_other_conversations_reach_the_prompt():
    """The wiring was removed and the guidance with it, so the app told people
    outright that it had no memory of anything they had said before."""
    from app.ai_context_service import build_ask_astrologer_system
    prompt = build_ask_astrologer_system()
    assert 'past_conversations' in prompt
    assert 'Never narrate your own machinery' in prompt


@pytest.mark.parametrize('draft', [
    "I don't have a date for that yet, but the shape of it is clear.",
    "I can't see a fixed answer here, but here's what's building.",
    "I don't have your birth time, so the houses are out — what time were you born?",
])
def test_ordinary_i_dont_have_is_not_self_narration(draft):
    """The first version of this rule matched any "I don't have…", rejected
    perfectly good answers, and pushed them all the way to the stock apology."""
    assert review_issues(draft, conversation_state('where do you see me building a future')) == []


def test_a_flawed_answer_beats_a_stock_apology():
    """safe_reply used to replace the answer whenever a rewrite still had any
    problem at all — including a stylistic one. Someone asking where they'd
    build a future got "I don't have enough reliable information to be specific
    about that yet", which is worse than an imperfect reading in every way."""
    state = conversation_state('where do you see me building a future')
    drafts = iter([
        ('The chart shows a long reach toward somewhere far from home.', 10),   # stock phrasing
        ('Your reach runs a long way from home — the chart shows it.', 10),      # still stock
    ])
    answer, _ = reviewed_answer(lambda *a, **k: next(drafts), 'prompt', {'conversation': state})
    assert 'reliable information' not in answer
    assert 'reach' in answer


def test_an_answer_that_invents_a_life_is_still_replaced():
    state = conversation_state('my friend is 22, why are they distant?')
    answer, _ = reviewed_answer(
        lambda *a, **k: ('Their children need attention right now.', 10),
        'prompt', {'conversation': state})
    assert 'children' not in answer


@pytest.mark.parametrize('draft', [
    "I never said late October guarantees anything with him specifically.",
    "That's not what I said — the window is about you, not him.",
    "I didn't tell you he would text.",
])
def test_it_does_not_argue_about_what_it_said(draft):
    """It has the open thread and the titles of the others, so it is not in a
    position to correct someone's memory of it — and the trade is bad even when
    it is right. It wins the point and loses the conversation."""
    assert 'argues about what it said instead of answering' in review_issues(
        draft, conversation_state('but you told me that late october something might happen'))


def test_taking_what_they_remember_and_moving_on_passes():
    good = ("Late October is real: the 24th through the 9th. It sharpens old feelings "
            "rather than bringing anyone back, so watch it, don't plan around it.")
    assert review_issues(good, conversation_state(
        'but you told me that late october something might happen')) == []


def test_the_prompt_says_not_to_lecture_or_reframe():
    from app.ai_context_service import build_ask_astrologer_system
    flat = " ".join(build_ask_astrologer_system().split())
    assert "Never dispute what they say you said" in flat
    assert "Take the thing seriously first" in flat
    assert "said every turn it is a lecture" in flat
