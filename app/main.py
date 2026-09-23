import asyncio
import hashlib
import json
import os
import secrets
from fastapi.middleware.cors import CORSMiddleware
from app.auth_service import create_account, login_user
from app.user_service import get_user_by_id, update_user
from app.profile_service import (
    create_profile,
    list_profiles_by_owner,
    get_profile_by_id,
    delete_profile_by_id,
    update_profile,
)
from app.chat_service import (
    summarize_recent_sessions,
    create_chat_session,
    get_chat_session_by_id,
    list_chat_sessions,
    update_chat_session,
    delete_chat_session_by_id,
)
from app.account_service import export_user_data, delete_user_account
from app.attachment_service import (
    ALLOWED_TYPES,
    MAX_BYTES,
    MAX_PER_MESSAGE,
    delete_attachment,
    get_attachment,
    load_owned_attachments,
    read_attachment_bytes,
    save_attachment,
)
from app.image_reading_service import read_images
from app.usage_log_service import usage_summary
from app.backup_service import create_backup, list_backups, backup_dir, run_backup_loop
from app.error_log_service import record_error, recent_errors, error_summary, prune_errors
from app.invite_service import create_invite, peek_invite, pending_invites, accept_invite
from app.email_service import (
    send_password_reset,
    send_verification,
    email_configured,
    frontend_base,
)
from app.auth_token_service import issue_token, consume_token, PURPOSE_RESET, PURPOSE_VERIFY, reset_password_by_token
from app.sky_view_service import build_sky_view
from app.compatibility_service import get_synastry_aspects, build_synastry_engine
from app.database import init_db, get_db_connection, DB_NAME
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.celestial_events_service import build_cosmic_events, describe_moon_phase
from app.chart_analysis_service import build_chart_analysis, get_house_rulers
from app.session_service import (
    create_session,
    delete_session,
    get_user_id_for_token,
    purge_expired_sessions,
)
from app.question_router import (
    conversational_cue,
    requested_detail,
    classify_question,
    classify_tier,
    detect_relocation_request,
    predictive_topic_for,
    filter_chart_context_by_question_type,
    get_focus_planets,
)
from dotenv import load_dotenv
load_dotenv()
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool
from app.request_validation import RequestModel as BaseModel
from pydantic import BaseModel as ResponseModel

from app.astrology_engine import (
    get_planet_positions_from_utc,
    get_houses_and_ascendant,
    add_house_to_planets,
)
from app.aspect_services import get_aspects
from app.location_service import get_location_data, describe_coordinates, suggest_places
from app.time_service import convert_to_utc
from app.interpretation_service import build_chart_interpretation
from app.month_outlook_service import build_month_outlook
from app.relocation_reading_service import prepare_relocation
from app.conversation_service import (
    BUDGETS,
    DETAILED_BUDGET,
    EXPLANATION_BUDGET,
    RELOCATION_BUDGET,
    apply_tier,
    attach_conversation,
    budget_for,
    conversation_state,
    normalize_history,
    relevant_history_question,
)
from app.answer_review_service import reviewed_answer
from app.transit_timing_service import build_predictive_timeline
from app.transit_service import (
    annotate_house_rulership,
    get_current_transit_positions,
    get_transit_aspects,
    get_transit_houses,
    build_relationship_timing,
    build_upcoming_transit_timeline,
)
from app.predictive_adapter_service import run_predictive_engine
from app.ai_context_service import (
    TIER_DIRECTIVE,
    build_ai_chart_context,
    build_summary_prompt,
    build_weekly_horoscope_prompt,
    build_ask_astrologer_system,
    build_ask_astrologer_user,
    build_compatibility_context,
    build_compatibility_prompt,
    build_ask_compatibility_context,
    build_ask_compatibility_prompt,
)
from app.ai_service import (
    classify_answer_tier,
    extract_asked_date,
    generate_chart_summary,
    generate_astrologer_answer,
    generate_compatibility_reading,
    generate_compatibility_answer,
)
from app.subscription_service import (
    check_usage,
    check_model_allowance,
    check_people_limit,
    model_key_for_id,
    record_usage,
    get_usage_status,
    set_user_tier,
    find_user_id_by_email,
    resolve_model,
    resolve_effort,
    get_user_tier,
    TIERS,
)
from app.content_repository import (
    get_aspects as get_content_aspects,
    get_career_rules,
    get_elements as get_content_elements,
    get_emotional_rules,
    get_houses as get_content_houses,
    get_interpretation_order,
    get_modalities as get_content_modalities,
    get_output_templates,
    get_planets as get_content_planets,
    get_relationship_rules,
    get_sign_rulers as get_content_sign_rulers,
    get_signs as get_content_signs,
)

from app.security_service import SecurityMiddleware, rate_limit

app = FastAPI(title="AI Horoscope API")
app.add_middleware(SecurityMiddleware)

