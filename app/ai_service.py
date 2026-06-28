import os
from dotenv import load_dotenv
from fastapi import HTTPException
from openai import OpenAI

load_dotenv()

_client: OpenAI | None = None

# Default model used when a caller doesn't specify a tier model. Kept for
# backward compatibility with anywhere that still calls these without a model.
DEFAULT_MODEL = "gpt-4.1-mini"


def _get_client() -> OpenAI:
    """Lazily initialize the OpenAI client.

    Returning a clear HTTPException here (instead of crashing the process at
    import time) means non-AI endpoints keep working when the key is missing,
    and AI endpoints fail with a useful message.
    """
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not configured on the server.",
            )
        _client = OpenAI(api_key=api_key)
    return _client


def _create_response(prompt: str, model: str, max_output_tokens: int) -> tuple[str, int]:
    try:
        response = _get_client().responses.create(
            model=model,
            input=prompt,
            max_output_tokens=max_output_tokens,
        )
    except HTTPException:
        raise
    except Exception as exc:  # surface the real OpenAI error to the client/logs
        cause = getattr(exc, "__cause__", None)
        detail = f"AI service error: {type(exc).__name__}: {exc}"
        if cause is not None:
            detail += f" | underlying: {type(cause).__name__}: {cause}"
        print("OpenAI error:", repr(exc), "| cause:", repr(cause))
        raise HTTPException(status_code=502, detail=detail)
    tokens = response.usage.total_tokens if response.usage else 0
    return response.output_text, tokens


def generate_chart_summary(prompt: str, model: str = DEFAULT_MODEL) -> tuple[str, int]:
    return _create_response(prompt, model=model, max_output_tokens=180)


def generate_astrologer_answer(prompt: str, model: str = DEFAULT_MODEL) -> tuple[str, int]:
    return _create_response(prompt, model=model, max_output_tokens=400)


def generate_compatibility_reading(prompt: str, model: str = DEFAULT_MODEL) -> tuple[str, int]:
    return _create_response(prompt, model=model, max_output_tokens=220)


def generate_compatibility_answer(prompt: str, model: str = DEFAULT_MODEL) -> tuple[str, int]:
    return _create_response(prompt, model=model, max_output_tokens=220)
