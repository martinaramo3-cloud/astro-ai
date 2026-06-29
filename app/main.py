import os
from fastapi.middleware.cors import CORSMiddleware
from app.auth_service import create_account, login_user
from app.user_service import get_user_by_id
from app.profile_service import create_profile, list_profiles_by_owner, get_profile_by_id, delete_profile_by_id
from app.chat_service import create_chat_session, get_chat_session_by_id, list_chat_sessions, update_chat_session
from app.compatibility_service import get_synastry_aspects, build_synastry_engine
from app.database import init_db
from app.question_router import classify_question, filter_chart_context_by_question_type
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Header, HTTPException
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
)
from app.predictive_adapter_service import run_predictive_engine
from app.ai_context_service import (
    build_ai_chart_context,
    build_summary_prompt,
    build_weekly_horoscope_prompt,
    build_ask_astrologer_prompt,
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
    resolve_model,
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
    history: Optional[List[ChatMessage]] = None
    user_id: Optional[int] = None
    model: Optional[str] = None  # "fast" | "smart" | "deep"; gated by tier server-side


class PredictiveRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    topic: Optional[str] = None

class PersonBirthData(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str

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
    model: Optional[str] = None  # "fast" | "smart" | "deep"; gated by tier server-side

class SaveProfileRequest(BaseModel):
    owner_user_id: int
    label: str
    person_name: str
    relationship_type: str | None = None
    birth_date: str
    birth_time: str
    birth_place: str

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
    subscription_tier: str = "free"

class UserResponse(BaseModel):
    id: int
    name: str
    birth_date: str
    birth_time: str
    birth_place: str
    subscription_tier: str = "free"


class TierUpdateRequest(BaseModel):
    tier: str


class ChartSummaryRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    user_id: Optional[int] = None

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def home():
    return {"message": "AI Horoscope API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


def build_natal_chart_data(data: BirthData):
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
            data.birth_time,
            location_data["timezone"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    planets = get_planet_positions_from_utc(utc_dt)

    house_data = get_houses_and_ascendant(
        utc_dt,
        location_data["latitude"],
        location_data["longitude"]
    )

    planets_with_houses = add_house_to_planets(
        planets,
        house_data["houses"]
    )

    aspects = get_aspects(planets_with_houses)

    interpretation = build_chart_interpretation(
        planets_with_houses,
        aspects
    )

    return {
        "location_data": location_data,
        "utc_birth_time": utc_dt.isoformat(),
        "ascendant": house_data["ascendant"],
        "houses": house_data["houses"],
        "planet_positions": planets_with_houses,
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
def chart_summary(data: ChartSummaryRequest):
    tier_config = check_usage(data.user_id)

    natal_data = build_natal_chart_data(
        BirthData(
            birth_date=data.birth_date,
            birth_time=data.birth_time,
            birth_place=data.birth_place,
        )
    )

    chart_context = build_ai_chart_context(
        planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
        aspects=natal_data["aspects"]
    )

    prompt = build_summary_prompt(chart_context)
    summary, tokens = generate_chart_summary(prompt, model=tier_config["model"])
    record_usage(data.user_id, tokens)

    return {
        "message": "AI chart summary generated",
        "chart_context": chart_context,
        "summary": summary,
        "tier": tier_config["label"],
    }

@app.post("/ask-astrologer")
def ask_astrologer(data: AstrologyQuestionRequest):
    tier_config = check_usage(data.user_id)
    model = resolve_model(get_user_tier(data.user_id), data.model)

    natal_data = build_natal_chart_data(data)

    transit_planets = get_current_transit_positions()

    active_transits = get_transit_aspects(
        natal_planets=natal_data["planet_positions"],
        transit_planets=transit_planets
    )

    question_type = classify_question(data.question)

    filtered_context = filter_chart_context_by_question_type(
        question_type=question_type,
        planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
        aspects=natal_data["aspects"],
        transits=active_transits
    )

    chat_context = {
        "question": data.question,
        "history": [msg.model_dump() for msg in (data.history or [])],
        **filtered_context,
    }

    prompt = build_ask_astrologer_prompt(chat_context)
    answer, tokens = generate_astrologer_answer(prompt, model=model)
    record_usage(data.user_id, tokens)

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
def compatibility_reading(data: CompatibilityRequest):
    tier_config = check_usage(data.user_id)

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
    record_usage(data.user_id, tokens)

    return {
        "message": "Compatibility reading generated",
        "context": context,
        "reading": reading,
        "tier": tier_config["label"],
    }

@app.post("/ask-compatibility")
def ask_compatibility(data: AskCompatibilityRequest):
    tier_config = check_usage(data.user_id)
    model = resolve_model(get_user_tier(data.user_id), data.model)

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
        [msg.model_dump() for msg in (data.history or [])]
    )

    prompt = build_ask_compatibility_prompt(context)
    answer, tokens = generate_compatibility_answer(prompt, model=model)
    record_usage(data.user_id, tokens)

    return {
        "message": "Compatibility answer generated",
        "question": data.question,
        "context": context,
        "answer": answer,
        "tier": tier_config["label"],
    }

@app.post("/ask-saved-compatibility")
def ask_saved_compatibility(data: AskSavedCompatibilityRequest):
    owner = get_user_by_id(data.owner_user_id)
    profile = get_profile_by_id(data.profile_id)

    if not owner:
        raise HTTPException(status_code=404, detail="Owner user not found")
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    compatibility_data = AskCompatibilityRequest(
        person_1=PersonBirthData(
            birth_date=owner["birth_date"],
            birth_time=owner["birth_time"],
            birth_place=owner["birth_place"],
        ),
        person_2=PersonBirthData(
            birth_date=profile["birth_date"],
            birth_time=profile["birth_time"],
            birth_place=profile["birth_place"],
        ),
        question=data.question,
        history=data.history,
        user_id=data.owner_user_id,
        model=data.model,
    )

    return ask_compatibility(compatibility_data)

@app.post("/signup", response_model=AuthUserResponse)
def signup(data: SignupRequest):
    user = create_account(
        name=data.name,
        email=data.email,
        password=data.password,
        birth_date=data.birth_date,
        birth_time=data.birth_time,
        birth_place=data.birth_place
    )

    if not user:
        raise HTTPException(status_code=400, detail="Email already exists")

    return user


@app.post("/login", response_model=AuthUserResponse)
def login(data: LoginRequest):
    user = login_user(
        email=data.email,
        password=data.password
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return user

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    user = get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user 

@app.get("/users/{user_id}/natal-chart")
def get_saved_user_natal_chart(user_id: int):
    user = get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    birth_data = BirthData(
        birth_date=user["birth_date"],
        birth_time=user["birth_time"],
        birth_place=user["birth_place"]
    )

    natal_data = build_natal_chart_data(birth_data)

    return {
        "message": "Saved user natal chart calculated",
        "user": user,
        **natal_data
    }
@app.get("/profiles/{owner_user_id}")
def get_profiles(owner_user_id: int):
    return list_profiles_by_owner(owner_user_id)


@app.get("/chat-sessions/{owner_user_id}")
def get_chat_sessions(owner_user_id: int):
    return list_chat_sessions(owner_user_id)


@app.get("/chat-sessions/session/{session_id}")
def get_chat_session(session_id: int):
    session = get_chat_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@app.post("/chat-sessions")
def create_chat_session_endpoint(data: ChatSessionRequest):
    session = create_chat_session(
        owner_user_id=data.owner_user_id,
        profile_id=data.profile_id,
        title=data.title,
        messages=[message.model_dump() for message in data.messages],
    )
    return session


@app.patch("/chat-sessions/{session_id}")
def update_chat_session_endpoint(session_id: int, data: ChatSessionUpdateRequest):
    existing = get_chat_session_by_id(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session = update_chat_session(
        session_id=session_id,
        title=data.title,
        profile_id=data.profile_id,
        messages=[message.model_dump() for message in data.messages],
    )
    return session

@app.post("/profiles")
def save_profile(data: SaveProfileRequest):
    return create_profile(
        owner_user_id=data.owner_user_id,
        label=data.label,
        person_name=data.person_name,
        relationship_type=data.relationship_type,
        birth_date=data.birth_date,
        birth_time=data.birth_time,
        birth_place=data.birth_place
    )

@app.get("/profiles/profile/{profile_id}")
def get_profile(profile_id: int):
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int):
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
def usage_for_user(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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

