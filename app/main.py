import os
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
    create_chat_session,
    get_chat_session_by_id,
    list_chat_sessions,
    update_chat_session,
    delete_chat_session_by_id,
    summarize_recent_sessions,
)
from app.account_service import export_user_data, delete_user_account
from app.compatibility_service import get_synastry_aspects, build_synastry_engine
from app.database import init_db, get_db_connection, DB_NAME
from datetime import datetime

from app.celestial_events_service import build_cosmic_events, describe_moon_phase
from app.chart_analysis_service import build_chart_analysis
from app.session_service import (
    create_session,
    delete_session,
    get_user_id_for_token,
    purge_expired_sessions,
)
from app.question_router import (
    classify_question,
    filter_chart_context_by_question_type,
    get_focus_planets,
)
from dotenv import load_dotenv
load_dotenv()
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.astrology_engine import (
    get_planet_positions_from_utc,
    get_houses_and_ascendant,
    add_house_to_planets,
)
from app.aspect_services import get_aspects
from app.location_service import get_location_data
from app.time_service import convert_to_utc
from app.interpretation_service import build_chart_interpretation
from app.transit_service import (
    get_current_transit_positions,
    get_transit_aspects,
    get_transit_houses,
    build_upcoming_transit_timeline,
)
from app.predictive_adapter_service import run_predictive_engine
from app.ai_context_service import (
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
    generate_chart_summary,
    generate_astrologer_answer,
    generate_compatibility_reading,
    generate_compatibility_answer,
)
from app.subscription_service import (
    check_usage,
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

app = FastAPI(title="AI Horoscope API")

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

class BirthData(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    # False when the person doesn't know what time they were born. The chart is
    # then cast for local noon and everything that depends on the exact moment
    # — Ascendant, houses, the Moon's precise degree — is withheld rather than
    # guessed at.
    birth_time_known: bool = True

from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str


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


class AuthUserResponse(BaseModel):
    id: int
    name: str
    email: str
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True
    subscription_tier: str = "free"
    token: str

class UserResponse(BaseModel):
    id: int
    name: str
    birth_date: str
    birth_time: str
    birth_place: str
    birth_time_known: bool = True
    subscription_tier: str = "free"


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
    "birth_time_known", "subscription_tier",
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
    return user


def require_self(current_user: dict, target_user_id: int) -> None:
    """Block reading or writing another account's data."""
    if current_user["id"] != target_user_id:
        raise HTTPException(status_code=403, detail="Not allowed.")


@app.on_event("startup")
def startup():
    init_db()
    purge_expired_sessions()

@app.get("/")
def home():
    return {"message": "AI Horoscope API is running"}


@app.get("/health")
def health_check():
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
        houses = house_data["houses"]
        planets = add_house_to_planets(planets, houses)
    else:
        # Houses and the Ascendant rotate a full circle each day, so without a
        # time they are not approximate — they are unknowable.
        ascendant, houses = None, []
        for planet in planets:
            planet["house"] = None

    aspects = get_aspects(planets)
    interpretation = build_chart_interpretation(planets, aspects)

    return {
        "location_data": location_data,
        "utc_birth_time": utc_dt.isoformat(),
        "birth_time_known": time_known,
        "ascendant": ascendant,
        "houses": houses,
        "planet_positions": planets,
        "aspects": aspects,
        "interpretation": interpretation
    }


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
        natal_planets=natal_data["planet_positions"],
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
        natal_planets=natal_data["planet_positions"],
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
        natal_planets=natal_data["planet_positions"],
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
    summary, tokens = generate_chart_summary(prompt, model=tier_config["model"])
    record_usage(current_user["id"], tokens)

    return {
        "message": "AI chart summary generated",
        "chart_context": chart_context,
        "summary": summary,
        "tier": tier_config["label"],
    }

@app.post("/ask-astrologer")
def ask_astrologer(
    data: AstrologyQuestionRequest,
    current_user: dict = Depends(get_current_user),
):
    # Usage and tier follow the token, so nobody can bill another account.
    user_id = current_user["id"]
    tier_config = check_usage(user_id)
    tier = get_user_tier(user_id)
    model = resolve_model(tier, data.model)
    effort = resolve_effort(tier, data.effort)

    if data.birth_time_known is None:
        data.birth_time_known = bool(current_user.get("birth_time_known", 1))

    natal_data = build_natal_chart_data(data)

    transit_planets = get_current_transit_positions()

    active_transits = get_transit_aspects(
        natal_planets=natal_data["planet_positions"],
        transit_planets=transit_planets
    )

    question_type = classify_question(data.question)
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

    chat_context = {
        "question": data.question,
        "history": [msg.model_dump() for msg in (data.history or [])],
        # Stated up front, not just buried in chart_structure: everything the
        # birth time would have given is null below, and the difference between
        # "unknown" and "absent" is the difference between honest and invented.
        "birth_time_known": natal_data["birth_time_known"],
        **filtered_context,
        "upcoming_transits": build_upcoming_transit_timeline(
            natal_data["planet_positions"],
            max_events=8,
            focus_planets=focus_planets,
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
        "chart_structure": chart_structure,
        # Titles only, so a question can be picked back up across sessions.
        "past_conversations": summarize_recent_sessions(
            user_id, exclude_session_id=data.session_id
        ),
    }

    answer, tokens = generate_astrologer_answer(
        build_ask_astrologer_user(chat_context),
        model=model,
        system=build_ask_astrologer_system(),
        effort=effort,
    )
    record_usage(user_id, tokens)

    return {
        "message": "Astrologer answer generated",
        "question": data.question,
        "question_type": question_type,
        "context": chat_context,
        "answer": answer,
        "tier": tier_config["label"],
    }
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

    reading, tokens = generate_compatibility_reading(prompt, model=tier_config["model"])
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
):
    user_id = current_user["id"]
    tier_config = check_usage(user_id)
    model = resolve_model(get_user_tier(user_id), data.model)

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

    context = build_ask_compatibility_context(
        person_1_chart,
        person_2_chart,
        synastry_aspects,
        synastry_engine,
        data.question,
        [msg.model_dump() for msg in (data.history or [])],
        person_1_name=data.person_1_name or current_user.get("name") or "the person asking",
        person_2_name=data.person_2_name or "the other person",
    )

    prompt = build_ask_compatibility_prompt(context)
    answer, tokens = generate_compatibility_answer(prompt, model=model)
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
    return ask_compatibility(compatibility_data, current_user=current_user)

@app.post("/signup", response_model=AuthUserResponse)
def signup(data: SignupRequest):
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

    return {**user, "token": create_session(user["id"])}


@app.post("/login", response_model=AuthUserResponse)
def login(data: LoginRequest):
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


@app.patch("/admin/users/{user_id}/tier")
def admin_update_tier(
    user_id: int,
    data: TierUpdateRequest,
    x_admin_secret: str | None = Header(default=None),
):
    """Promote/demote a user's subscription tier. Guarded by ADMIN_SECRET env var."""
    expected = os.getenv("ADMIN_SECRET")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoint disabled: set ADMIN_SECRET in .env to enable.",
        )
    if x_admin_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid admin secret.")

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
    if x_admin_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid admin secret.")

    user_id = find_user_id_by_email(data.email)
    if user_id is None:
        raise HTTPException(status_code=404, detail="No account with that email.")

    updated = set_user_tier(user_id, data.tier)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Tier updated", "user": updated}

