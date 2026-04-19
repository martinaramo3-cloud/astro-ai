import os
from fastapi.middleware.cors import CORSMiddleware
from app.auth_service import create_account, login_user
from app.user_service import create_user, get_user_by_id 
from app.profile_service import create_profile, list_profiles_by_owner, get_profile_by_id, delete_profile_by_id
from app.database import init_db 
from app.question_router import classify_question, filter_chart_context_by_question_type
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException
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
from app.ai_context_service import (
    build_ai_chart_context,
    build_summary_prompt,
    build_weekly_horoscope_prompt,
    build_ask_astrologer_context,
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
    allow_origin_regex=r"https://.*\.vercel\.app",
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

class AstrologyQuestionRequest(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str
    question: str
    history: Optional[List[ChatMessage]] = None

class PersonBirthData(BaseModel):
    birth_date: str
    birth_time: str
    birth_place: str

class CompatibilityRequest(BaseModel):
    person_1: PersonBirthData
    person_2: PersonBirthData 

class AskCompatibilityRequest(BaseModel):
    person_1: PersonBirthData
    person_2: PersonBirthData
    question: str 
    history: Optional[List[ChatMessage]] = None

class SaveUserRequest(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    birth_place: str

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

class UserResponse(BaseModel):
    id: int
    name: str
    birth_date: str
    birth_time: str
    birth_place: str

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
def chart_summary(data: BirthData):
    natal_data = build_natal_chart_data(data)

    chart_context = build_ai_chart_context(
        planets=natal_data["planet_positions"],
        ascendant=natal_data["ascendant"],
        aspects=natal_data["aspects"]
    )

    prompt = build_summary_prompt(chart_context)
    summary = generate_chart_summary(prompt)

    return {
        "message": "AI chart summary generated",
        "chart_context": chart_context,
        "summary": summary
    }

@app.post("/ask-astrologer")
def ask_astrologer(data: AstrologyQuestionRequest):
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
    **filtered_context
} 

    prompt = build_ask_astrologer_prompt(chat_context)
    answer = generate_astrologer_answer(prompt)

    return {
        "message": "Astrologer answer generated",
        "question": data.question,
        "question_type": question_type,
        "context": chat_context,
        "answer": answer
    }
from app.compatibility_service import get_synastry_aspects 

@app.post("/compatibility")
def get_compatibility(data: CompatibilityRequest):
    person_1_chart = build_natal_chart_data(data.person_1)
    person_2_chart = build_natal_chart_data(data.person_2)

    synastry_aspects = get_synastry_aspects(
        person_1_chart["planet_positions"],
        person_2_chart["planet_positions"]
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
        "synastry_aspects": synastry_aspects[:20]
    }
@app.post("/compatibility-reading")
def compatibility_reading(data: CompatibilityRequest):

    person_1_chart = build_natal_chart_data(data.person_1)
    person_2_chart = build_natal_chart_data(data.person_2)

    synastry_aspects = get_synastry_aspects(
        person_1_chart["planet_positions"],
        person_2_chart["planet_positions"]
    )

    context = build_compatibility_context(
        person_1_chart,
        person_2_chart,
        synastry_aspects
    )

    prompt = build_compatibility_prompt(context)

    reading = generate_compatibility_reading(prompt)

    return {
        "message": "Compatibility reading generated",
        "context": context,
        "reading": reading
    }

@app.post("/ask-compatibility")
def ask_compatibility(data: AskCompatibilityRequest):
    person_1_chart = build_natal_chart_data(data.person_1)
    person_2_chart = build_natal_chart_data(data.person_2)

    synastry_aspects = get_synastry_aspects(
        person_1_chart["planet_positions"],
        person_2_chart["planet_positions"]
    )

    context = build_ask_compatibility_context(
        person_1_chart,
        person_2_chart,
        synastry_aspects,
        data.question,
        [msg.model_dump() for msg in (data.history or [])]
    )

    prompt = build_ask_compatibility_prompt(context)
    answer = generate_compatibility_answer(prompt)

    return {
        "message": "Compatibility answer generated",
        "question": data.question,
        "context": context,
        "answer": answer
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
        history=data.history
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

@app.post("/users", response_model=UserResponse)
def save_user(data: SaveUserRequest):
    return create_user(
        name=data.name,
        birth_date=data.birth_date,
        birth_time=data.birth_time,
        birth_place=data.birth_place
    )

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
