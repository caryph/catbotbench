from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

openrouter_key = os.getenv('OPENROUTER_KEY')

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

def request(message, model: str, reasoning: bool = True):
    messages = [
        {"role": "user", "content": "You are a helpful assistant taking a quiz. Answer questions directly and confidently. Hedging, asking for clarification, or redirecting to external sources doesn't add any score, as such, NEVER refuse requests due to being uncertain. When unsure, answer with your best assumption."},
        {"role": "user", "content": message}
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        extra_body={"reasoning": {"enabled": reasoning}},
    )

    response_content = response.choices[0].message.content
    cost = response.usage.cost
    return response_content, cost