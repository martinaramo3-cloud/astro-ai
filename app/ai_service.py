import os
from dotenv import load_dotenv

load_dotenv()
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set.")

client = OpenAI(api_key=api_key)


def generate_chart_summary(prompt: str):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=180
    )
    return response.output_text


def generate_astrologer_answer(prompt: str):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=220
    )
    return response.output_text

def generate_compatibility_reading(prompt: str):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=220
    )

    return response.output_text

def generate_compatibility_answer(prompt: str):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=220
    )
    return response.output_text 
