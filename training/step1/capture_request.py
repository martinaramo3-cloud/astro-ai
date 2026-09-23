"""Capture exactly what Zoli sends to the model, for one fictional person.

Reads only. Runs the app's real calculation and prompt-assembly code with the
network stubbed, so nothing is spent and nothing is changed. Writes three files
into this folder: the standing instructions, the per-request half, and a
summary of how big each piece is.

    ./venv/bin/python training/step1/capture_request.py
"""
import json
import os
import pathlib
import sys
import tempfile

# Run from anywhere: the app package lives two levels up.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(prefix="zoli-step1-"), "t.db")
os.environ.setdefault("ADMIN_SECRET", "step1")

import app.main as main
from app.database import init_db

HERE = pathlib.Path(__file__).parent

# Entirely invented. Real coordinates so the chart is genuine, but the person
# is not anyone.
PERSON = {"name": "Ana Dimitrova", "email": "ana@example.invalid",
          "password": "Testing123!", "birth_date": "1999-03-02",
          "birth_time": "07:15", "birth_place": "Sofia, Bulgaria",
          "birth_time_known": True}
PLACES = {"sofia, bulgaria": {"latitude": 42.6977, "longitude": 23.3219,
                              "timezone": "Europe/Sofia", "display_name": "Sofia, Bulgaria"}}

QUESTION = "when is this thing with him actually going to come to a head?"
HISTORY = [
    {"role": "user", "content": "we fought and honestly im done"},
    {"role": "assistant", "content": "Good. Say it."},
]


def main_capture():
    from fastapi.testclient import TestClient
    import app.location_service as location
    import app.ai_service as ai

    init_db()
    location.get_location_data = lambda name: PLACES[name.strip().lower()]
    main.get_location_data = location.get_location_data

    captured = {}

    def fake_generate(prompt, **kwargs):
        captured["user_half"] = prompt
        captured["system_half"] = kwargs.get("system", "")
        captured["max_output_tokens"] = kwargs.get("max_output_tokens")
        captured["model"] = kwargs.get("model")
        return "…the model's answer would go here…", 0

    main.generate_astrologer_answer = fake_generate
    ai.generate_astrologer_answer = fake_generate
    main.classify_answer_tier = lambda *a, **k: 4   # no cheap-model call
    main.extract_asked_date = lambda *a, **k: None  # no cheap-model call

    client = TestClient(main.app)
    signup = client.post("/signup", json=PERSON).json()
    headers = {"Authorization": f"Bearer {signup['token']}"}
    body = {k: PERSON[k] for k in ("birth_date", "birth_time", "birth_place", "birth_time_known")}
    response = client.post("/ask-astrologer", headers=headers,
                           json={**body, "question": QUESTION, "history": HISTORY,
                                 "user_id": signup["id"]})
    response.raise_for_status()
    result = response.json()

    (HERE / "01-system-half.txt").write_text(captured["system_half"])
    (HERE / "02-user-half.txt").write_text(captured["user_half"])

    system, user = captured["system_half"], captured["user_half"]
    summary = {
        "model_that_would_be_used": captured["model"],
        "answer_tier_chosen": result["context"]["answer_tier"],
        "max_output_tokens_allowed": captured["max_output_tokens"],
        "system_half_characters": len(system),
        "user_half_characters": len(user),
        "ratio_data_to_instructions": round(len(user) / max(len(system), 1), 1),
        "top_level_data_keys": sorted(
            k for k in result["context"] if k not in ("history", "question", "conversation")),
    }
    (HERE / "03-summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main_capture()
