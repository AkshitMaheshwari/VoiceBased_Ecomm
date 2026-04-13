# Voice-Based E-commerce Agent

AI voice shopping assistant built with FastAPI, Twilio Voice, ElevenLabs, Groq, ChromaDB, and a browser voice UI.

The app supports:

- Phone calls through Twilio webhooks.
- Browser voice calls through the Twilio Voice JavaScript SDK.
- Product retrieval from ChromaDB with HuggingFace embeddings.
- Short voice-friendly answers from Groq.
- ElevenLabs TTS audio served back to Twilio.
- A modern static UI at `GET /`.
- Local ngrok setup through `scripts/start-local-ngrok.ps1`.

## Stack

| Layer | Tool |
| --- | --- |
| Backend | FastAPI |
| Voice gateway | Twilio Voice |
| Browser calls | Twilio Voice JavaScript SDK |
| TTS | ElevenLabs |
| LLM | Groq `llama-3.1-8b-instant` |
| Vector DB | ChromaDB |
| Embeddings | HuggingFace `sentence-transformers/all-MiniLM-L6-v2` |
| Frontend | Static HTML/CSS/JS |

## How It Works

1. Twilio sends the incoming call to `POST /webhooks/voice/incoming`.
2. The app plays a welcome message through ElevenLabs audio, with Twilio `<Say>` fallback.
3. Twilio gathers speech and sends the transcript to `POST /webhooks/voice/process-speech`.
4. The app updates session memory and retrieves products from ChromaDB.
5. Groq generates a short response.
6. ElevenLabs generates MP3 audio in `audio_cache/`.
7. Twilio fetches the MP3 from `/audio/{filename}` and plays it to the caller.

Browser calling uses the same TwiML App flow. The UI requests a token from `POST /api/twilio/token`, then starts a Twilio Voice SDK call against the configured TwiML App.

## Important Runtime Behavior

ChromaDB and HuggingFace embeddings are warmed during FastAPI startup:

```text
Warming ChromaDB retriever...
ChromaDB retriever ready.
```

That means startup can take longer, especially the first time the embedding model is loaded, but the first real voice response should not pay that delay.

The app also uses ASCII-safe logging and Twilio `<Say>` fallbacks so console encoding or downstream agent/TTS errors do not immediately become Twilio "application error" failures.

## Environment

Create a `.env` file in the repo root:

```env
# LLM
GROQ_API_KEY=your_groq_api_key

# Voice
ELEVEN_LABS=your_elevenlabs_api_key
DEEPGRAM_API_KEY=optional_deepgram_key

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Twilio account
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token

# Twilio browser Voice SDK
TWILIO_API_KEY_SID=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_KEY_SECRET=your_api_key_secret
TWILIO_TWIML_APP_SID=APxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Public HTTPS origin used by Twilio to fetch TwiML actions and MP3 audio
PUBLIC_BASE_URL=https://your-ngrok-domain.ngrok-free.dev

# Optional: require X-Token-Secret on POST /api/twilio/token
# TOKEN_ENDPOINT_SECRET=choose_a_random_string
```

Twilio values must come from the same Twilio account or subaccount:

- `TWILIO_ACCOUNT_SID` starts with `AC`.
- `TWILIO_API_KEY_SID` starts with `SK`.
- `TWILIO_API_KEY_SECRET` is the secret shown once when creating the API key.
- `TWILIO_TWIML_APP_SID` starts with `AP`.

## Install

```powershell
uv sync
```

Or:

```powershell
pip install -r requirements.txt
```

## Data Pipeline

Cleaned product data should live at:

```text
DataCleaning/cleaned_data.csv
```

Build or refresh ChromaDB:

```powershell
python Ingestion/chroma.py
```

The Chroma database is stored in:

```text
chroma_db/
```

`retriever.py` uses an absolute path to this folder, so Chroma loads correctly even when the app is started from another working directory.

## Run Locally

Start FastAPI:

```powershell
python app.py
```

Open:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/api/health
```

## Run With Ngrok

This repo includes a helper script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-ngrok.ps1
```

The script:

