import os
import asyncio
from elevenlabs import ElevenLabs
from elevenlabs import stream as eleven_stream
from dotenv import load_dotenv

load_dotenv()

client = ElevenLabs(api_key=os.getenv("ELEVEN_LABS"))

VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # Change as needed
MODEL_ID = "eleven_turbo_v2_5"  # Fastest model


def speak(text: str):
    """Simple TTS - waits for full text."""
    audio = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        text=text,
        model_id=MODEL_ID
    )
    eleven_stream(audio)


async def stream_tts(text_generator) -> str:
    """
    Streaming TTS - speaks while LLM generates.
    Returns full response text.
    """
    buffer = ""
    full_response = ""
    
    for chunk in text_generator:
        buffer += chunk
        full_response += chunk
        print(chunk, end="", flush=True)  # Real-time console output
        
        # Speak when we hit sentence boundary
        if any(p in chunk for p in ['.', '!', '?']):
            await _speak_async(buffer)
            buffer = ""
    
    # Speak remaining text
    if buffer.strip():
        await _speak_async(buffer)
    
    return full_response


async def _speak_async(text: str):
    """Async wrapper for TTS."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _speak_sync, text)


def _speak_sync(text: str):
    """Sync TTS call."""
    audio = client.text_to_speech.convert_as_stream(
        voice_id=VOICE_ID,
        text=text,
        model_id=MODEL_ID
    )
    eleven_stream(audio)