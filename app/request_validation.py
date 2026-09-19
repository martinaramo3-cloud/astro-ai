"""Bound client input before it reaches storage or expensive chart/model work."""
from datetime import date, datetime
import re
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, model_validator


class RequestModel(PydanticBaseModel):
    model_config = ConfigDict(str_max_length=16000)

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        if not isinstance(values, dict):
            return values
        values = dict(values)
        for key in ("name", "person_name", "label", "title", "birth_place", "relationship_type"):
            value = values.get(key)
            if isinstance(value, str) and len(value) > 300:
                raise ValueError(f"{key.replace('_', ' ')} must be at most 300 characters.")
        for key in ("history", "messages"):
            if isinstance(values.get(key), list) and len(values[key]) > 200:
                raise ValueError("A conversation can contain at most 200 messages.")
        if isinstance(values.get("attachment_ids"), list) and len(values["attachment_ids"]) > 3:
            raise ValueError("Attach at most three images.")
        if "email" in values and isinstance(values["email"], str):
            email = values["email"].strip()
            if len(email) > 254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email):
                raise ValueError("Please enter a valid email address.")
            values["email"] = email
        if isinstance(values.get("password"), str) and len(values["password"]) > 256:
            raise ValueError("Password must be at most 256 characters.")
        birth_date = values.get("birth_date")
        if birth_date is not None:
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", birth_date):
                    raise ValueError()
                parsed = date.fromisoformat(birth_date)
                if not 1800 <= parsed.year or parsed > date.today():
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError("Please enter a valid birth date between 1800 and today.")
        birth_time = values.get("birth_time")
        if values.get("birth_time_known") is False:
            values["birth_time"] = "12:00"
        elif birth_time is not None:
            try:
                datetime.strptime(birth_time, "%H:%M")
            except (ValueError, TypeError):
                raise ValueError("Please enter a valid birth time (HH:MM).")
        return values