- Uses `tools\ngrok.exe` if present, otherwise `ngrok` from PATH.
- Starts `ngrok http 8000` if ngrok is not already running.
- Reads the public HTTPS URL from `http://127.0.0.1:4040/api/tunnels`.
- Writes `PUBLIC_BASE_URL=<public-url>` into `.env`.
- Starts `python app.py` if port `8000` is free.
- Checks `http://127.0.0.1:8000/api/health`.

If ngrok is not authenticated:

```powershell
.\tools\ngrok.exe config add-authtoken <your-ngrok-authtoken>
```

If you prefer to run the app yourself, you can still run ngrok manually:

```powershell
.\tools\ngrok.exe http 8000
```

Then copy the HTTPS origin into `.env` as `PUBLIC_BASE_URL`.

## Twilio Setup

### Phone Number Webhook

In Twilio Console:

1. Go to Phone Numbers.
2. Open your active Twilio number.
3. In Voice Configuration, set "A call comes in" to Webhook.
4. Use:

```text
https://<your-public-host>/webhooks/voice/incoming
```

5. Set method to `POST`.
6. Save.

### Browser Calling With Twilio Voice SDK

Create or open your TwiML App in Twilio Console.

Set Voice Request URL:

```text
https://<your-public-host>/webhooks/voice/incoming
```

Set method:

```text
POST
```

Copy the TwiML App SID into:

```env
TWILIO_TWIML_APP_SID=AP...
```

Create a Standard API Key in the same Twilio account, then set:

```env
TWILIO_API_KEY_SID=SK...
TWILIO_API_KEY_SECRET=...
```

Restart the FastAPI server after changing `.env`.

## UI

The static UI lives in:

```text
static/index.html
static/styles.css
static/app.js
```

The current UI is cache-busted with:

```html
/static/styles.css?v=4
/static/app.js?v=4
```

If the browser shows old UI or old JavaScript behavior, hard refresh with:

```text
Ctrl + Shift + R
```

## API Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Static browser UI |
| `/` | POST | Legacy incoming-call webhook |
| `/incoming-call` | POST | Legacy incoming-call webhook |
| `/webhooks/voice/incoming` | POST | Recommended Twilio incoming-call webhook |
| `/process-speech` | POST | Legacy speech callback |
| `/webhooks/voice/process-speech` | POST | Recommended Twilio `Gather` callback |
| `/api/twilio/token` | POST | Browser Voice SDK access token |
| `/api/health` | GET | Non-secret configuration and Chroma presence |
| `/audio/{filename}` | GET | ElevenLabs MP3 files for Twilio `<Play>` |
| `/static/*` | GET | UI assets |

## Testing

Pipeline test:

```powershell
python test_pipeline.py
```

Local webhook smoke test:

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri "http://127.0.0.1:8000/webhooks/voice/process-speech" `
  -Method Post `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "SpeechResult=Hi%2C%20I%20am%20looking%20for%20an%20iPhone&CallSid=TEST"
```

## Troubleshooting

### Port 8000 Already In Use

Find the process:

```powershell
netstat -ano | Select-String ':8000'
```

Stop it:

```powershell
Stop-Process -Id <PID> -Force
```

### Twilio JWT Signature Validation Failed

Use a new Standard API Key from the same account as `TWILIO_ACCOUNT_SID`.

The `SK...` value and secret must be from the same key. Twilio only shows the secret once.

### Twilio 31404 Not Found

Check `TWILIO_TWIML_APP_SID`.

The `AP...` TwiML App must exist in the same account/subaccount as the `AC...` account and `SK...` API key.

### Twilio Application Error

Check:

```powershell
Get-Content tools\app.err.log -Tail 120
Get-Content tools\app.log -Tail 120
```

The app now includes safer logging and fallback TwiML, but backend exceptions should still be fixed when they appear.

### Slow First Response

ChromaDB now warms on startup. If startup is slow, it is usually loading the HuggingFace embedding model. Once startup completes, the first user query should be faster.

If HuggingFace rate limits are slow, set an optional `HF_TOKEN` in your environment.

## Notes

- `tools/` is ignored by Git and may contain the local ngrok binary and logs.
- `.env` is ignored by Git and should never be committed.
- `audio_cache/` stores generated MP3 files served to Twilio.
