import base64
import os

from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi import HTTPException
from openai import OpenAI

load_dotenv()

_openai_client: OpenAI | None = None
_anthropic_client: Anthropic | None = None

# Default model used when a caller doesn't specify a tier model. Kept for
# backward compatibility with anywhere that still calls these without a model.
DEFAULT_MODEL = "gpt-4.1-mini"

# Claude models think before answering, and thinking tokens count toward
# max_tokens. The visible reply is kept short by the prompt itself, so this
# budget is headroom for reasoning rather than a length target — but it is also
# the ceiling on what a single reading can cost, since thinking bills as
# output. 4000 leaves roughly 3,400 tokens of reasoning behind a ~550-token
# answer, which is ample; 8000 was paying for headroom nothing used.
ANTHROPIC_MAX_TOKENS = 4000

# How hard the model works. Thinking bills as output, and at $50/M on the
# premium model that was most of the cost per answer — for interpretive
# writing, which is synthesis rather than hard reasoning, medium reads about
# the same. Paid tiers can still ask for "high" per request.
EFFORT_BY_MODEL: dict[str, str] = {}
DEFAULT_EFFORT = "medium"

# Lets a refused request be retried on another model server-side instead of
# simply failing. Paired with the scalar "default" routing form.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Both SDKs retry twice by default. That is right for an idempotent read and
# wrong for a paid generation: a read timeout does not mean the model stopped
# writing, so each automatic retry is a second and third answer we are billed
# for and never show anyone. Off, with a timeout long enough that a normal
# reading finishes well inside it.
AI_MAX_RETRIES = 0
AI_TIMEOUT_SECONDS = 180.0


def _is_anthropic(model: str) -> bool:
    return model.startswith("claude-")


def _get_openai_client() -> OpenAI:
    """Lazily initialize the OpenAI client.

    Returning a clear HTTPException here (instead of crashing the process at
    import time) means non-AI endpoints keep working when the key is missing,
    and AI endpoints fail with a useful message.
    """
    global _openai_client
    if _openai_client is None:
        # .strip() guards against a stray newline pasted into the dashboard,
        # which would otherwise produce an illegal auth header.
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not configured on the server.",
            )
        _openai_client = OpenAI(
            api_key=api_key,
            max_retries=AI_MAX_RETRIES,
            timeout=AI_TIMEOUT_SECONDS,
        )
    return _openai_client


def _get_anthropic_client() -> Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="ANTHROPIC_API_KEY is not configured on the server.",
            )
        _anthropic_client = Anthropic(
            api_key=api_key,
            max_retries=AI_MAX_RETRIES,
            timeout=AI_TIMEOUT_SECONDS,
        )
    return _anthropic_client


def _anthropic_tokens(usage) -> int:
    """Total billable tokens, including anything read from or written to cache."""
    if usage is None:
        return 0
    fields = (
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    )
    return sum(getattr(usage, field, 0) or 0 for field in fields)


def _anthropic_response(
    user_prompt: str,
    model: str,
    system: str | None,
    effort: str | None = None,
    images: list[dict] | None = None,
) -> tuple[str, int]:
    client = _get_anthropic_client()

    # Images lead, text follows: a picture read before the question is
    # understood in the question's terms rather than described in the abstract.
    if images:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image["content_type"],
                    "data": base64.b64encode(image["content"]).decode(),
                },
            }
            for image in images
        ]
        content.append({"type": "text", "text": user_prompt})
    else:
        content = user_prompt

    request = {
        "model": model,
        "max_tokens": ANTHROPIC_MAX_TOKENS,
        "messages": [{"role": "user", "content": content}],
        "output_config": {
            "effort": effort or EFFORT_BY_MODEL.get(model, DEFAULT_EFFORT)
        },
    }
    if system:
        # Cached as a stable prefix: the standing instructions are identical on
        # every call, so repeat questions in a session only pay for the chart data.
        request["system"] = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    # Thinking is intentionally not configured: it is on by default on these
    # models, and passing an explicit configuration is rejected.
    try:
        with client.beta.messages.stream(
            betas=[FALLBACK_BETA], fallbacks="default", **request
        ) as stream:
            message = stream.get_final_message()
    except Exception as exc:
        # Server-side fallbacks may not be enabled for every account. Losing
        # them is survivable; losing the whole answer is not.
        if "fallback" not in str(exc).lower():
            raise
        print("Anthropic fallbacks unavailable, retrying without:", repr(exc))
        with client.beta.messages.stream(**request) as stream:
            message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise HTTPException(
            status_code=502,
            detail="The astrologer couldn't take that one on. Try rephrasing it.",
        )

    text = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )
    return text, _anthropic_tokens(message.usage)


