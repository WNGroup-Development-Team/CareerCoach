import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("backend/.env")

groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    timeout=30.0
)

try:
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("Success:")
    print(response.choices[0].message.content)
except Exception as e:
    print("Error:", type(e))
    print(e)
