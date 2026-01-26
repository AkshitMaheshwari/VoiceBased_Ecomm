# 🛒 Voice-Based E-commerce Agent

An AI-powered voice calling agent for e-commerce that helps customers find products through natural phone conversations. Built with Twilio, ElevenLabs, Groq LLM, and ChromaDB.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Twilio](https://img.shields.io/badge/Twilio-Voice-red)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-purple)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)

---

## 📖 Project Overview

This project is a **Voice-based AI Shopping Assistant** that allows customers to call a phone number and shop for products using natural conversation. Here's how we built it step-by-step:

### 🔄 Complete Pipeline

#### 1️⃣ Data Collection
We sourced our product catalog from the **Walmart Products Dataset**:
- 📦 **Dataset**: [Walmart Dataset Samples](https://github.com/luminati-io/Walmart-dataset-samples)
- Contains product names, descriptions, prices, categories, and more
- Raw CSV file stored in `DataCleaning/walmart-products.csv`

#### 2️⃣ Data Cleaning & Preprocessing
The raw data needed cleaning before it could be used effectively:
- Removed duplicate products and null values
- Normalized price formats (removed `$` symbols, converted to float)
- Extracted brand names from product titles
- Categorized products (Laptops, Smartphones, etc.)
- Output: `DataCleaning/cleaned_data.csv`

#### 3️⃣ Vector Database Setup (ChromaDB)
Converted cleaned data into searchable embeddings:
- Used **HuggingFace Embeddings** (`all-MiniLM-L6-v2`) to create vector representations
- Stored in **ChromaDB** with both content and metadata
- **Page Content**: Product name + description (for semantic search)
- **Metadata**: Price, Brand, Category (for filtering)

This allows us to search products semantically ("show me gaming laptops") while also filtering by budget, brand, or category.

#### 4️⃣ Retriever with Smart Filtering
Built a retriever that combines semantic search with metadata filters:
- User says "Samsung phone under 20000" 
- System extracts: `brand=Samsung`, `category=Smartphone`, `budget=20000`
- ChromaDB query: Semantic search + `$and` filters
- Returns top 3 matching products

#### 5️⃣ Session Memory
Implemented two types of memory for natural conversations:
- **Conversation Memory**: Remembers last 10 exchanges in the call
- **User Preferences**: Tracks budget, brand, and category mentioned by user

#### 6️⃣ LLM Engine (Groq)
Connected everything to a fast LLM for response generation:
- Uses **Groq** with `llama-3.1-8b-instant` (super fast - 500+ tokens/sec)
- Takes: Retrieved products + Conversation history + User preferences + Current query
- Generates: Short, voice-friendly responses (1-2 sentences)

#### 7️⃣ Voice Integration (Twilio + ElevenLabs)
Final integration for phone-based interaction:
- **Twilio Voice**: Handles incoming calls and speech-to-text
- **ElevenLabs**: Converts AI responses to natural human-like voice
- **FastAPI**: Webhook server that orchestrates everything

**Result**: Customer calls → Speaks → Gets AI response in natural voice → Continues shopping! 🛒

---

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



**Metadata stored:**
| Field | Type | Example | Use |
|-------|------|---------|-----|
| `price` | float | 499.99 | Budget filtering (`$lte`) |
| `brand` | string | "Samsung" | Brand filtering |
| `category` | string | "Laptop" | Category filtering |



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


## 📝 License

MIT License

---

## 🤝 Contributing

PRs welcome! Please read contributing guidelines first.