def _openai_response(
    user_prompt: str,
    model: str,
    max_output_tokens: int,
    system: str | None,
    images: list[dict] | None = None,
) -> tuple[str, int]:
    # The Responses API takes a single input string, so the standing
    # instructions ride along at the front.
    prompt = f"{system}\n\n{user_prompt}" if system else user_prompt

    if images:
        parts = [
            {
                "type": "input_image",
                # Required by the SDK's type for this block. "auto" lets the
                # provider pick the resolution — screenshots have to be read as
                # text, so forcing "low" here would cost accuracy, not just tokens.
                "detail": "auto",
                "image_url": (
                    f"data:{image['content_type']};base64,"
                    + base64.b64encode(image["content"]).decode()
                ),
            }
            for image in images
        ]
        parts.append({"type": "input_text", "text": prompt})
        payload = [{"role": "user", "content": parts}]
    else:
        payload = prompt

    response = _get_openai_client().responses.create(
        model=model,
        input=payload,
        max_output_tokens=max_output_tokens,
    )
    tokens = response.usage.total_tokens if response.usage else 0
    return response.output_text, tokens


def _create_response(
    user_prompt: str,
    model: str,
    max_output_tokens: int,
    system: str | None = None,
    effort: str | None = None,
    images: list[dict] | None = None,
) -> tuple[str, int]:
    try:
        if _is_anthropic(model):
            return _anthropic_response(
                user_prompt, model=model, system=system, effort=effort, images=images
            )
        return _openai_response(
            user_prompt,
            model=model,
            max_output_tokens=max_output_tokens,
            system=system,
            images=images,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Log full detail server-side (Render logs) but never leak it — including
        # the API key, which can appear in header errors — to the client.
        cause = getattr(exc, "__cause__", None)
        print("AI provider error:", repr(exc), "| cause:", repr(cause))
        raise HTTPException(
            status_code=502,
            detail="The astrologer is temporarily unavailable. Please try again in a moment.",
        )


def generate_chart_summary(
    prompt: str, model: str = DEFAULT_MODEL, system: str | None = None
) -> tuple[str, int]:
    return _create_response(prompt, model=model, max_output_tokens=180, system=system)


def generate_astrologer_answer(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    effort: str | None = None,
    images: list[dict] | None = None,
) -> tuple[str, int]:
    # A little more room when there's a picture: reading a screenshot back and
    # then answering takes more words than answering alone.
    return _create_response(
        prompt,
        model=model,
        max_output_tokens=750 if images else 550,
        system=system,
        effort=effort,
        images=images,
    )


# Always the cheap model: this pass is transcription, not interpretation, and
# running it on the premium model would double the cost of every picture for
# no gain in accuracy.
INSPECTION_MODEL = "gpt-4.1-mini"


def inspect_images(prompt: str, images: list[dict]) -> tuple[str, int]:
    """A first read of an attached picture: what is it, and what does it say?"""
    return _create_response(
        prompt,
        model=INSPECTION_MODEL,
        max_output_tokens=1200,
        images=images,
    )


def generate_compatibility_reading(
    prompt: str, model: str = DEFAULT_MODEL, system: str | None = None
) -> tuple[str, int]:
    return _create_response(prompt, model=model, max_output_tokens=220, system=system)


def generate_compatibility_answer(
    prompt: str, model: str = DEFAULT_MODEL, system: str | None = None
) -> tuple[str, int]:
    return _create_response(prompt, model=model, max_output_tokens=220, system=system)
