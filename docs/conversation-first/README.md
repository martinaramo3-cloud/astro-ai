# Conversation-first answers

Branch: `codex/conversation-first-answers`. Local implementation; not deployed.

## Trace of the response path

- `astro-frontend/app/chat/page.tsx` builds requests and consumes SSE. Previously it put the new message in both `question` and `history`; now history contains only prior turns. Glossary rendering is visual and does not rewrite model answers.
- `app/main.py` validates/gates requests, calculates natal/transit/predictive or compatibility data, selects tier and output ceilings, prepares image data, and calls providers. Both solo endpoints now use `_answer_prepared`. Compatibility, saved-profile compatibility and chart summaries use the same draft reviewer. Weekly horoscope context is a prompt/data endpoint, not an additional model-generated reply.
- `app/conversation_service.py` normalizes legacy duplicated input, discards the introductory assistant greeting, distinguishes topic changes from added context, retains the original question outside the recent 12-turn window, keeps three previous assistant responses for review, and separates user reports from assistant text and profile fields. Reports are bounded to 12,000 characters. Technical mode is requested per turn; it is not sticky.
- `app/ai_context_service.py` holds the shared personality, presentation, uncertainty and fact-provenance rules. Summary, weekly, solo and compatibility prompts all reuse them. Internal chart JSON is separate from the conversation block and is not an instruction to recite every field. Legacy content-repository output templates are no longer injected into reply prompts; the content inspection API still exposes them.
- `app/ai_service.py` provides model adapters, image inspection, and routing/date helper calls. Provider token ceilings remain enforced, including Claude. Helpers do not create extra user-facing readings. Existing provider usage logging remains.
- `app/answer_review_service.py` checks length, technical terminology, stock phrases, unsupported personal claims/pronouns, unqualified third-party predictions, and sentence similarity against recent answers. A violating draft gets at most one corrective model call; both calls count toward recorded usage. A failed/rejected repair returns a cautious clarification. Streaming sends only reviewed text, then the existing completion event.
- `app/image_reading_service.py` extracts printed chart data or message transcripts. It now prohibits biography inferred from appearance/layout and uses LEFT/RIGHT when speaker identity is unknown.
- `app/relocation_reading_service.py` renders computed rankings directly, with a brief interpretation limit, requested ranked cities, strongest practical area, and exact local timestamps. Technical requests add a supporting factor and tradeoff per city. Follow-ups reuse the return calculation and go through conversational review; failed calculations still produce a deterministic error, not an unrelated reading.
- `app/chat_service.py` persists chats. Unrelated recent-session summaries are no longer injected into these readings; only the supplied current conversation establishes follow-up context.

Calculation implementations in chart/ephemeris, transit/timing, predictive, synastry, relocation and relocation-scoring services were not changed. Their existing regressions still run. Calculations remain available in API context/debug data; “internal” here means omitted from default answer prose, not removed from API responses.

## Why answers repeated

The previous prompt mixed voice guidance with instructions to name and explain multiple chart factors. Separate templates reinforced report structure. The current message appeared twice, and the old six-message prompt window could lose the original question. Short follow-ups could be treated as a fresh reading or be stripped of useful calculation context. Retrieval could introduce another session's topic. There was no check against prior generated sentences before streamed output appeared.

The replacement leads with the answer, normally within 190 words/three paragraphs; follow-ups normally within 130 words. Explicit technical explanation allows 170 words; an explicitly detailed request allows 260. Social turns allow 30. Provider token ceilings additionally constrain generation. Ranked-city lists are a deliberate exception so requested cities and travel times cannot disappear.

## Personal information safeguards

Only user reports and saved profile fields can establish biography; questions/hypotheticals and prior assistant claims are not facts. Instructions require subject attribution, neutral pronouns when unknown, and qualified interpretation of another person's intentions. Children, marriage, pregnancy, employment, finances, housing, diagnoses, orientation, ages and pronouns receive additional lexical checks. Saying “may” does not make unsupported parenthood acceptable. Screenshots do not establish identity through layout.

## Verification

- `venv/bin/python -m pytest -q`: **272 passed**.
- 27 new scenario cases in `tests/test_conversation_policy.py`: direct relationship answers with real calculated inputs, explicit technical mode, university follow-up and repetition repair, multiple follow-ups, original-question retention, topic changes, invented children for a 22-year-old friend, neutral clarification, pronouns, third-party certainty, failed repair, streaming draft isolation, shared summary/weekly/compatibility rules, and relocation follow-up continuity.
- Existing streaming tests updated to target the reviewed generation path. Existing calculation, ownership, tier and security regressions pass.
- Frontend ESLint, TypeScript and production Webpack build passed.
- `git diff --check` passed.

Tests use stubbed model output and offline geocoding with actual chart math. They test routing, prompt inputs, guards, and delivery; they do not prove every real model response will have the desired style. No paid live-model evaluation or deployment was performed.

## Limits and tradeoffs

The reviewer uses lexical checks and sentence similarity, not a complete semantic fact checker. Paraphrased repetition, subject-confused facts and less common unsupported claims can escape it; ordinary references to planets or work can produce false positives. Prompt rules supplement those checks. Topic recognition and technical opt-in are also heuristic, especially for ambiguous messages and languages other than English. Long conversations retain the anchor and recent turns, not an unlimited memory of every fact. Repeated failed repairs can produce repeated generic clarifications.

Review may require one extra paid generation. Full-draft buffering delays the first visible SSE text. Token ceilings can still truncate a model response. Relocation rankings use the existing heuristic model and do not establish actual financial outcomes. Specific cities outside the calculated candidate results require additional calculations rather than invented comparisons.

## Deferred AI restrictions

Per the user's prior instruction, removed the newly introduced email-verification model gate, daily AI spending reservations, call caps and concurrency guard. Changes touch `.env.example`, account/database/security/subscription services, provider integration, frontend plan wording and security fixtures/tests/docs. Existing subscription allowances, request throttles and independent security fixes remain. This branch includes the prior local security commit; neither is published by this work.

## Follow-up: complete, fuller replies

The first release made token ceilings too tight (130–380 tokens for substantive turns), and provider stop reasons were discarded. A reply could therefore end mid-word and pass review. The corrected release allows 800–1,200 tokens for normal substantive turns, 1,600–2,200 for explicitly detailed explanations, and 1,000 for summary/compatibility overviews. Word checks now allow 350 words for new questions/technical explanations, 260 for follow-ups, and 500 for requested detail, with up to five ordinary paragraphs. Guidance encourages useful 150–250-word substantive answers without a minimum or padding.

OpenAI incomplete status and Claude max-token stop reasons now travel with generated text into review. Truncated drafts receive one complete rewrite, with a larger token allowance where configurable; incomplete repairs are never displayed. A secondary check catches substantial prose ending without closing punctuation when provider metadata is unavailable. Brief casual replies remain valid. This punctuation heuristic can misclassify unpunctuated lists or emoji endings; provider metadata is the primary signal.

Validation: 278 backend tests passed, including six new tests for both provider adapters, the reported mid-word cutoff, repair headroom, rejected incomplete repairs, and fuller answers. No frontend code changed in this follow-up. Actual paid-model output has not been sampled.
