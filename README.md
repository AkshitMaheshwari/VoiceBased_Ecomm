# 🛒 Voice-Based E-commerce Agent

An AI-powered voice calling agent for e-commerce that helps customers find products through natural phone conversations. Built with Twilio, ElevenLabs, Groq LLM, and ChromaDB.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Twilio](https://img.shields.io/badge/Twilio-Voice-red)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-purple)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)



## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VOICE E-COMMERCE AGENT                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  📞 TWILIO VOICE                                                     │
│  ├── Incoming call handling                                          │
│  ├── Speech-to-Text (built-in)                                       │
│  └── Webhook endpoints                                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  🧠 PROCESSING PIPELINE                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Retriever  │→ │   Memory    │→ │  LLM Engine │→ │   Response  │ │
│  │  (ChromaDB) │  │ (Session)   │  │   (Groq)    │  │  Generation │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  🎙 ELEVENLABS TTS                                                   │
│  ├── Natural voice synthesis                                         │
│  ├── Turbo model (low latency)                                       │
│  └── Audio streaming to Twilio                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

- 📞 **Phone-based shopping** - Customers call and shop via voice
- 🎯 **Smart product search** - Semantic search with filters (brand, category, budget)
- 🧠 **Conversation memory** - Remembers context within the call
- 👤 **User preferences** - Tracks budget, brand, category preferences
- 🗣️ **Natural voice** - ElevenLabs for human-like responses
- ⚡ **Low latency** - Groq LLM (500+ tokens/sec) + ElevenLabs Turbo

---

## 🛠 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Voice Gateway** | Twilio Voice | Phone calls, STT |
| **Text-to-Speech** | ElevenLabs | Natural voice synthesis |
| **LLM** | Groq (Llama 3.1 8B) | Response generation |
| **Vector DB** | ChromaDB | Product embeddings & search |
| **Embeddings** | HuggingFace (all-MiniLM-L6-v2) | Text embeddings |
| **Backend** | FastAPI | API server |
| **Data Processing** | Pandas | Data cleaning |


---

## 🚀 Setup Guide

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/voice_ecomm.git
cd voice_ecomm

# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Environment Variables

Create `.env` file:

```env
# LLM
GROQ_API_KEY=your_groq_api_key

# Voice
ELEVEN_LABS=your_elevenlabs_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key  # Optional for CLI mode

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Twilio (for webhook validation)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

### 3. Data Pipeline

#### Step 1: Data Cleaning
```bash
# Run the data cleaning notebook
jupyter notebook DataCleaning/file.ipynb
```

The cleaning process:
- Removes duplicates and null values
- Normalizes price formats
- Extracts brand names
- Categorizes products
- Outputs `cleaned_data.csv`

#### Step 2: Ingest to ChromaDB
```bash
python Ingestion/chroma.py
```

This creates vector embeddings with metadata:
- `product_name` - Product title
- `description` - Product description  
- `price` - Numeric price (for filtering)
- `brand` - Brand name (for filtering)
- `category` - Product category (for filtering)

### 4. Run the Server

```bash
# Start FastAPI server
python app.py
```

### 5. Expose with Ngrok

```bash
# In another terminal
ngrok http 8000
```

### 6. Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com)
2. Buy a phone number (or use trial)
3. Configure Voice webhook:
   - **URL**: `https://your-ngrok-url.ngrok.io/`
   - **Method**: POST
4. Save and call the number!

---

## 🔄 Pipeline Details

### 1️⃣ Data Cleaning (`DataCleaning/`)

```python
# Sample cleaning operations
df = pd.read_csv("walmart-products.csv")
df = df.dropna(subset=["Product Name", "Sale Price"])
df["price"] = df["Sale Price"].str.replace("$", "").astype(float)
df["brand"] = df["Product Name"].apply(extract_brand)
df.to_csv("cleaned_data.csv", index=False)
```

### 2️⃣ Vector Store - ChromaDB (`Ingestion/chroma.py`)

```python
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Create embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Store with metadata
db = Chroma.from_documents(
    documents=docs,
    embedding=embeddings,
    persist_directory="./chroma_db"
)
```

**Metadata stored:**
| Field | Type | Example | Use |
|-------|------|---------|-----|
| `price` | float | 499.99 | Budget filtering (`$lte`) |
| `brand` | string | "Samsung" | Brand filtering |
| `category` | string | "Laptop" | Category filtering |

### 3️⃣ Retriever (`retriever.py`)

```python
def retrieve(query, user_memory):
    conditions = []
    
    if user_memory.pref["brand"]:
        conditions.append({"brand": user_memory.pref["brand"]})
    
    if user_memory.pref["budget"]:
        conditions.append({"price": {"$lte": user_memory.pref["budget"]}})
    
    # ChromaDB requires $and for multiple filters
    if len(conditions) > 1:
        filters = {"$and": conditions}
    
    return chroma.similarity_search(query, k=3, filter=filters)
```

### 4️⃣ Session Memory (`SessionMemory/`)

**Conversation Memory** - Stores recent exchanges:
```python
class ConversationMemory:
    def __init__(self, max_length=10):
        self.buffer = deque(maxlen=max_length)
    
    def add_user(self, text): ...
    def add_ai(self, text): ...
    def context(self): ...  # Returns formatted history
```

**User Memory** - Extracts preferences from speech:
```python
class UserMemory:
    def __init__(self):
        self.pref = {"budget": None, "brand": None, "category": None}
    
    def update(self, text):
        # Extract budget: "under 5000" → budget=5000
        # Extract brand: "Samsung phone" → brand="Samsung"
        # Extract category: "laptop" → category="Laptop"
```

### 5️⃣ LLM Engine (`llm.py`)

```python
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_answer(context, convo, prefs, query):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Products:\n{context}"},
        {"role": "system", "content": f"User preferences: {prefs}"},
        {"role": "user", "content": f"Conversation:\n{convo}\n\nQuery: {query}"}
    ]
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=80,  # Short for voice
        temperature=0.7
    )
    return response.choices[0].message.content
```

### 6️⃣ Twilio + ElevenLabs (`app.py`)

**Call Flow:**
```
📞 Incoming Call
      │
      ▼
┌─────────────────┐
│  POST /         │ ──→ Welcome message (ElevenLabs)
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Twilio STT      │ ──→ User speaks, transcribed
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ POST /process-  │
│ speech          │ ──→ Retrieve → LLM → ElevenLabs → Play
└─────────────────┘
      │
      ▼
   (Loop until hangup)
```

**ElevenLabs Integration:**
```python
def generate_elevenlabs_audio(text, base_url):
    audio = eleven_client.text_to_speech.convert(
        voice_id=VOICE_ID,
        text=text,
        model_id="eleven_turbo_v2_5",  # Low latency
        output_format="mp3_44100_128"
    )
    # Save and return URL for Twilio to fetch
    return f"{base_url}/audio/{filename}"
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | POST | Twilio webhook - incoming call |
| `/incoming-call` | POST | Alias for incoming call |
| `/process-speech` | POST | Process user speech, return AI response |
| `/audio/{filename}` | GET | Serve ElevenLabs audio files |

---

## 🧪 Testing

### Text-based Testing (without calling)
```bash
python test_pipeline.py
```

This tests:
- ✅ Retriever with filters
- ✅ LLM response generation
- ✅ Memory updates
- ✅ Interactive chat mode

### Live Call Testing
1. Start server: `python app.py`
2. Start ngrok: `ngrok http 8000`
3. Update Twilio webhook
4. Call your Twilio number

---

## 📊 Performance

| Component | Latency |
|-----------|---------|
| Twilio STT | ~1s |
| ChromaDB Retrieval | ~100ms |
| Groq LLM | ~200ms |
| ElevenLabs TTS | ~500ms |
| **Total Response Time** | **~2s** |

---

## 🔮 Future Improvements

- [ ] Streaming TTS (ElevenLabs WebSocket)
- [ ] Cart management
- [ ] Order placement
- [ ] Multi-language support
- [ ] Voice authentication
- [ ] Analytics dashboard

---

## 📝 License

MIT License

---

## 🤝 Contributing

PRs welcome! Please read contributing guidelines first.

