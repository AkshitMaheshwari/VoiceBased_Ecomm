# from langchain_openai import OpenAI
# from pathlib import Path
# from dotenv import load_dotenv
# import os
# from openai import OpenAI
# load_dotenv()

# PROMPT_PATH = Path(__file__).parent / "prompts.txt"

# with open(PROMPT_PATH, "r",encoding = "utf-8") as f:
#     SYSTEM_PROMPT = f.read()

# client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"),base_url = "https://models.inference.ai.azure.com")

# def generate_res(context:str,convo:str,prefs:str,query:str)->str:
#     """Generates a spoken-style response for a voice -based ecommerce assistant."""
#     messages= [
#         {"role":"system","context":SYSTEM_PROMPT},
#         {"role":"system","content":f"User preferences:{prefs}"},
#         {"role":"system","content":f"Conversation so far:\n{convo}"}
#     ]

from pathlib import Path
from dotenv import load_dotenv
import os
from groq import Groq  # Groq is super fast!

load_dotenv()

PROMPT_PATH = Path(__file__).parent / "prompts.txt"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_res(context: str, convo: str, prefs: str, query: str) -> str:
    """Generates a spoken-style response for voice-based ecommerce assistant."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Product Context:\n{context}"},
        {"role": "system", "content": f"User preferences: {prefs}"},
        {"role": "user", "content": f"Conversation:\n{convo}\n\nQuery: {query}"}
    ]
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Very fast!
        messages=messages,
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].message.content


def generate_res_stream(context: str, convo: str, prefs: str, query: str):
    """Streaming version - yields chunks for real-time TTS."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Product Context:\n{context}"},
        {"role": "system", "content": f"User preferences: {prefs}"},
        {"role": "user", "content": f"Conversation:\n{convo}\n\nQuery: {query}"}
    ]
    
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