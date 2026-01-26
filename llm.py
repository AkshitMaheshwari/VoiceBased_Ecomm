from pathlib import Path
from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()

PROMPT_PATH = Path(__file__).parent / "prompt.txt"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_answer(context: str, convo: str, prefs: str, query: str) -> str:
    """Non-streaming version."""
    messages = _build_messages(context, convo, prefs, query)
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].message.content


def generate_answer_stream(context: str, convo: str, prefs: str, query: str):
    """Streaming version - yields text chunks."""
    messages = _build_messages(context, convo, prefs, query)
    
    stream = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=150,
        temperature=0.7,
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _build_messages(context: str, convo: str, prefs: str, query: str) -> list:
    """Helper to build message list."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Product Context:\n{context}"},
        {"role": "system", "content": f"User preferences: {prefs}"},
        {"role": "user", "content": f"Conversation:\n{convo}\n\nQuery: {query}"}
    ]