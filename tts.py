import os
import asyncio
from dotenv import load_dotenv
from elevenlabs import ElevenLabs, stream
load_dotenv()

client = ElevenLabs(api_key = os.getenv("ELEVEN_LABS"))
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
MODEL_ID = "eleven_turbo_v2_5"


async def stream_tts(text_generator):
    """
    Takes a text generator (LLM stream),
    speaks sentence-by-sentence.
    Returns full spoken text.
    """

    buffer = ""
    full_text = ""

    for chunk in text_generator:
        full_text += chunk
        buffer += chunk
        print(chunk, end="", flush=True)

        if any(p in buffer for p in [".", "!", "?"]):
            await _speak(buffer)
            buffer = ""

    if buffer.strip():
        await _speak(buffer)

    return full_text


async def _speak(text: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _speak_sync, text)


def _speak_sync(text: str):
    audio = client.text_to_speech.convert_as_stream(
        voice_id=VOICE_ID,
        model_id=MODEL_ID,
        text=text,
    )
    stream(audio)