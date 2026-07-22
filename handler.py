from openai import OpenAI
import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

openrouter_key = os.getenv('OPENROUTER_KEY')

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

def request(messages, model: str, reasoning: bool = False):
    if type(messages) is str:
        messages = [{
            "role": "user",
            "content": messages
        }]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        extra_body={"reasoning": {"enabled": reasoning}},
    )

    response_content = response.choices[0].message.content
    cost = response.usage.cost
    return response_content, cost