frontend_origins = [
    origin.strip()
    for origin in (
        os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def catch_and_record_errors(request, call_next):
    """Record what broke instead of letting it vanish into the logs.

    An unhandled exception used to surface as a 500 and a line in Render's log
    that nobody was reading. It is now written down with the request that
    caused it, and the caller still gets a civil answer rather than a stack
    trace.
    """
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001
        record_error(str(request.url.path), request.method, exc, status_code=500)
        print("Unhandled error on", request.url.path, repr(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our end. Please try again."},
        )


class BirthData(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    # False when the person doesn't know what time they were born. The chart is
    # then cast for local noon and everything that depends on the exact moment
    # — Ascendant, houses, the Moon's precise degree — is withheld rather than
    # guessed at.
    birth_time_known: bool = True

from typing import List, Optional, Literal

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    # Pictures sent with this message, so a reopened conversation still shows
    # them. Ids only — the files are fetched one at a time, by their owner.
    attachment_ids: Optional[List[int]] = None


class ChatSessionRequest(BaseModel):
    owner_user_id: int
    profile_id: int | None = None
    title: str
    messages: List[ChatMessage]


class ChatSessionUpdateRequest(BaseModel):
    title: str
    profile_id: int | None = None
    messages: List[ChatMessage]

class AstrologyQuestionRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    question: str
    # None means "the client didn't say" — an older cached build, say. The
    # saved account is then the authority, so a user who told us they don't
    # know their birth time never gets a Rising sign invented for them.
    birth_time_known: Optional[bool] = None
    history: Optional[List[ChatMessage]] = None
    user_id: Optional[int] = None
    model: Optional[str] = None  # "fast" | "smart" | "deep"; gated by tier server-side
    effort: Optional[str] = None  # "low" | "medium" | "high"; gated by tier server-side
    session_id: Optional[int] = None  # the open conversation, excluded from the past list
    # Images attached to this question. Ownership is re-checked server-side, so
    # a guessed id can't pull someone else's picture into an answer.
    attachment_ids: Optional[List[int]] = None


class PredictiveRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True
    topic: Optional[str] = None

class PersonBirthData(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True

class CompatibilityRequest(BaseModel):
    person_1: PersonBirthData
    person_2: PersonBirthData
    user_id: Optional[int] = None

class AskCompatibilityRequest(BaseModel):
    person_1: PersonBirthData
    person_2: PersonBirthData
    question: str
    history: Optional[List[ChatMessage]] = None
    user_id: Optional[int] = None
    # Without names the two charts are interchangeable, and answers about one
    # person can silently describe the other.
    person_1_name: Optional[str] = None
    person_2_name: Optional[str] = None
    model: Optional[str] = None  # "fast" | "smart" | "deep"; gated by tier server-side
    effort: Optional[str] = None  # "low" | "medium" | "high"; gated by tier server-side

class SaveProfileRequest(BaseModel):
    owner_user_id: int
    label: str
    person_name: str
    relationship_type: str | None = None
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True

class AskSavedCompatibilityRequest(BaseModel):
    owner_user_id: int
    profile_id: int
    question: str
    history: Optional[List[ChatMessage]] = None
    model: Optional[str] = None  # "fast" | "smart" | "deep"; gated by tier server-side

PASSWORD_RULES = (
    (lambda p: len(p) >= 8, "at least 8 characters"),
    (lambda p: any(c.isupper() for c in p), "one capital letter"),
    (lambda p: any(c.isdigit() for c in p), "one number"),
    (lambda p: any(not c.isalnum() for c in p), "one symbol, like ! or ?"),
)


def check_password(password: str) -> None:
    """Reject a weak password with the specific thing that is missing.

    Listing what failed is friendlier than restating the whole rule, and it is
    not a security leak: these are the published requirements.
    """
    missing = [label for ok, label in PASSWORD_RULES if not ok(password)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Password needs " + ", ".join(missing) + ".",
        )


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUserResponse(ResponseModel):
    id: int
    name: str
    email: str
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True
    subscription_tier: str = "free"
    email_verified: bool = True
    token: str

class UserResponse(ResponseModel):
    id: int
    name: str
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True
    subscription_tier: str = "free"
    email_verified: bool = True


class TierUpdateRequest(BaseModel):
    tier: str


class TierByEmailRequest(BaseModel):
    email: str
    tier: str


class UpdateMeRequest(BaseModel):
    """A partial edit of your own details. Anything omitted is left alone.

    Email and password are absent on purpose — both are credentials and need
    their own confirmation flow, not a ride-along on a birth-details form.
    """
    name: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    birth_time_known: Optional[bool] = None


class UpdateProfileRequest(BaseModel):
    """A partial edit of someone you saved."""
    label: Optional[str] = None
    person_name: Optional[str] = None
    relationship_type: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    birth_time_known: Optional[bool] = None


class ChartSummaryRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: Optional[bool] = None  # see AstrologyQuestionRequest
    user_id: Optional[int] = None

PUBLIC_USER_FIELDS = (
    "id", "name", "email", "birth_date", "birth_time", "birth_place",
    "birth_time_known", "subscription_tier", "email_verified",
)


def public_user(user: dict) -> dict:
    """Strip internal columns (password hash, usage counters) before returning."""
    return {key: user[key] for key in PUBLIC_USER_FIELDS if key in user}


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """Resolve the caller from their `Authorization: Bearer <token>` header.

    Every endpoint that touches stored data depends on this, so identity comes
    from the token rather than from an id the client can choose.
    """
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    user_id = get_user_id_for_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Please log in again.")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in again.")
    rate_limit("account-requests", str(user_id), 120, 60)
    return user


def require_owned_profile(profile_id: int | None, user_id: int) -> None:
    if profile_id is not None:
        profile = get_profile_by_id(profile_id)
        if not profile or profile["owner_user_id"] != user_id:
            raise HTTPException(status_code=403, detail="That saved person is not available.")


def require_self(current_user: dict, target_user_id: int) -> None:
    """Block reading or writing another account's data."""
    if current_user["id"] != target_user_id:
        raise HTTPException(status_code=403, detail="Not allowed.")


@app.on_event("startup")
async def startup():
    init_db()
    purge_expired_sessions()
    # One clean copy on boot, then daily. Boot matters: a deploy restarts the
    # service, so every deploy is now preceded by a backup — which is precisely
    # when a migration is most likely to go wrong.
    asyncio.create_task(run_backup_loop())
    prune_errors()

@app.get("/")
def home():
    return {"message": "AI Horoscope API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/admin/health")
def health_diagnostics(x_admin_secret: str | None = Header(default=None)):
    _require_admin(x_admin_secret)
    return _health_details()


def _health_details():
    """Liveness, storage, and which credentials are configured.

    `database_persistent` is the launch-critical bit: when the DB sits on the
    container's own filesystem instead of a mounted disk, every deploy wipes
    all accounts. The `configured` block reports only whether each secret is
    present — never any part of its value.
    """
    db_path = os.path.abspath(DB_NAME)
    persistent = db_path.startswith("/var/data")

    try:
        conn = get_db_connection()
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
    except Exception:
        user_count = None

    def is_set(name: str) -> bool:
        return bool((os.getenv(name) or "").strip())

    return {
        "status": "ok",
        "database_path": db_path,
        "database_persistent": persistent,
        "registered_users": user_count,
        # A fingerprint of the live astrologer prompt. The service answers
        # /health from the old build until a deploy actually swaps over, so
        # "the API is up" never meant "my prompt change is live". This does.
        "prompt_fingerprint": hashlib.sha256(
            (build_ask_astrologer_system() + repr(sorted(TIER_DIRECTIVE.items()))).encode("utf-8")
        ).hexdigest()[:12],
        # Says which build is answering, so "did my change ship" is one request.
        "tier_routing": "model-assisted",
        # Chiron needs a data file shipped beside the code. If it is missing the
        # chart still builds without it, so the absence is silent — this is how
        # to see it without guessing from a reading.
        "ephemeris": _ephemeris_status(),
        "configured": {
            "openai_key": is_set("OPENAI_API_KEY"),
            "anthropic_key": is_set("ANTHROPIC_API_KEY"),
            "admin_secret": is_set("ADMIN_SECRET"),
        },
    }


# Noon minimises the error on the Moon, which moves ~13 degrees a day: any
# other choice can be half a day wrong, noon at most half of that.
UNKNOWN_BIRTH_TIME = "12:00"


def build_natal_chart_data(data: BirthData):
    time_known = getattr(data, "birth_time_known", True)
    location_data = get_location_data(data.birth_place)

    if not location_data:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not find birth place. Use a clear city/country or "
                "city and country name, for example 'Paris, France' or 'Paris France'."
            )
        )

    if not location_data.get("timezone"):
        raise HTTPException(
            status_code=400,
            detail="Could not determine timezone for this location."
        )

    try:
        utc_dt = convert_to_utc(
            data.birth_date,
            data.birth_time if time_known else UNKNOWN_BIRTH_TIME,
            location_data["timezone"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    planets = get_planet_positions_from_utc(utc_dt)

    if time_known:
        house_data = get_houses_and_ascendant(
            utc_dt,
            location_data["latitude"],
            location_data["longitude"]
        )
        ascendant = house_data["ascendant"]
        midheaven = house_data["midheaven"]
        angles = house_data["angles"]
        houses = house_data["houses"]
        planets = add_house_to_planets(planets, houses)
    else:
        # Houses and the Ascendant rotate a full circle each day, so without a
        # time they are not approximate — they are unknowable.
        # The angles rotate a full circle each day, so without a birth time
        # they are not approximate — they are unknowable, and a transit to one
        # would be pure invention.
        ascendant, midheaven, angles, houses = None, None, [], []
        for planet in planets:
            planet["house"] = None

    aspects = get_aspects(planets)
    interpretation = build_chart_interpretation(planets, aspects)

    return {
        "location_data": location_data,
        "utc_birth_time": utc_dt.isoformat(),
        "birth_time_known": time_known,
        "ascendant": ascendant,
        "midheaven": midheaven,
        # Aspect targets in their own right: Saturn crossing the Midheaven is
        # among the most strongly felt transits anyone has, and until now
        # nothing could see it.
        "angles": angles,
        "houses": houses,
        "planet_positions": planets,
        "aspects": aspects,
        "interpretation": interpretation
    }


@app.get("/places/suggest")
def places_suggest(q: str = ""):
    """Birthplace suggestions, from the same geocoder that resolves the chart.

    Public: it is needed on the signup screen and on an invite page, before
    anyone has an account.
    """
    return {"places": suggest_places(q)}


@app.post("/natal-chart")
def get_natal_chart(data: BirthData):
    natal_data = build_natal_chart_data(data)

    return {
        "message": "Natal chart calculated",
        "input_data": {
            "birth_date": data.birth_date,
            "birth_time": data.birth_time,
            "birth_place": data.birth_place
        },
        **natal_data
    }


@app.post("/transits")
def get_transits(data: BirthData):
    natal_data = build_natal_chart_data(data)

    transit_planets = get_current_transit_positions()

    active_transits = get_transit_aspects(
        natal_planets=natal_data["planet_positions"] + natal_data.get("angles", []),
        transit_planets=transit_planets
    )

    return {
        "message": "Current transits calculated",
        "input_data": {
            "birth_date": data.birth_date,
            "birth_time": data.birth_time,
            "birth_place": data.birth_place
        },
        "location_data": natal_data["location_data"],
        "utc_birth_time": natal_data["utc_birth_time"],
        "natal_planets": natal_data["planet_positions"],
        "transit_planets": transit_planets,
        "active_transits": active_transits
    }


@app.post("/ai-context")
def get_ai_context(data: BirthData):
    natal_data = build_natal_chart_data(data)

    chart_context = build_ai_chart_context(
        planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
        aspects=natal_data["aspects"]
    )

    prompt = build_summary_prompt(chart_context)

    return {
        "message": "AI natal summary context generated",
        "chart_context": chart_context,
        "prompt": prompt
    }


@app.post("/transit-ai-context")
def get_transit_ai_context(data: BirthData):
    natal_data = build_natal_chart_data(data)

    transit_planets = get_current_transit_positions()

    active_transits = get_transit_aspects(
        natal_planets=natal_data["planet_positions"] + natal_data.get("angles", []),
        transit_planets=transit_planets
    )

    chart_context = build_ai_chart_context(
        planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
        aspects=natal_data["aspects"],
        transits=active_transits
    )

    prompt = build_weekly_horoscope_prompt(chart_context)

    return {
        "message": "AI weekly horoscope context generated",
        "chart_context": chart_context,
        "prompt": prompt
    }


@app.post("/predictive-reading")
def predictive_reading(data: PredictiveRequest):
    natal_data = build_natal_chart_data(
        BirthData(
            birth_date=data.birth_date,
            birth_time=data.birth_time,
            birth_place=data.birth_place,
            birth_time_known=data.birth_time_known,
        )
    )

    transit_planets = get_current_transit_positions()
    active_transits = get_transit_aspects(
        natal_planets=natal_data["planet_positions"] + natal_data.get("angles", []),
        transit_planets=transit_planets
    )

    result = run_predictive_engine(
        natal_chart=natal_data,
        transit_aspects=active_transits,
        requested_topic=data.topic,
    )

    return {
        "message": "Predictive reading generated",
        "topic": result.main_topic.value,
        "tone": result.tone.value,
        "process_or_event": result.process_or_event,
        "strongest_window": result.strongest_window,
        "likely_manifestation": result.likely_manifestation,
        "why_active": result.why_active,
        "competing_interpretations": result.competing_interpretations,
        "topic_assessments": [
            {
                "topic": assessment.topic.value,
                "natal_promise_score": assessment.natal_promise_score,
                "activation_score": assessment.activation_score,
                "repeated_methods": [method.value for method in assessment.repeated_methods],
                "activated_houses": assessment.activated_houses,
                "activated_planets": assessment.activated_planets,
                "tone": assessment.tone.value,
                "manifestation_level": assessment.manifestation_level.value,
                "strongest_window": assessment.strongest_window,
                "likely_manifestation": assessment.likely_manifestation,
                "competing_interpretations": assessment.competing_interpretations,
                "reasoning": assessment.reasoning,
            }
            for assessment in result.topic_assessments
        ],
    }




@app.get("/content-library")
def get_content_library():
    return {
        "planets": get_content_planets(),
        "signs": get_content_signs(),
        "houses": get_content_houses(),
        "aspects": get_content_aspects(),
        "sign_rulers": get_content_sign_rulers(),
        "elements": get_content_elements(),
        "modalities": get_content_modalities(),
        "interpretation_order": get_interpretation_order(),
        "output_templates": get_output_templates(),
        "relationship_rules": get_relationship_rules(),
        "career_rules": get_career_rules(),
        "emotional_rules": get_emotional_rules(),
    }

@app.post("/chart-summary")
def chart_summary(
    data: ChartSummaryRequest,
    current_user: dict = Depends(get_current_user),
):
    tier_config = check_usage(current_user["id"])

    if data.birth_time_known is None:
        data.birth_time_known = bool(current_user.get("birth_time_known", 1))

    natal_data = build_natal_chart_data(
        BirthData(
            birth_date=data.birth_date,
            birth_time=data.birth_time,
            birth_place=data.birth_place,
            birth_time_known=data.birth_time_known,
        )
    )

    chart_context = build_ai_chart_context(
        planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
        aspects=natal_data["aspects"]
    )

    prompt = build_summary_prompt(chart_context)
    review_context = attach_conversation({}, "Give me a brief personal overview.")
    summary, tokens = reviewed_answer(generate_chart_summary, prompt, review_context,
                                     model=tier_config["model"], user_id=current_user["id"])
    record_usage(current_user["id"], tokens)

    return {
        "message": "AI chart summary generated",
        "chart_context": chart_context,
        "summary": summary,
        "tier": tier_config["label"],
    }

def interpret_attachments(attachments: list[dict], user_id: int | None = None) -> tuple[dict | None, list[dict], int]:
    """Turn attached pictures into something the answering model can use.

    Returns (context, images_to_send, tokens_spent).

    The branch that matters is the birth chart: when the birth data is printed
    on it, the chart is cast here from the real ephemeris and the picture is
    *not* forwarded. The answer is then based on the same arithmetic as every
    other reading, rather than on a model squinting at a wheel — and it costs
    less, because the expensive model never sees the image.
    """
    if not attachments:
        return None, [], 0

    reading = read_images(attachments, user_id=user_id)
    tokens = reading.get("tokens", 0)
    kind = reading.get("kind")

    if kind == "birth_chart" and reading.get("birth_data"):
        found = reading["birth_data"]
        try:
            chart = build_natal_chart_data(BirthData(**found))
        except HTTPException as exc:
            # The place was printed but isn't one we can find. Fall back to
            # looking at the picture rather than dropping the question.
            print("Chart image recast failed:", exc.detail)
        else:
            return (
                {
                    "kind": "birth_chart",
                    "note": (
                        "The user attached a chart. Its birth details were printed on it, "
                        "so this chart has been recalculated here from the ephemeris — it is "
                        "accurate, not read off the picture. Treat it as a second person's "
                        "chart, separate from the user's own chart above."
                    ),
                    "read_from_image": found,
                    "birth_time_known": chart["birth_time_known"],
                    "ascendant": chart["ascendant"],
                    "placements": [
                        {
                            "planet": p["planet"],
                            "sign": p["sign"],
                            "degree_in_sign": p["degree_in_sign"],
                            "house": p["house"],
                            "retrograde": p.get("retrograde", False),
                        }
                        for p in chart["planet_positions"]
                    ],
                    "aspects": chart["aspects"][:12],
                },
                [],
                tokens,
            )

    if kind == "conversation":
        return (
            {
                "kind": "conversation",
                "note": (
                    "The user attached a screenshot of a conversation and is asking for help "
                    "with it. The transcript below was read from the image. Answer about what "
                    "is actually said in it, using their chart to explain how they tend to "
                    "react and what they will find hard to say — not to predict the other "
                    "person, whose chart you do not have unless one is given above. If they "
                    "ask what to say, give them actual words they could send."
                ),
                "transcript": reading.get("transcript"),
                "description": reading.get("description"),
            },
            # The picture still goes through: tone, emoji and who-said-what are
            # carried by the layout as much as by the words.
            attachments,
            tokens,
        )

    note = (
        "The user attached an image. Answer about what is actually in it."
    )
    if kind == "birth_chart":
        note = (
            "The user attached a chart, but its birth details could not be read from it or "
            "resolved to a real place, so it could not be recalculated. You are reading placements off a picture: say so "
            "plainly, keep to what is clearly legible, and offer to cast it properly if they "
            "give you the birth date, time and place. Never state a degree or a house you "
            "cannot clearly see."
        )

    return (
        {"kind": kind, "note": note, "description": reading.get("description")},
        attachments,
        tokens,
    )


def build_prediction(natal_data: dict, active_transits: list, question_type: str | None) -> dict | None:
    """Run the predictive engine and trim its output for the prompt.

    The engine ranks every life area by how hard it is currently being hit and
    explains its own reasoning, which is exactly the judgement a language model
    is worst at making unaided. It is pure arithmetic — no AI call, no cost —
    so the only thing to be careful about is how much of it ships in the prompt.
    """
    if not natal_data.get("houses"):
        # Every topic in the engine is defined by houses, so without a birth
        # time there is nothing for it to rank.
        return None

    try:
        result = run_predictive_engine(
            natal_chart=natal_data,
            # The engine looks every natal point up among the planets, so a
            # transit to the Ascendant or Midheaven is not something it can
            # place. Those are read directly in the prompt instead.
            transit_aspects=[
                t for t in active_transits
                if t["natal_planet"] not in ("Ascendant", "Midheaven")
            ],
            requested_topic=predictive_topic_for(question_type),
        )
    except Exception as exc:  # noqa: BLE001 - a reading is better than an error
        print("Predictive engine failed:", repr(exc))
        return None

    return {
        "note": (
            "Computed from the transits above, not written by a model. "
            "'why_active' is the engine's own reasoning — use it to decide what to "
            "lead with, don't quote it back."
        ),
        "main_topic": result.main_topic.value,
        "tone": result.tone.value,
        "process_or_event": result.process_or_event,
        "strongest_window": result.strongest_window,
        "likely_manifestation": result.likely_manifestation,
        "why_active": result.why_active[:6],
        "competing_interpretations": result.competing_interpretations[:3],
        # Ranked so the model can see which areas are loud and which are quiet.
        "topics_by_activation": [
            {
                "topic": t.topic.value,
                "score": t.activation_score,
                "tone": t.tone.value,
                "level": t.manifestation_level.value,
            }
            for t in result.topic_assessments[:5]
        ],
    }


# How long the visible answer may be, per tier — the original numbers. Four
# genuinely different sizes, so a greeting costs a greeting and a real question
# gets room. A single default, whatever its value, brings back the complaint
# that started the tiers: every answer arriving the same shape.
#
# This is the answer's budget alone. Claude spends its thinking from a separate
# allowance (THINKING_HEADROOM in ai_service), so these stay tight without
# strangling the reasoning behind them.
#
# The matching word limits live beside these in conversation_service.BUDGETS,
# because the provider ceiling and the draft review have to agree.
ANSWER_CEILING = {tier: tokens for tier, (tokens, _) in BUDGETS.items()}
DETAIL_CEILING = {"explanation": EXPLANATION_BUDGET[0], "detailed": DETAILED_BUDGET[0]}


def answer_ceiling(question: str, tier: int, conversation: dict | None = None) -> int:
    tokens, _ = budget_for(question, tier, conversation)
    return tokens


_MONTH_WORDS = (
    "month", "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
)


def _asks_about_a_month(question: str) -> bool:
    """Whether this is a question about a stretch of time rather than a moment."""
    lowered = (question or "").lower()
    return any(word in lowered for word in _MONTH_WORDS)


def _prepare_astrologer_call(
    data: AstrologyQuestionRequest,
    current_user: dict,
) -> dict:
    """Everything that happens before the model is asked anything.

    Shared by the blocking endpoint and the streaming one, so the two can
    never drift apart: same tier gate, same chart, same context.
    """
    state = conversation_state(data.question, data.history, {"user": {
        k: current_user[k] for k in ("name", "birth_date") if current_user.get(k)
    }})
    normalized_history = normalize_history(data.history, data.question)
    # Usage and tier follow the token, so nobody can bill another account.
    user_id = current_user["id"]
    tier_config = check_usage(user_id)
    tier = get_user_tier(user_id)
    model = resolve_model(tier, data.model)
    # Stop here if this model's token budget is already spent for this tier.
    check_model_allowance(user_id, tier, model_key_for_id(model))
    effort = resolve_effort(tier, data.effort)

    if data.birth_time_known is None:
        data.birth_time_known = bool(current_user.get("birth_time_known", 1))

    # Attached pictures are read before anything else, because what they turn
    # out to be changes what the answering model is given.
    attachments = (
        load_owned_attachments(data.attachment_ids, user_id)
        if data.attachment_ids
        else []
    )
    if attachments:
        require_image_tier(user_id)

    image_context, images_for_model, image_tokens = interpret_attachments(attachments, user_id=user_id)

    natal_data = build_natal_chart_data(data)

    relocation_question = data.question
    relocation = detect_relocation_request(relocation_question)
    relocation_followup = False
    if not relocation and state['kind'] == 'follow_up':
        relocation_question = state['original_question']
        relocation = detect_relocation_request(relocation_question)
        relocation_followup = bool(relocation)
    if relocation:
        context, answer = prepare_relocation(relocation_question, data.birth_date, natal_data, relocation)
        context.update(question=data.question, answer_tier=4, conversation=state, history=normalized_history)
        ranking = context.get("where_to_be") or context.get("where_to_live")
        calculated = ranking["status"] in ("ok", "partial")
        # Only the request that asks for the ranking has to deliver it. A
        # follow-up — "do I have to move there?" — is answering something else
        # about a ranking already on screen, and demanding the list again would
        # reject every sensible reply to it.
        if calculated and not relocation_followup:
            # Zoli writes this one. Returning the rendered report instead was
            # protecting the ranking from being talked over — but it shipped a
            # spreadsheet: numbered rows, raw scores, ISO timestamps and IANA
            # timezone names, in an app whose own rules say never to quote the
            # arithmetic. The protection belongs in review, not in refusing to
            # let it speak: naming the cities is now a requirement of the draft,
            # so the ranking cannot quietly become a paragraph about transits.
            state["must_mention"] = [city["place"] for city in ranking["best"][:3]]
        return {
            "user_id": user_id, "tier": 4, "tier_config": tier_config,
            "max_output_tokens": RELOCATION_BUDGET[0], "model": model, "effort": effort,
            "images": None, "image_tokens": image_tokens, "question_type": "relocation",
            # A failed calculation still has something true to say, and no model
            # should be asked to improvise around a missing one.
            "chat_context": context,
            **({"report_fallback": answer} if calculated else {"calculated_answer": answer}),
        }

    transit_planets = get_current_transit_positions()

    active_transits = annotate_house_rulership(
        get_transit_aspects(
            natal_planets=natal_data["planet_positions"] + natal_data.get("angles", []),
            transit_planets=transit_planets,
        ),
        natal_data.get("houses", []),
        natal_data["planet_positions"],
    )

    question_type = state["topic"]
    focus_planets = get_focus_planets(question_type)

    filtered_context = filter_chart_context_by_question_type(
        question_type=question_type,
        planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
        aspects=natal_data["aspects"],
        transits=active_transits
    )

    sky = build_cosmic_events(
        natal_planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
    )

    chart_structure = build_chart_analysis(
        planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
        houses=natal_data["houses"],
        aspects=natal_data["aspects"],
        utc_dt=datetime.fromisoformat(natal_data["utc_birth_time"]),
        question_type=question_type,
    )

    rules_by_point: dict[str, list[int]] = {}
    for entry in get_house_rulers(natal_data["houses"], natal_data["planet_positions"]):
        rules_by_point.setdefault(entry["ruler"], []).append(entry["house"])

    chat_context = {
        "question": data.question,
        # Attachment ids are dropped: the model can't fetch a file, and a
        # column of nulls in every past turn is only noise in the prompt.
        "history": normalized_history,
        # Stated up front, not just buried in chart_structure: everything the
        # birth time would have given is null below, and the difference between
        # "unknown" and "absent" is the difference between honest and invented.
        "birth_time_known": natal_data["birth_time_known"],
        # The top of the chart. Present whether or not anything is transiting
        # it: for any question about work or reputation the Midheaven's sign is
        # the starting point, not a detail that only matters when hit.
        "midheaven": natal_data.get("midheaven"),
        "personal_planets": natal_data["planet_positions"],
        "active_transits": active_transits,
        "requested_detail": requested_detail(data.question),
        **filtered_context,
        # Real windows, one per exact hit, searched as far ahead as the
        # question warrants. Replaces an eight-week scan that used one orb for
        # everything and merged a retrograde's passes into a single smear.
        "predictive_timeline": build_predictive_timeline(
            natal_data["planet_positions"] + natal_data.get("angles", []),
            question_type=question_type,
            rules_by_point=rules_by_point,
            limit=18 if requested_detail(data.question) else 12,
        ),
        "sky_now": {
            "moon": sky["moon"],
            "retrograde_now": sky["retrograde_now"],
            "notable_event": sky["headline"],
            # Trimmed to essentials — the full objects (with natal_hits) are
            # heavy, and only the headline needs that much detail.
            "upcoming_events": [
                {
                    "date": e["date"][:10],
                    "name": e["name"],
                    "sign": e["sign"],
                    "days_away": e["days_away"],
                    "is_personal": e["is_personal"],
                }
                for e in sky["events"][:5]
            ],
            # Which of their houses each transiting planet is crossing — the
            # area of life a transit is playing out in.
            "transits_through_houses": get_transit_houses(
                transit_planets, natal_data["houses"], focus_planets=focus_planets
            ),
        },
        "chart_structure": {**chart_structure, "source": "natal",
                            "all_house_rulers": get_house_rulers(natal_data["houses"], natal_data["planet_positions"]),
                            "house_system": "Placidus", "rulership_system": "traditional"},
        "prediction": build_prediction(natal_data, active_transits, question_type),
        # Titles only, so a question can be picked back up across sessions.
        # Without this the app told people outright that it had no memory of
        # anything they had said before, which is both a worse product and
        # untrue — it has the shape of every other conversation, just not the
        # contents.
        "past_conversations": summarize_recent_sessions(
            user_id, exclude_session_id=data.session_id
        ),
    }

    if image_context:
        chat_context["attached_image"] = image_context

    # A question that names a time gets that time's sky rather than an
    # extrapolation from this week's.
    asked_date = extract_asked_date(relevant_history_question(state), user_id=user_id)
    if asked_date:
        try:
            moment = datetime.fromisoformat(asked_date).replace(tzinfo=timezone.utc)
            on_the_day = annotate_house_rulership(
                get_transit_aspects(
                    natal_planets=natal_data["planet_positions"] + natal_data.get("angles", []),
                    transit_planets=get_current_transit_positions(moment),
                    when=moment,
                ),
                natal_data.get("houses", []),
                natal_data["planet_positions"],
            )
            chat_context["transits_on_asked_date"] = {
                "date": asked_date,
                "note": (
                    "The sky calculated for the date this question asks about. "
                    "These are real positions for that day — cite them as confidently "
                    "as today's, and do not hedge about being unable to see that far."
                ),
                "transits": on_the_day[:8],
            }
        except Exception as exc:  # noqa: BLE001
            print("Could not build transits for", asked_date, repr(exc))

    # Asked about a month, answer about the whole month and the whole life.
    # Picking the loudest transit and going deep on one area left work, money,
    # health and everyone's friends unmentioned.
    if _asks_about_a_month(data.question) and natal_data.get("houses"):
        try:
            when = datetime.fromisoformat(asked_date) if asked_date else datetime.now(timezone.utc)
            rules: dict[str, list[int]] = {}
            for entry in get_house_rulers(natal_data["houses"], natal_data["planet_positions"]):
                rules.setdefault(entry["ruler"], []).append(entry["house"])
            chat_context["month_outlook"] = build_month_outlook(
                natal_data["planet_positions"] + natal_data.get("angles", []),
                when.year, when.month, rules_by_point=rules,
            )
        except Exception as exc:  # noqa: BLE001
            print("Month outlook failed:", repr(exc))

    # How much answer does this deserve? Decided from the question and the
    # thread, before the prompt is assembled — because the honest way to get a
    # one-line reply is to stop shipping three thousand tokens of chart with it.
    tier = classify_tier(data.question, chat_context["history"])
    # Being mid-conversation does not make a question small. Forcing every
    # follow-up to tier 3 here — before the classifier had even run — meant a
    # whole thread answered in eighty words a turn however much was at stake:
    # "do you think he'll regret it?" and "what does his chart say?" got the
    # same budget as "so yes??". classify_tier already recognises the short
    # leaning follow-ups that genuinely belong there, and repetition is caught
    # in draft review, which is where it belongs.
    if tier is None:
        # Greetings and mid-thread follow-ups are certain from the text alone.
        # Everything else is put to a cheap model, because guessing weight from
        # length is what made real questions come back bland.
        recent = "\n".join(
            f"{m['role']}: {m['content'][:200]}" for m in chat_context["history"][-3:-1]
        )
        tier = classify_answer_tier(data.question, recent, user_id=user_id) or 4
    # Now the tier is settled, let it set the size the draft is reviewed
    # against, so the ceiling and the review agree about how long this is.
    apply_tier(state, tier, requested_detail(data.question))
    if tier == 1 and not image_context:
        # A social turn needs the exchange, not astrological evidence to fill
        # the silence. Keep history so laughter or a symbol is read in context.
        chat_context = {
            "question": chat_context["question"],
            "history": chat_context["history"],
        }
    elif tier == 2 and not image_context:
        sky = chat_context.get("sky_now") or {}
        chat_context = {
            "question": chat_context["question"],
            "history": chat_context["history"],
            "birth_time_known": chat_context["birth_time_known"],
            "personal_planets": [
                p for p in chat_context.get("personal_planets", [])
                if p["planet"] in {"Sun", "Moon", "Mercury", "Venus", "Mars"}
            ],
            # A short answer still has to be about something. Without a live
            # transit there is nothing true and particular to say, and "the Moon
            # is in Gemini" on its own is what bland sounds like.
            "active_transits": (chat_context.get("active_transits") or [])[:3],
            "sky_now": {
                "moon": sky.get("moon"),
                "retrograde_now": sky.get("retrograde_now"),
                "notable_event": sky.get("notable_event"),
                "transits_through_houses": (sky.get("transits_through_houses") or [])[:3],
            },
        }
    chat_context["sources"] = {
        key: source for key, source in {
            "ascendant": "natal", "midheaven": "natal", "personal_planets": "natal",
            "relevant_planets": "natal", "relevant_aspects": "natal", "chart_structure": "natal",
            "active_transits": "transit_to_natal", "relevant_transits": "transit_to_natal",
            "predictive_timeline": "transit_to_natal", "transits_on_asked_date": "transit_to_natal",
            "month_outlook": "transit_to_natal", "prediction": "transit_to_natal_interpretation",
            "sky_now": "current_sky_and_transits_through_natal_houses",
        }.items() if key in chat_context
    }
    chat_context["conversation"] = state
    chat_context["answer_tier"] = tier
    chat_context["conversation_cue"] = conversational_cue(data.question)

    return {
        "user_id": user_id,
        "tier": tier,
        "tier_config": tier_config,
        "max_output_tokens": answer_ceiling(data.question, tier, state),
        "model": model,
        "effort": effort,
        "images": images_for_model or None,
        "image_tokens": image_tokens,
        "question_type": question_type,
        "chat_context": chat_context,
    }


class InviteRequest(BaseModel):
    label: str
    person_name: str = ""


class InviteFillRequest(BaseModel):
    person_name: str
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True
    relationship_type: str | None = None


@app.post("/invites")
def make_invite(data: InviteRequest, current_user: dict = Depends(get_current_user)):
    """Create a link to send someone, asking for their birth details."""
    # Refuse now rather than after they have filled the form in — being told
    # your details were rejected because someone else is out of slots is a
    # miserable way to meet the product.
    check_people_limit(
        get_user_tier(current_user["id"]),
        len(list_profiles_by_owner(current_user["id"])),
    )
    token = create_invite(current_user["id"], data.label, data.person_name)
    return {
        "token": token,
        "url": f"{frontend_base()}/invite/{token}",
        "expires_in_days": 14,
    }


@app.get("/invites")
def list_pending_invites(current_user: dict = Depends(get_current_user)):
    return {"invites": pending_invites(current_user["id"])}


@app.get("/invite/{token}")
def read_invite(token: str):
    """What the person opening the link sees. No account needed."""
    invite = peek_invite(token)
    if not invite:
        raise HTTPException(status_code=404, detail="This link has expired or has already been used.")
    return invite


@app.post("/invite/{token}")
def fill_invite(token: str, data: InviteFillRequest):
    """Someone filling in their own birth details from a link."""
    if not peek_invite(token):
        raise HTTPException(status_code=404, detail="This link has expired or has already been used.")
    validate_birth_input(data)
    accept_invite(token, data.model_dump())
    return {"message": "Thank you — your details are saved."}


def _answer_prepared(prep):
    if "calculated_answer" in prep:
        return prep["calculated_answer"], 0
    return reviewed_answer(
        generate_astrologer_answer, build_ask_astrologer_user(prep["chat_context"]), prep["chat_context"],
        on_repair=lambda: check_model_allowance(prep["user_id"], get_user_tier(prep["user_id"]), model_key_for_id(prep["model"])),
        # A city ranking never depends on the model getting it right: if the
        # draft can't be fixed, the calculated report is served as written.
        fallback=prep.get("report_fallback"),
        model=prep["model"], system=build_ask_astrologer_system(), effort=prep["effort"],
        images=prep["images"], user_id=prep["user_id"], max_output_tokens=prep["max_output_tokens"],
    )


@app.post("/ask-astrologer")
def ask_astrologer(
    data: AstrologyQuestionRequest,
    current_user: dict = Depends(get_current_user),
):
    prep = _prepare_astrologer_call(data, current_user)

    answer, tokens = _answer_prepared(prep)
    # The inspection pass is billed too — it is a real call on the user's behalf.
    record_usage(prep["user_id"], tokens + prep["image_tokens"])

    return {
        "message": "Astrologer answer generated",
        "question": data.question,
        "question_type": prep["question_type"],
        "answer_tier": prep["tier"],
        "context": prep["chat_context"],
        "answer": answer,
        "tier": prep["tier_config"]["label"],
    }
@app.post("/ask-astrologer/stream")
def ask_astrologer_stream(
    data: AstrologyQuestionRequest,
    current_user: dict = Depends(get_current_user),
):
    """SSE-compatible response; review the complete draft before displaying it."""
    prep = _prepare_astrologer_call(data, current_user)

    def event(name: str, payload: dict) -> str:
        return f"event: {name}\ndata: {json.dumps(payload)}\n\n"

    def events():
        try:
            answer, tokens = _answer_prepared(prep)
            record_usage(prep["user_id"], tokens + prep["image_tokens"])
            yield event("delta", {"text": answer})
            yield event("done", {"question_type": prep["question_type"], "tier": prep["tier_config"]["label"]})
        except HTTPException as exc:
            yield event("error", {"detail": exc.detail})
        except Exception:
            yield event("error", {"detail": "The astrologer is temporarily unavailable. Please try again in a moment."})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Keep the SSE completion/error envelope unbuffered by the proxy.
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/compatibility")
def get_compatibility(data: CompatibilityRequest):
    person_1_chart = build_natal_chart_data(data.person_1)
    person_2_chart = build_natal_chart_data(data.person_2)

    synastry_aspects = get_synastry_aspects(
        person_1_chart["planet_positions"],
        person_2_chart["planet_positions"]
    )
    synastry_engine = build_synastry_engine(
        person_1_chart,
        person_2_chart,
        synastry_aspects
    )

    return {
        "message": "Compatibility calculated",
        "person_1": {
            "input_data": data.person_1.model_dump(),
            "ascendant": person_1_chart["ascendant"],
            "planet_positions": person_1_chart["planet_positions"]
        },
        "person_2": {
            "input_data": data.person_2.model_dump(),
            "ascendant": person_2_chart["ascendant"],
            "planet_positions": person_2_chart["planet_positions"]
        },
        "synastry_aspects": synastry_aspects[:20],
        "synastry_engine": synastry_engine
    }
@app.post("/compatibility-reading")
def compatibility_reading(
    data: CompatibilityRequest,
    current_user: dict = Depends(get_current_user),
):
    tier_config = check_usage(current_user["id"])

    person_1_chart = build_natal_chart_data(data.person_1)
    person_2_chart = build_natal_chart_data(data.person_2)

    synastry_aspects = get_synastry_aspects(
        person_1_chart["planet_positions"],
        person_2_chart["planet_positions"]
    )
    synastry_engine = build_synastry_engine(
        person_1_chart,
        person_2_chart,
        synastry_aspects
    )

    context = build_compatibility_context(
        person_1_chart,
        person_2_chart,
        synastry_aspects,
        synastry_engine
    )

    prompt = build_compatibility_prompt(context)

    review_context = attach_conversation({}, "Give me a brief overview of how we relate to each other.")
    reading, tokens = reviewed_answer(generate_compatibility_reading, prompt, review_context,
                                     model=tier_config["model"], user_id=current_user["id"])
    record_usage(current_user["id"], tokens)

    return {
        "message": "Compatibility reading generated",
        "context": context,
        "reading": reading,
        "tier": tier_config["label"],
    }

@app.post("/ask-compatibility")
def ask_compatibility(
    data: AskCompatibilityRequest,
    current_user: dict = Depends(get_current_user),
    profile_id: int | None = None,
):
    user_id = current_user["id"]
    tier_config = check_usage(user_id)
    tier = get_user_tier(user_id)
    model = resolve_model(tier, data.model)
    check_model_allowance(user_id, tier, model_key_for_id(model))

    person_1_chart = build_natal_chart_data(data.person_1)
    person_2_chart = build_natal_chart_data(data.person_2)

    synastry_aspects = get_synastry_aspects(
        person_1_chart["planet_positions"],
        person_2_chart["planet_positions"]
    )
    synastry_engine = build_synastry_engine(
        person_1_chart,
        person_2_chart,
        synastry_aspects
    )

    # What this person is to them, in their own words. A chart cannot tell a
    # friendship from a romance, so without this a reading full of fifth-house
    # contacts gets called a crush — which is what happened.
    described_as = None
    if profile_id is not None:
        saved = get_profile_by_id(profile_id)
        if saved and saved.get("owner_user_id") == current_user["id"]:
            described_as = saved.get("relationship_type") or saved.get("label")

    # Synastry alone cannot answer "why now" — it describes a permanent
    # dynamic. The transits are what make a timing question answerable.
    timing = build_relationship_timing(
        person_1_chart["planet_positions"] + person_1_chart.get("angles", []),
        person_2_chart["planet_positions"] + person_2_chart.get("angles", []),
        synastry_aspects,
    )

    context = build_ask_compatibility_context(
        person_1_chart,
        person_2_chart,
        synastry_aspects,
        synastry_engine,
        data.question,
        [msg.model_dump() for msg in (data.history or [])],
        person_1_name=data.person_1_name or current_user.get("name") or "the person asking",
        person_2_name=data.person_2_name or "the other person",
        relationship_type=described_as,
    )
    context["timing"] = timing
    context["requested_detail"] = requested_detail(data.question)
    facts = {"user": {k: current_user[k] for k in ("name", "birth_date") if current_user.get(k)}}
    if profile_id is not None:
        saved = get_profile_by_id(profile_id)
        if saved and saved.get("owner_user_id") == user_id:
            facts["other_person"] = {k: saved[k] for k in ("person_name", "birth_date", "relationship_type", "label") if saved.get(k)}
    attach_conversation(context, data.question, data.history, facts)
    state = context["conversation"]
    # Judged on what was asked, like everywhere else. Hard-coding 3 for every
    # follow-up meant a compatibility thread shrank to eighty words a turn
    # however much the second message actually carried.
    context["answer_tier"] = classify_tier(data.question, data.history) or (
        3 if state["kind"] == "follow_up" else 4)
    prompt = build_ask_compatibility_prompt(context)
    answer, tokens = reviewed_answer(
        generate_compatibility_answer, prompt, context, model=model, user_id=user_id,
        on_repair=lambda: check_model_allowance(user_id, tier, model_key_for_id(model)),
        max_output_tokens=answer_ceiling(data.question, context["answer_tier"], state),
    )
    record_usage(user_id, tokens)

    return {
        "message": "Compatibility answer generated",
        "question": data.question,
        "context": context,
        "answer": answer,
        "tier": tier_config["label"],
    }

@app.post("/ask-saved-compatibility")
def ask_saved_compatibility(
    data: AskSavedCompatibilityRequest,
    current_user: dict = Depends(get_current_user),
):
    owner = current_user
    profile = get_profile_by_id(data.profile_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    # A saved person's birth details are private to whoever saved them.
    require_self(current_user, profile["owner_user_id"])

    compatibility_data = AskCompatibilityRequest(
        person_1=PersonBirthData(
            birth_date=owner["birth_date"],
            birth_time=owner["birth_time"],
            birth_place=owner["birth_place"],
            birth_time_known=bool(owner.get("birth_time_known", 1)),
        ),
        person_2=PersonBirthData(
            birth_date=profile["birth_date"],
            birth_time=profile["birth_time"],
            birth_place=profile["birth_place"],
            birth_time_known=bool(profile.get("birth_time_known", 1)),
        ),
        question=data.question,
        history=data.history,
        user_id=owner["id"],
        model=data.model,
        person_1_name=owner.get("name") or "the person asking",
        # The label is what they call this person ("My boyfriend"); the name is
        # who it actually is. Both help the astrologer speak naturally.
        person_2_name=profile.get("person_name") or profile.get("label") or "the other person",
    )

    # Called directly, so the dependency has to be handed over explicitly.
    return ask_compatibility(
        compatibility_data, current_user=current_user, profile_id=data.profile_id
    )

@app.post("/signup", response_model=AuthUserResponse)
def signup(data: SignupRequest):
    rate_limit("signup-email", data.email.casefold(), 3, 3600)
    check_password(data.password)
    validate_birth_input(data)

    user = create_account(
        name=data.name,
        email=data.email,
        password=data.password,
        birth_date=data.birth_date,
        birth_time=data.birth_time if data.birth_time_known else UNKNOWN_BIRTH_TIME,
        birth_place=data.birth_place,
        birth_time_known=data.birth_time_known,
    )

    if not user:
        raise HTTPException(status_code=400, detail="Email already exists")

    # New accounts start unverified and are sent a confirmation link. This is
    # soft — they can use Zoli right away; the email just confirms we can reach
    # them, which is what makes a password reset trustworthy later.
    _send_verification_email(user["id"], user["email"], user["name"])

    return {**user, "token": create_session(user["id"])}


def _send_verification_email(user_id: int, email: str, name: str) -> None:
    token = issue_token(user_id, PURPOSE_VERIFY)
    link = f"{frontend_base()}/verify-email?token={token}"
    send_verification(email, name, link)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class TokenOnlyRequest(BaseModel):
    token: str


@app.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    """Email a reset link — but never reveal whether the address has an account.

    The response is identical whether or not the email is registered, so this
    can't be used to discover who has a Zoli account.
    """
    rate_limit("reset-email", data.email.casefold(), 1, 60)
    user_id = find_user_id_by_email(data.email)
    if user_id:
        user = get_user_by_id(user_id)
        token = issue_token(user_id, PURPOSE_RESET)
        link = f"{frontend_base()}/reset-password?token={token}"
        send_password_reset(data.email.strip(), (user or {}).get("name", ""), link)

    return {
        "message": "If that email has an account, a reset link is on its way.",
        "email_configured": email_configured(),
    }


@app.post("/reset-password", response_model=AuthUserResponse)
def reset_password(data: ResetPasswordRequest):
    """Set a new password from a valid reset link, then sign in fresh."""
    # Validate the new password BEFORE spending the token, so a weak choice
    # doesn't burn the one-time link and strand the user.
    check_password(data.password)

    user_id = reset_password_by_token(data.token, data.password)
    if not user_id:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user = get_user_by_id(user_id)
    public = {key: user[key] for key in PUBLIC_USER_FIELDS if key in user}
    return {**public, "token": create_session(user_id)}


@app.post("/verify-email")
def verify_email(data: TokenOnlyRequest):
    """Mark an email confirmed from the link in the verification message."""
    user_id = consume_token(data.token, PURPOSE_VERIFY)
    if not user_id:
        raise HTTPException(status_code=400, detail="This confirmation link is invalid or has expired.")

    conn = get_db_connection()
    conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"message": "Email confirmed. Thank you."}


@app.post("/resend-verification")
def resend_verification(current_user: dict = Depends(get_current_user)):
    rate_limit("verify-email", str(current_user["id"]), 1, 60)
    """Send the confirmation email again, for someone who lost the first."""
    if current_user.get("email_verified"):
        return {"message": "Your email is already confirmed."}
    _send_verification_email(current_user["id"], current_user["email"], current_user["name"])
    return {"message": "Confirmation email sent.", "email_configured": email_configured()}


@app.post("/login", response_model=AuthUserResponse)
def login(data: LoginRequest):
    rate_limit("login-email", data.email.casefold(), 10, 900)
    user = login_user(
        email=data.email,
        password=data.password
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {**user, "token": create_session(user["id"])}


@app.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        delete_session(authorization[7:].strip())
    return {"message": "Logged out"}


@app.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.get("/cosmic-events")
def cosmic_events(current_user: dict = Depends(get_current_user)):
    """Notable sky events, scored against the signed-in user's own chart.

    Powers the app speaking up unprompted when something big is happening.
    """
    natal_data = build_natal_chart_data(
        BirthData(
            birth_date=current_user["birth_date"],
            birth_time=current_user["birth_time"],
            birth_place=current_user["birth_place"],
            birth_time_known=bool(current_user.get("birth_time_known", 1)),
        )
    )
    return build_cosmic_events(
        natal_planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
    )


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    require_self(current_user, user_id)
    return current_user


@app.get("/users/{user_id}/natal-chart")
def get_saved_user_natal_chart(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    require_self(current_user, user_id)

    birth_data = BirthData(
        birth_date=current_user["birth_date"],
        birth_time=current_user["birth_time"],
        birth_place=current_user["birth_place"],
        birth_time_known=bool(current_user.get("birth_time_known", 1)),
    )

    natal_data = build_natal_chart_data(birth_data)

    return {
        "message": "Saved user natal chart calculated",
        # public_user() keeps the password hash and usage counters out of this.
        "user": public_user(current_user),
        **natal_data
    }
@app.get("/profiles/{owner_user_id}")
def get_profiles(owner_user_id: int, current_user: dict = Depends(get_current_user)):
    require_self(current_user, owner_user_id)
    return list_profiles_by_owner(owner_user_id)


@app.get("/chat-sessions/{owner_user_id}")
def get_chat_sessions(owner_user_id: int, current_user: dict = Depends(get_current_user)):
    require_self(current_user, owner_user_id)
    return list_chat_sessions(owner_user_id)


@app.get("/chat-sessions/session/{session_id}")
def get_chat_session(session_id: int, current_user: dict = Depends(get_current_user)):
    session = get_chat_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    require_self(current_user, session["owner_user_id"])
    return session


@app.post("/chat-sessions")
def create_chat_session_endpoint(
    data: ChatSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    require_owned_profile(data.profile_id, current_user["id"])
    session = create_chat_session(
        # Ownership comes from the token, not the request body.
        owner_user_id=current_user["id"],
        profile_id=data.profile_id,
        title=data.title,
        messages=[message.model_dump() for message in data.messages],
    )
    return session


@app.patch("/chat-sessions/{session_id}")
def update_chat_session_endpoint(
    session_id: int,
    data: ChatSessionUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    existing = get_chat_session_by_id(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Chat session not found")
    require_self(current_user, existing["owner_user_id"])

    require_owned_profile(data.profile_id, current_user["id"])
    session = update_chat_session(
        session_id=session_id,
        title=data.title,
        profile_id=data.profile_id,
        messages=[message.model_dump() for message in data.messages],
    )
    return session


@app.delete("/chat-sessions/{session_id}")
def delete_chat_session_endpoint(
    session_id: int,
    current_user: dict = Depends(get_current_user),
):
    existing = get_chat_session_by_id(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Chat session not found")
    require_self(current_user, existing["owner_user_id"])

    delete_chat_session_by_id(session_id)
    return {"message": "Conversation deleted"}


@app.get("/me/export")
def export_my_data(current_user: dict = Depends(get_current_user)):
    """Everything we hold about the signed-in person, in a portable form."""
    data = export_user_data(current_user["id"])
    if data is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return data


@app.delete("/me")
def delete_my_account(current_user: dict = Depends(get_current_user)):
    """Erase the account and everything attached to it. Not reversible."""
    deleted = delete_user_account(current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account deleted"}


@app.post("/profiles")
def save_profile(
    data: SaveProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    validate_birth_input(data)
    # Free saves one person, standard three, premium unlimited.
    existing = list_profiles_by_owner(current_user["id"])
    check_people_limit(get_user_tier(current_user["id"]), len(existing))

    return create_profile(
        owner_user_id=current_user["id"],
        label=data.label,
        person_name=data.person_name,
        relationship_type=data.relationship_type,
        birth_date=data.birth_date,
        birth_time=data.birth_time if data.birth_time_known else UNKNOWN_BIRTH_TIME,
        birth_place=data.birth_place,
        birth_time_known=data.birth_time_known,
    )

@app.get("/profiles/profile/{profile_id}")
def get_profile(profile_id: int, current_user: dict = Depends(get_current_user)):
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    require_self(current_user, profile["owner_user_id"])
    return profile

def validate_birth_input(data) -> None:
    if not get_location_data(data.birth_place):
        raise HTTPException(400, "Could not find that birth place. Please use a city and country.")


def clean_birth_edits(changes: dict, existing: dict) -> dict:
    """Validate a partial birth-details edit and normalise the time.

    Saving an unrecognised birth place would break every later chart request
    for that person, so the place is geocoded here and rejected up front. The
    time is normalised the same way signup does it, so "unknown" never lands
    in the database as an empty string.
    """
    edits = {k: v for k, v in changes.items() if v is not None}

    place = edits.get("birth_place")
    if place is not None:
        if not place.strip():
            raise HTTPException(status_code=400, detail="Please enter a birth place.")
        if not get_location_data(place):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not find that birth place. Use a clear city and country, "
                    "for example 'Paris, France'."
                ),
            )

    # The flag and the time are read together: whether a time is required
    # depends on the flag as it will be *after* this edit, not as it was.
    time_known = edits.get("birth_time_known", bool(existing.get("birth_time_known", 1)))
    if not time_known:
        edits["birth_time"] = UNKNOWN_BIRTH_TIME
    elif "birth_time" in edits and not edits["birth_time"].strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter a birth time, or tick that it's unknown.",
        )

    return edits


@app.patch("/me", response_model=UserResponse)
def update_me(
    data: UpdateMeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit your own name and birth details.

    People guess a birth time at signup, or find the real one later on a birth
    certificate — without this the wrong chart is permanent.
    """
    edits = clean_birth_edits(data.model_dump(exclude_unset=True), current_user)

    if "name" in edits and not edits["name"].strip():
        raise HTTPException(status_code=400, detail="Please enter your name.")

    updated = update_user(current_user["id"], edits)
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found.")
    return updated


@app.patch("/profiles/{profile_id}")
def edit_profile(
    profile_id: int,
    data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    """Edit someone you saved — same reasons as your own details."""
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    require_self(current_user, profile["owner_user_id"])

    edits = clean_birth_edits(data.model_dump(exclude_unset=True), profile)

    for field, message in (("label", "Please give them a label."),
                           ("person_name", "Please enter their name.")):
        if field in edits and not edits[field].strip():
            raise HTTPException(status_code=400, detail=message)

    updated = update_profile(profile_id, edits)
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found")
    return updated


@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, current_user: dict = Depends(get_current_user)):
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    require_self(current_user, profile["owner_user_id"])

    deleted = delete_profile_by_id(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deleted"}


# ---- Attached images ----

# Free stays text-only. Images cost real tokens on every question they ride
# along with, and this is the clearest thing a paid tier actually buys.
IMAGE_TIERS = {"standard", "premium"}


def require_image_tier(user_id: int) -> None:
    if get_user_tier(user_id) not in IMAGE_TIERS:
        raise HTTPException(
            status_code=403,
            detail="Attaching pictures is part of a paid plan. Upgrade to send charts and screenshots.",
        )


@app.post("/attachments")
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Store one image so a question can refer to it."""
    require_image_tier(current_user["id"])
    rate_limit("uploads", str(current_user["id"]), 10, 60)

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="That file type isn't supported. Send a PNG, JPEG, WebP or GIF.",
        )

    # Read with a ceiling rather than trusting a declared length, which the
    # client controls.
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"That image is too large. Keep it under {MAX_BYTES // (1024 * 1024)}MB.",
        )
    if not content:
        raise HTTPException(status_code=400, detail="That file appears to be empty.")

    return await run_in_threadpool(save_attachment, current_user["id"], content, content_type)


@app.get("/attachments/{attachment_id}")
def serve_attachment(
    attachment_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Return the image itself, to the person who uploaded it and nobody else."""
    attachment = get_attachment(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Image not found")
    require_self(current_user, attachment["owner_user_id"])

    content = read_attachment_bytes(attachment)
    if content is None:
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(
        content=content,
        media_type=attachment["content_type"],
        # Private: it may be a screenshot of someone's messages, so no shared
        # cache should ever hold a copy.
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.delete("/attachments/{attachment_id}")
def remove_attachment(
    attachment_id: int,
    current_user: dict = Depends(get_current_user),
):
    if not delete_attachment(attachment_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Image not found")
    return {"message": "Image deleted"}


# ---- The sky itself ----

def _sky_for(current_user: dict, utc_dt=None, at: tuple | None = None) -> dict:
    """Build a sky view.

    The vantage point is their birth place unless `at` says otherwise. That
    distinction matters: the sky they were born under is fixed to where they
    were born, but the sky *now* is above wherever they are standing, which is
    very often somewhere else entirely.
    """
    natal_data = build_natal_chart_data(
        BirthData(
            birth_date=current_user["birth_date"],
            birth_time=current_user["birth_time"],
            birth_place=current_user["birth_place"],
            birth_time_known=bool(current_user.get("birth_time_known", 1)),
        )
    )
    location = natal_data["location_data"]
    moment = utc_dt or datetime.fromisoformat(natal_data["utc_birth_time"])

    if at is not None:
        latitude, longitude, label, zone = at
    else:
        latitude = location["latitude"]
        longitude = location["longitude"]
        label = current_user["birth_place"]
        zone = location.get("timezone")

    sky = build_sky_view(moment, latitude, longitude)
    sky["place"] = label
    sky["timezone"] = zone

    # The hour as a clock on the wall there would have read it. "Night" is
    # wrong for half of all births, so the page needs to know it was a morning.
    if zone:
        try:
            local = moment.astimezone(ZoneInfo(zone))
            sky["local_hour"] = local.hour
            sky["local_time"] = local.strftime("%H:%M")
        except Exception:
            pass
    return sky


@app.get("/sky-at-birth")
def sky_at_birth(current_user: dict = Depends(get_current_user)):
    """The sky over their birthplace at the moment they were born."""
    sky = _sky_for(current_user)
    # Without a real birth time the chart is cast for noon, so this would be a
    # picture of the wrong sky. Say so rather than quietly showing midday.
    sky["birth_time_known"] = bool(current_user.get("birth_time_known", 1))
    return sky


@app.get("/sky-now")
def sky_now(
    latitude: float | None = None,
    longitude: float | None = None,
    current_user: dict = Depends(get_current_user),
):
    """The sky right now — over wherever they are, or their birthplace.

    Coordinates are optional because asking the browser for a location is a
    permission prompt, and someone who declines should still get a sky.
    """
    at = None
    if latitude is not None and longitude is not None:
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise HTTPException(status_code=400, detail="That location isn't on Earth.")
        zone, label = describe_coordinates(latitude, longitude)
        at = (latitude, longitude, label, zone)

    return _sky_for(current_user, utc_dt=datetime.now(timezone.utc), at=at)


# ---- Subscription / tiers ----

@app.get("/subscription/tiers")
def list_tiers():
    """Public endpoint that lists tier metadata for the pricing page."""
    return {
        tier: {
            "label": config["label"],
            "model": config["model"],
            "daily_token_limit": config["daily_token_limit"],
        }
        for tier, config in TIERS.items()
    }


@app.get("/subscription/usage/{user_id}")
def usage_for_user(user_id: int, current_user: dict = Depends(get_current_user)):
    require_self(current_user, user_id)
    return get_usage_status(user_id)


def _ephemeris_status() -> dict:
    from app.astrology_engine import _EPHE_DIR
    try:
        files = sorted(os.listdir(_EPHE_DIR)) if os.path.isdir(_EPHE_DIR) else []
    except OSError:
        files = []
    # Actually try the calculation rather than reporting on the files and
    # inferring. Two deploys have now been spent guessing why Chiron is
    # missing; the exception itself is the only thing that settles it.
    chiron = "ok"
    try:
        import swisseph as swe
        from app.astrology_engine import use_bundled_ephemeris
        use_bundled_ephemeris()
        swe.calc_ut(swe.julday(1999, 3, 2, 5.25), swe.CHIRON, swe.FLG_SWIEPH | swe.FLG_SPEED)
    except Exception as exc:  # noqa: BLE001
        chiron = f"{type(exc).__name__}: {exc}"[:300]

    return {
        "dir": _EPHE_DIR,
        "exists": os.path.isdir(_EPHE_DIR),
        "files": files,
        "chiron": chiron,
    }


def _require_admin(x_admin_secret: str | None) -> None:
    """Shared gate for every admin route: a matching ADMIN_SECRET header."""
    expected = os.getenv("ADMIN_SECRET")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoint disabled: set ADMIN_SECRET in .env to enable.",
        )
    if not secrets.compare_digest((x_admin_secret or "").encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid admin secret.")


class BugReportRequest(BaseModel):
    message: str
    page: str | None = None


@app.post("/bug-reports")
def report_a_bug(
    data: BugReportRequest,
    user_agent: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    """Someone telling us something is wrong, in their own words.

    Deliberately open to anyone signed in or not: a bug that stops you logging
    in is exactly the one you most need to hear about, and a report form that
    requires an account cannot receive it.
    """
    message = (data.message or "").strip()
    if len(message) < 3:
        raise HTTPException(status_code=400, detail="Tell us a little about what happened.")

    user_id, email = None, None
    if authorization and authorization.lower().startswith("bearer "):
        user_id = get_user_id_for_token(authorization.split(" ", 1)[1])
        if user_id:
            email = (get_user_by_id(user_id) or {}).get("email")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO bug_reports (user_id, email, message, page, user_agent, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, email, message[:4000], (data.page or "")[:300],
         (user_agent or "")[:300], datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return {"message": "Thank you — that's been logged."}


@app.get("/admin/bug-reports")
def admin_bug_reports(
    limit: int = 50,
    x_admin_secret: str | None = Header(default=None),
):
    """What people have said is broken, newest first."""
    _require_admin(x_admin_secret)
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, user_id, email, message, page, user_agent, resolved, created_at "
        "FROM bug_reports ORDER BY id DESC LIMIT ?",
        (min(limit, 200),),
    ).fetchall()
    unresolved = conn.execute(
        "SELECT COUNT(*) FROM bug_reports WHERE resolved = 0"
    ).fetchone()[0]
    conn.close()
    return {"open": unresolved, "reports": [dict(r) for r in rows]}


@app.patch("/admin/bug-reports/{report_id}")
def admin_resolve_bug(
    report_id: int,
    x_admin_secret: str | None = Header(default=None),
):
    """Mark one as dealt with, so the list stays a list of things to do."""
    _require_admin(x_admin_secret)
    conn = get_db_connection()
    conn.execute("UPDATE bug_reports SET resolved = 1 WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return {"message": "Marked as done."}


@app.get("/admin/errors")
def admin_errors(
    limit: int = 50,
    x_admin_secret: str | None = Header(default=None),
):
    """What has been failing, newest first, with a summary to glance at."""
    _require_admin(x_admin_secret)
    return {"summary": error_summary(), "errors": recent_errors(min(limit, 200))}


@app.get("/admin/backups")
def admin_list_backups(x_admin_secret: str | None = Header(default=None)):
    """The copies on disk, newest first."""
    _require_admin(x_admin_secret)
    return {"backups": list_backups(), "directory": str(backup_dir())}


@app.post("/admin/backups")
def admin_make_backup(x_admin_secret: str | None = Header(default=None)):
    """Take one now, rather than waiting for tonight."""
    _require_admin(x_admin_secret)
    return create_backup()


@app.get("/admin/backups/{name}")
def admin_download_backup(name: str, x_admin_secret: str | None = Header(default=None)):
    """Download a copy, so a backup can live somewhere that isn't Render."""
    _require_admin(x_admin_secret)
    # Only ever a file this service wrote: the name is matched against the
    # listing rather than joined onto a path, so nothing can be traversed out
    # of the backup directory.
    if name not in {entry["name"] for entry in list_backups()}:
        raise HTTPException(status_code=404, detail="No such backup.")
    return FileResponse(
        backup_dir() / name,
        media_type="application/octet-stream",
        filename=name,
    )


@app.get("/admin/usage")
def admin_usage(x_admin_secret: str | None = Header(default=None)):
    """What the app has cost, per model and per user, this month and all time.

    The provider dashboards can't do per-user — only the app knows who its users
    are. This reads the usage log the app writes on every AI call.
    """
    _require_admin(x_admin_secret)
    return usage_summary()


@app.patch("/admin/users/{user_id}/tier")
def admin_update_tier(
    user_id: int,
    data: TierUpdateRequest,
    x_admin_secret: str | None = Header(default=None),
):
    """Promote/demote a user's subscription tier. Guarded by ADMIN_SECRET env var."""
    _require_admin(x_admin_secret)

    updated = set_user_tier(user_id, data.tier)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Tier updated", "user": updated}


# Three segments, so this can't be captured by /admin/users/{user_id}/tier.
@app.patch("/admin/tier-by-email")
def admin_update_tier_by_email(
    data: TierByEmailRequest,
    x_admin_secret: str | None = Header(default=None),
):
    """Same as above, keyed on email — what you know about a real customer."""
    expected = os.getenv("ADMIN_SECRET")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoint disabled: set ADMIN_SECRET to enable.",
        )
    if not secrets.compare_digest((x_admin_secret or "").encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid admin secret.")

    rate_limit("reset-email", data.email.casefold(), 1, 60)
    user_id = find_user_id_by_email(data.email)
    if user_id is None:
        raise HTTPException(status_code=404, detail="No account with that email.")

    updated = set_user_tier(user_id, data.tier)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Tier updated", "user": updated}
