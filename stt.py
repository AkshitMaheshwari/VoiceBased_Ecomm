import os
import asyncio
import time
import httpx
from dotenv import load_dotenv
from voice.mic import audio_queue

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")


async def listen(record_seconds: float = 4.0) -> str:
    """
    Records audio for specified seconds and transcribes.
    Simple HTTP version - more reliable.
    """
    # Collect audio
    audio_data = b""
    start_time = time.time()
    
    print("🔴 Recording...")
    
    while time.time() - start_time < record_seconds:
        try:
            chunk = audio_queue.get(timeout=0.1)
            audio_data += chunk
        except:
            await asyncio.sleep(0.05)
    
    print("⏹ Processing...")
    
    if not audio_data:
        return ""
    
    # Send to Deepgram
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "audio/raw",
            },
            content=audio_data,
            params={
                "encoding": "linear16",
                "sample_rate": "16000",
                "channels": "1",
                "model": "nova-2",
                "language": "hi",
                "punctuate": "true",
                "smart_format": "true"
            },
            timeout=10.0
        )
        
        if response.status_code == 200:
            result = response.json()
            transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
            return transcript.strip()
        else:
            print(f"Deepgram error: {response.status_code} - {response.text}")
            return ""