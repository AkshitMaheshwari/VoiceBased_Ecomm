import os
import base64
from fastapi import FastAPI, Request, Form
from fastapi.responses import Response, FileResponse
from twilio.twiml.voice_response import VoiceResponse, Gather, Play
from dotenv import load_dotenv
from groq import Groq
from elevenlabs import ElevenLabs
from retriever import retrieve
from SessionMemory.user_memory import UserMemory
import uuid

load_dotenv()

app = FastAPI()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_LABS"))

VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  

with open("prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# Storing call sessions and audio files for using user memory
sessions = {}
AUDIO_DIR = "audio_cache"
os.makedirs(AUDIO_DIR, exist_ok=True)


@app.post("/")
@app.post("/incoming-call")
async def incoming_call(request: Request):
    """Handle incoming call with ElevenLabs TTS."""
    response = VoiceResponse()
    
    # Get base URL for audio files
    host = request.headers.get("host", "localhost:8000")
    scheme = "https" if "ngrok" in host else "http"
    base_url = f"{scheme}://{host}"
    
   
    welcome_text = "Hi! I am your AI shopping assistant. What are you looking for today?"
    audio_url = generate_elevenlabs_audio(welcome_text, base_url)
    
   
    response.play(audio_url)
    
    gather = Gather(
        input="speech",
        action="/process-speech",
        language="en-US",
        speech_timeout="auto",
        timeout=5
    )
    response.append(gather)
    
    response.say("No response received. Goodbye!", voice="Polly.Aditi")
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/process-speech")
async def process_speech(
    request: Request,
    SpeechResult: str = Form(default=""),
    CallSid: str = Form(default="")
):
    """Process user speech and respond with ElevenLabs voice."""
    response = VoiceResponse()
    
    # base URL
    host = request.headers.get("host", "localhost:8000")
    scheme = "https" if "ngrok" in host else "http"
    base_url = f"{scheme}://{host}"
    
    if not SpeechResult.strip():
        audio_url = generate_elevenlabs_audio("I didn't understand that. Could you please repeat?", base_url)
        response.play(audio_url)
        gather = Gather(
            input="speech",
            action="/process-speech",
            language="en-US",
            speech_timeout="auto"
        )
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")
    
    print(f"👤 User ({CallSid}): {SpeechResult}")
    
    # Get sessionID
    if CallSid not in sessions:
        sessions[CallSid] = {"memory": UserMemory(), "history": []}
    
    session = sessions[CallSid]
    session["memory"].update(SpeechResult)
    
    # Get AI response
    ai_response = get_response(SpeechResult, session)
    print(f"🤖 AI: {ai_response}")
    
    session["history"].append({"user": SpeechResult, "ai": ai_response})
    
    # Generate ElevenLabs audio and play
    audio_url = generate_elevenlabs_audio(ai_response, base_url)
    response.play(audio_url)
    
    # Continue conversation
    gather = Gather(
        input="speech",
        action="/process-speech",
        language="en-US",
        speech_timeout="auto",
        timeout=8
    )
    response.append(gather)
    
    response.say("Anything else? If not, goodbye!", voice="Polly.Aditi")
    
    return Response(content=str(response), media_type="application/xml")


def get_response(query: str, session: dict) -> str:
    """Generate AI response."""
    # Get context from retriever
    docs = retrieve(query, session["memory"])
    context = "\n".join([d.page_content for d in docs]) if docs else ""
    
    # Build conversation history
    history = "\n".join([f"User: {h['user']}\nAI: {h['ai']}" for h in session["history"][-3:]])
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Products:\n{context}"},
        {"role": "system", "content": f"Preferences: {session['memory'].summary()}"},
        {"role": "system", "content": "Keep responses SHORT (1-2 sentences) for phone calls."},
        {"role": "user", "content": f"History:\n{history}\n\nQuery: {query}"}
    ]
    
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=80,
        temperature=0.7
    )
    return response.choices[0].message.content


def generate_elevenlabs_audio(text: str, base_url: str) -> str:
    """Generate audio with ElevenLabs and return URL."""
    # Generate unique filename
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    
    # Generate audio with ElevenLabs
    audio = eleven_client.text_to_speech.convert(
        voice_id=VOICE_ID,
        text=text,
        model_id="eleven_turbo_v2_5",  # Fast model
        output_format="mp3_44100_128"
    )
    
    # Save audio file
    with open(filepath, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    
    return f"{base_url}/audio/{filename}"


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio files to Twilio."""
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/mpeg")
    return Response(status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)