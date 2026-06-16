# Kirana AI - Complete Documentation

## Overview

Kirana AI is an end-to-end enterprise automation platform for Indian Kirana (grocery) stores. It transforms traditional voice/WhatsApp orders into an automated pipeline that handles order processing, credit tracking, and debt collection—all while supporting 10+ Indian languages.

---

## System Architecture

### Microservices (3 Services)

| Service | Port | Technology | Responsibility |
|---------|------|------------|----------------|
| **Ingestion Service** | 8001 | FastAPI + Google Gemini | Voice/Image/Text → Structured Orders |
| **Webhook Service** | 8000 | FastAPI + Twilio | WhatsApp message routing |
| **DB & Alerts Service** | 8002 | FastAPI + MongoDB | Persistence, Khata, Vasooli alerts |

### Frontend
- React + TypeScript + Vite
- Tailwind CSS (dark theme)
- Recharts for analytics
- Lucide React for icons

---

## Core Features

### 1. Multimodal Order Ingestion
- **Audio**: Sarvam Saaras STT → Hindi/Kannada/Telugu/Tamil
- **Image**: Google Cloud Vision OCR
- **Text**: Direct WhatsApp messages

### 2. AI Processing Pipeline
```
Raw Input → Normalization → Gemini/Groq LLM → SKU Matcher → Orchestrator
```

**SKU Matcher** (rapidfuzz):
- 10+ languages supported via alias mapping
- 85%+ match accuracy on phonetic variants
- Khata inquiry detection prevents balance questions from being matched to products

### 3. Khata (Credit) System
- Outstanding balance tracking
- Transaction ledger with ageing analysis
- WhatsApp PDF exports
- Balance inquiry support in 10+ languages

### 4. Vasooli - Debt Collection
- Escalating voice notes (Level 1 → 3)
- ElevenLabs TTS with progressive firmness
- Amount spoken in English for clarity
- Auto-triggers when debt exceeds ₹1500

### 5. AI Demand Forecasting
- XGBoost model (offline training)
- Stockout prediction (days)
- Recommended reorder quantities
- Confidence scores

---

## Database Schema (MongoDB)

**Collections:**
- `orders` - Order history with items, splits
- `khata` - Customer credit ledger with entries
- `customers` - Profiles, lifetime value, order count
- `products` - Inventory, categories, pricing
- `purchase_orders` - Supplier orders
- `suppliers` - Vendor management
- `settings` - Store configuration
- `notifications` - System alerts

---

## Key Integrations

| Service | Purpose |
|---------|---------|
| Google Gemini 2.5 Flash | Order extraction (structured JSON) |
| Groq (Qwen) | Fallback LLM parsing |
| Sarvam AI | STT (10+ Indic languages) |
| ElevenLabs | Multilingual TTS for Vasooli |
| Twilio | WhatsApp messaging |
| Google Cloud Vision | OCR for images |
| MongoDB Atlas | Cloud database |

---

## Environment Variables

### Ingestion Service (.env in ingestion/)
```bash
GEMINI_API_KEY=xxx
GROQ_API_KEY=xxx
SARVAM_API_KEY=xxx
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
DB_ALERTS_URL=http://localhost:8002
```

### DB & Alerts Service (.env in db_alerts/)
```bash
MONGO_URI=mongodb+srv://...
MONGO_DB_NAME=kirana_ai
STORE_ID=store_001
ELEVENLABS_API_KEY=xxx
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
PUBLIC_BASE_URL=http://localhost:8002
```

### Webhook Service (.env in webhook/)
```bash
INGESTION_URL=http://localhost:8001/process
DB_ALERTS_URL=http://localhost:8002/log
SHOPKEEPER_PHONE=whatsapp:+919986013436
```

### Frontend (.env in frontend/)
```bash
VITE_INGESTION_URL=http://localhost:8001
VITE_DB_ALERTS_URL=http://localhost:8002
```

---

## Deployment

### Local Development
```bash
# Terminal 1 - DB & Alerts
cd db_alerts
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8002

# Terminal 2 - Ingestion
cd ingestion
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Terminal 3 - Webhook
cd webhook
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 4 - Frontend
cd frontend
npm install
npm run dev
```

### Production
- Use ngrok/Vultr for public URLs
- Set `PUBLIC_BASE_URL` for audio file serving
- MongoDB Atlas for persistence
- Use `--host 0.0.0.0` for public access

---

## Sample Order Flow

```
Customer WhatsApp: "20kg rice for me, 10kg godhi hittu for Abyud"
    ↓
Twilio Webhook (Person 2 - Port 8000)
    ↓
Ingestion (Person 1 - Port 8001): 
    STT → Normalize → Gemini → SKU Match → Batch Orders
    ↓
DB & Alerts (Person 3 - Port 8002): 
    Store order → Update Khata → Send receipts
    ↓
WhatsApp Receipts to each customer
    ↓
Vasooli (if khata debt > ₹1500)
```

---

## Supported Languages

### Full Support
- Hindi (hi)
- Kannada (kn)
- English (en)

### Fallback to Hindi
- Tamil (ta)
- Telugu (te)
- Malayalam (ml)
- Marathi (mr)
- Gujarati (gu)
- Bengali (bn)
- Punjabi (pa)
- Odia (or)

---

## Performance Metrics

- Order processing: ~3-5 seconds
- SKU matching accuracy: 88-95%
- Vasooli voice generation: ~2 seconds
- Supports 10+ concurrent orders

---

## Project Structure

```
KiranaAI/
├── db_alerts/              # Person 3 - DB & Alerts
│   ├── alerts.py           # Twilio/ElevenLabs integration
│   ├── main.py             # FastAPI server
│   ├── mongo_connector.py  # MongoDB operations
│   └── requirements.txt
├── frontend/               # React Dashboard
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── pages/          # Dashboard pages
│   │   └── services/       # API clients
│   └── package.json
├── ingestion/              # Person 1 - Order Processing
│   ├── data/               # SKU catalog
│   ├── gemini.py           # Gemini/Groq parsing
│   ├── main.py             # FastAPI server
│   ├── orchestrator.py     # Order orchestration
│   ├── sarvam.py           # Sarvam STT/OCR
│   ├── sku_match.py        # Product matching
│   └── utils.py            # Normalization utilities
├── ML/                     # Machine Learning
│   ├── generate_data.py    # Synthetic data generation
│   ├── train_xgboost.py    # Model training
│   └── src/                # Feature engineering
└── webhook/                # Person 2 - Twilio Webhook
    └── main.py             # Webhook receiver
```

---

## API Endpoints

### Ingestion Service (Port 8001)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/process` | POST | Process text/audio/image order |
| `/health` | GET | Health check |

### DB & Alerts Service (Port 8002)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/log` | POST | Log order to MongoDB |
| `/orders` | GET | List recent orders |
| `/khata/{name}` | GET | Get customer khata ledger |
| `/khata/tx` | POST | Add khata transaction |
| `/dashboard` | GET | Dashboard metrics |
| `/analytics` | GET | Analytics data |
| `/forecast` | GET | ML forecasts |
| `/products` | GET/POST | Product CRUD |
| `/customers` | GET/POST | Customer CRUD |
| `/suppliers` | GET/POST | Supplier CRUD |
| `/purchase_orders` | GET/POST | Purchase order CRUD |
| `/vasooli` | POST | Manual debt collection |

### Webhook Service (Port 8000)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | Twilio webhook receiver |
| `/health` | GET | Health check |