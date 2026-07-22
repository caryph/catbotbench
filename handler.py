from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

openrouter_key = os.getenv('OPENROUTER_KEY')

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

def request(message, model: str, reasoning: bool = True):
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer questions directly and confidently. Hedging or redirecting to external sources doesn't add any score. As such, never refuse requests and make assumptions when unsure."},
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