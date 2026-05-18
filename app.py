import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from groq import Groq
from elevenlabs import ElevenLabs
from SessionMemory.user_memory import UserMemory

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Voice-Based E-commerce Agent")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_LABS"))

VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

with open(BASE_DIR / "prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

sessions: dict = {}
AUDIO_DIR = "audio_cache"
os.makedirs(AUDIO_DIR, exist_ok=True)


def safe_log(message: str) -> None:
    print(message.encode("ascii", errors="backslashreplace").decode("ascii"))


@app.on_event("startup")
async def warm_chroma_db() -> None:
    # Retriever now uses eager initialization at import time.
    from retriever import retrieve
    safe_log("ChromaDB retriever ready.")


def resolve_public_base_url(request: Request) -> str:
    """Public origin for Twilio <Play> URLs and Gather action (use PUBLIC_BASE_URL behind proxies/ngrok)."""
    pub = (os.getenv("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if pub:
        return pub
    return str(request.base_url).rstrip("/")


def process_speech_url(base_url: str) -> str:
    return f"{base_url}/webhooks/voice/process-speech"


async def voice_incoming(request: Request) -> Response:
    """Twilio webhook: welcome TTS + speech gather (PSTN or Twilio Client)."""
    vr = VoiceResponse()
    base_url = resolve_public_base_url(request)
    action_url = process_speech_url(base_url)

    welcome_text = "Hi! I am your AI shopping assistant. What are you looking for today?"
    try:
        audio_url = generate_elevenlabs_audio(welcome_text, base_url)
        vr.play(audio_url)
    except Exception as exc:
        safe_log(f"Welcome audio error: {exc!r}")
        vr.say(welcome_text, voice="Polly.Aditi")

    gather = Gather(
        input="speech",
        action=action_url,
        method="POST",
        language="en-US",
        speech_timeout="auto",
        timeout=5,
    )
    vr.append(gather)
    vr.say("No response received. Goodbye!", voice="Polly.Aditi")
    return Response(content=str(vr), media_type="application/xml")


async def voice_process_speech(
    request: Request,
    SpeechResult: str = Form(default=""),
    CallSid: str = Form(default=""),
) -> Response:
    """Twilio webhook: STT transcript -> agent -> ElevenLabs TTS."""
    vr = VoiceResponse()
    base_url = resolve_public_base_url(request)
    action_url = process_speech_url(base_url)

    if not SpeechResult.strip():
        retry_text = "I didn't understand that. Could you please repeat?"
        try:
            audio_url = generate_elevenlabs_audio(retry_text, base_url)
            vr.play(audio_url)
        except Exception as exc:
            safe_log(f"Retry audio error: {exc!r}")
            vr.say(retry_text, voice="Polly.Aditi")
        gather = Gather(
            input="speech",
            action=action_url,
            method="POST",
            language="en-US",
            speech_timeout="auto",
        )
        vr.append(gather)
        return Response(content=str(vr), media_type="application/xml")

    safe_log(f"User ({CallSid}): {SpeechResult}")

    if CallSid not in sessions:
        sessions[CallSid] = {"memory": UserMemory(), "history": []}

    session = sessions[CallSid]
    session["memory"].update(SpeechResult)

    try:
        ai_response = get_response(SpeechResult, session)
    except Exception as exc:
        safe_log(f"Agent error: {exc!r}")
        vr.say(
            "I heard you, but I had trouble looking that up. Please try again.",
            voice="Polly.Aditi",
        )
        gather = Gather(
            input="speech",
            action=action_url,
            method="POST",
            language="en-US",
            speech_timeout="auto",
            timeout=8,
        )
        vr.append(gather)
        return Response(content=str(vr), media_type="application/xml")

    safe_log(f"AI: {ai_response}")

    session["history"].append({"user": SpeechResult, "ai": ai_response})

    try:
        audio_url = generate_elevenlabs_audio(ai_response, base_url)
        vr.play(audio_url)
    except Exception as exc:
        safe_log(f"Response audio error: {exc!r}")
        vr.say(ai_response, voice="Polly.Aditi")

    gather = Gather(
        input="speech",
        action=action_url,
        method="POST",
        language="en-US",
        speech_timeout="auto",
        timeout=8,
    )
    vr.append(gather)
    vr.say("Anything else? If not, goodbye!", voice="Polly.Aditi")
    return Response(content=str(vr), media_type="application/xml")


@app.get("/")
async def serve_index():
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        return JSONResponse(
            {"detail": "Frontend missing: static/index.html not found"},
            status_code=404,
        )
    return FileResponse(index)


class ChatRequest(BaseModel):
    session_id: str
    query: str

@app.post("/api/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    base_url = resolve_public_base_url(request)
    session_id = body.session_id.strip()
    query = body.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if not session_id:
        session_id = "default_session"

    if session_id not in sessions:
        sessions[session_id] = {"memory": UserMemory(), "history": []}

    session = sessions[session_id]
    session["memory"].update(query)

    try:
        ai_response = get_response(query, session)
        session["history"].append({"user": query, "ai": ai_response})
    except Exception as exc:
        safe_log(f"Agent error: {exc!r}")
        raise HTTPException(status_code=500, detail="Error generating AI response")

    try:
        audio_url = generate_elevenlabs_audio(ai_response, base_url)
    except Exception as exc:
        safe_log(f"Response audio error: {exc!r}")
        audio_url = None

    return {
        "response": ai_response,
        "audio_url": audio_url
    }



@app.post("/webhooks/voice/incoming")
async def webhook_voice_incoming(request: Request):
    return await voice_incoming(request)


@app.post("/webhooks/voice/process-speech")
async def webhook_voice_process_speech(
    request: Request,
    SpeechResult: str = Form(default=""),
    CallSid: str = Form(default=""),
):
    return await voice_process_speech(request, SpeechResult, CallSid)


@app.post("/")
@app.post("/incoming-call")
async def incoming_call_legacy(request: Request):
    """Legacy Twilio webhook URL (POST /)."""
    return await voice_incoming(request)


@app.post("/process-speech")
async def process_speech_legacy(
    request: Request,
    SpeechResult: str = Form(default=""),
    CallSid: str = Form(default=""),
):
    """Legacy gather callback URL."""
    return await voice_process_speech(request, SpeechResult, CallSid)


@app.post("/api/twilio/token")
async def twilio_token(request: Request):
    """
    Issue a Twilio Voice access token for the browser SDK (TwiML App outbound).
    Optional: set TOKEN_ENDPOINT_SECRET and send header X-Token-Secret.
    JSON body optional: {"identity": "my-user-id"}
    """
    expected = os.getenv("TOKEN_ENDPOINT_SECRET")
    if expected and request.headers.get("X-Token-Secret") != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Token-Secret")

    account_sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
    api_key_sid = (os.getenv("TWILIO_API_KEY_SID") or "").strip()
    api_secret = (os.getenv("TWILIO_API_KEY_SECRET") or "").strip()
    twiml_app_sid = (os.getenv("TWILIO_TWIML_APP_SID") or "").strip()

    missing = [
        name
        for name, val in [
            ("TWILIO_ACCOUNT_SID", account_sid),
            ("TWILIO_API_KEY_SID", api_key_sid),
            ("TWILIO_API_KEY_SECRET", api_secret),
            ("TWILIO_TWIML_APP_SID", twiml_app_sid),
        ]
        if not val
    ]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Twilio token env not configured: {', '.join(missing)}",
        )

    raw: dict = {}
    try:
        body = await request.json()
        if isinstance(body, dict):
            raw = body
    except Exception:
        pass

    identity_raw = raw.get("identity")
    identity = (
        identity_raw.strip()
        if isinstance(identity_raw, str) and identity_raw.strip()
        else f"web-{uuid.uuid4().hex[:12]}"
    )

    token = AccessToken(account_sid, api_key_sid, api_secret, identity=identity, ttl=3600)
    # Outbound-only: do not set incoming_allow=True without push/incoming setup or register() may fail in the browser.
    voice_grant = VoiceGrant(outgoing_application_sid=twiml_app_sid)
    token.add_grant(voice_grant)
    return {"token": token.to_jwt(), "identity": identity}


@app.get("/api/health")
async def health():
    chroma_path = BASE_DIR / "chroma_db"
    return {
        "ok": True,
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "elevenlabs_configured": bool(os.getenv("ELEVEN_LABS")),
        "twilio_token_env_ready": bool(
            os.getenv("TWILIO_ACCOUNT_SID")
            and os.getenv("TWILIO_API_KEY_SID")
            and os.getenv("TWILIO_API_KEY_SECRET")
            and os.getenv("TWILIO_TWIML_APP_SID")
        ),
        "chroma_db_present": chroma_path.is_dir(),
        "public_base_url_set": bool(os.getenv("PUBLIC_BASE_URL")),
    }


def get_response(query: str, session: dict) -> str:
    from retriever import retrieve, format_context

    q = query.strip().lower()
    if q in {"hi", "hello", "hey", "yo"}:
        return "Hi! Tell me what you are shopping for and I will curate options."
    if q.startswith("my name is "):
        name = query.strip()[11:].strip()
        if name:
            session["user_name"] = name
            return f"Nice to meet you, {name}. What are you shopping for today?"
        return "Nice to meet you. What are you shopping for today?"
    if "your name" in q or "who are you" in q:
        return "I am your shopping assistant. What are you looking for today?"
    if "what can you do" in q or "what do you do" in q:
        return "I can help you find products, compare options, and answer questions about the catalog. What are you shopping for?"

    docs = retrieve(query, session["memory"])
    context = format_context(docs)

    history = "\n".join(
        [f"User: {h['user']}\nAI: {h['ai']}" for h in session["history"][-3:]]
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Products:\n{context}"},
        {"role": "system", "content": f"Preferences: {session['memory'].summary()}"},
        {"role": "system", "content": "Keep responses SHORT (1-2 sentences) for phone calls."},
        {"role": "user", "content": f"History:\n{history}\n\nQuery: {query}"},
    ]

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=80,
        temperature=0.7,
    )
    return response.choices[0].message.content


def generate_elevenlabs_audio(text: str, base_url: str) -> str:
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    try:
        audio = eleven_client.text_to_speech.convert(
            voice_id=VOICE_ID,
            text=text,
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128",
        )

        with open(filepath, "wb") as f:
            for chunk in audio:
                f.write(chunk)
                
        return f"{base_url}/audio/{filename}"
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise e


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/mpeg")
    return Response(status_code=404)


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
