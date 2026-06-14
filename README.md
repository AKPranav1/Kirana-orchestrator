# Kirana AI – Autonomous Retail Operating System

<div align="center">
  <strong>AI‑powered, WhatsApp‑first ERP for Indian Kirana stores</strong>
</div>

---

## 📌 Overview

**Kirana AI** is a production‑grade, full‑stack operating system that digitises and automates the daily operations of small‑format retail stores (Kirana shops). It bridges the gap between a shopkeeper’s handwritten *khata* (credit ledger), incoming WhatsApp orders, inventory management, and AI‑driven demand forecasting.

The system is built for **high‑fidelity automation**:

- 📱 **WhatsApp Order Intake** – Customers send text, audio, or images of handwritten lists; the system extracts structured orders.
- 🧠 **Multilingual AI Parsing** – Supports 10+ Indian languages (Hindi, Kannada, Tamil, Telugu, Marathi, Gujarati, Bengali, Punjabi, Malayalam, Odia) via Gemini Flash + fallback heuristic.
- 📖 **Khata (Credit) Ledger** – Full double‑entry bookkeeping with per‑customer split‑billing, ageing analysis, and automated recovery voice notes (Vasooli).
- 📈 **Demand Forecasting** – XGBoost models trained on synthetic data (180 days, 20 store clusters, 25 products) to predict stockouts and suggest reorder quantities.
- 🎙️ **Voice/Image OCR** – Sarvam AI STT and Google Cloud Vision for handling audio notes and handwritten order photos.
- 🤖 **React Dashboard** – Real‑time metrics, order inspector, inventory control, and ML‑driven “Stock Suggestions” page.

The system is split into three independent microservices (Personas 1‑3), making it modular, scalable, and demo‑ready.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Twilio WhatsApp                             │
└────────┬────────────────────────────────────────────────────────────┘
         │ webhook
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Person 1       │     │  Person 2       │     │  Person 3       │
│  /webhook       │────▶│  /process       │────▶│  /log           │
│  (Twilio        │     │  (Ingestion)    │     │  (MongoDB +     │
│   router)       │     │   Port 8001     │     │   Alerts)       │
│   Port 8003     │     │                 │     │   Port 8002     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                   ┌─────────────┐
                                                   │  MongoDB    │
                                                   │  Atlas      │
                                                   └─────────────┘
         ┌─────────────────────────────────────────────────────────┐
         │                    React Frontend (Vite)                │
         │                     Port 3000                           │
         └─────────────────────────────────────────────────────────┘
```

**Three Core Services**:

1. **Person 1 – Webhook Receiver** (`webhook/`)  
   - Exposes `/webhook` for Twilio WhatsApp callbacks.  
   - Forwards text, audio, or image media to the Ingestion service.

2. **Person 2 – Ingestion Engine** (`ingestion/`)  
   - Multimodal processing: Sarvam STT for audio, Google Cloud Vision OCR for images.  
   - Gemini Flash extraction of structured order (items, quantities, splits, payment intent).  
   - Canonical SKU matching against a local `sku_catalog.json` with fuzzy fallback.  
   - Orchestrates split bills (equal or per‑person) and computes per‑party totals.

3. **Person 3 – DB + Alerts** (`db_alerts/`)  
   - FastAPI server that enriches items with real‑time prices, applies bulk discounts (10% over ₹1500).  
   - Writes to MongoDB (collections: `orders`, `khata`, `customers`, `products`, `purchase_orders`, `suppliers`).  
   - Sends **text‑only** WhatsApp receipts to the shopkeeper (no audio for regular orders).  
   - Automatically triggers **escalating Vasooli voice notes** when a customer’s khata debt exceeds ₹1500.  
   - Serves ML forecasts (from `model_forecasts.pkl`) to the frontend.

**Frontend** (`frontend/`)  
- React + TypeScript + Tailwind CSS + Recharts.  
- Pages: Dashboard, Live Orders, Customers, Khata Ledger, Inventory, Sales Insights, Stock Suggestions (ML), Reports, Settings.  
- Communicates with Person 3 (`/dashboard`, `/orders`, `/forecast`, etc.) and Ingestion (`/process` for manual orders).

---

## ✨ Key Features

### 🤖 AI‑Powered Order Processing
- **Multilingual text:** Hinglish + 9 other languages – the Gemini prompt recognises split instructions (`"Abhi ke saath"`, `"with Rahul"`) and payment intent (`"khate mein daal do"`).
- **Audio notes:** Customers can speak their order; Sarvam Saaras STT converts to text.
- **Handwritten lists:** Image → Google Cloud Vision OCR → text extraction.

### 📒 Khata (Credit) System
- Each order can be split equally or per‑item among multiple customers.
- Khata ledger tracks `credit` (purchase) and `payment` entries.
- Ageing report (0–7 days, 8–15 days, 16–30 days, >30 days) helps prioritise recovery.
- **Vasooli Engine:** Automatic voice notes (ElevenLabs) sent to overdue customers – firmness escalates with reminder count.

### 📊 ML Demand Forecasting
- Synthetic dataset generator (`ML/generate_data.py`) simulates 20 stores × 25 products × 180 days with neighbourhood, weather, festival, and salary‑day effects.
- XGBoost regressor predicts `quantity_sold`; classifier predicts `stockout_occurred`.
- Frontend “Stock Suggestions” page shows predicted stockout days and recommended reorder quantities.

### 📱 React Dashboard
- **Live Metrics:** Today’s revenue, orders, outstanding khata, low‑stock count, pending deliveries.
- **Order Inspector:** View details of any order – items, splits, total.
- **Product Management:** Add products, update stock, view profit margins.
- **Customer Profiles:** Lifetime spend, order history, khata balance – with one‑click WhatsApp reminder.
- **Purchase Orders:** Create, approve, and receive B2B stock orders; automatically updates inventory.

### 🔔 Notification & Alert Stack
- Shopkeeper receives **text‑only** WhatsApp receipt after every order (no audio cost).
- Low stock alerts appear in the top bell icon.
- Khata overdue reminders can be manually triggered from the Customers page.

---

## 🛠️ Tech Stack

| Layer          | Technologies                                                                                             |
|----------------|----------------------------------------------------------------------------------------------------------|
| **Backend**    | FastAPI, Python 3.11, Uvicorn, Pydantic, HTTPX                                                          |
| **Database**   | MongoDB Atlas (PyMongo)                                                                                  |
| **AI & ML**    | Gemini Flash (Google GenAI), Sarvam AI (STT, OCR), Groq (fallback), XGBoost, scikit‑learn, pandas, numpy |
| **WhatsApp**   | Twilio WhatsApp Business API                                                                             |
| **Audio/OCR**  | ElevenLabs (TTS for Vasooli), Google Cloud Vision                                                        |
| **Frontend**   | React 19, TypeScript, Vite, Tailwind CSS, Recharts, React Router, Lucide icons, TanStack Query          |
| **PDF Gen**    | ReportLab (invoices, khata statements)                                                                   |
| **Deployment** | Docker‑ready, can run on Cloud Run, Vultr, or local                                                      |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- MongoDB Atlas cluster (free tier works) or local MongoDB
- Twilio account with a WhatsApp Business sandbox
- API keys: Gemini, Sarvam, ElevenLabs, Google Cloud Vision (optional), Groq (optional)

### Environment Variables

Create `.env` files in `ingestion/`, `db_alerts/`, and `webhook/`.

**Ingestion** (`ingestion/.env`):
```ini
GEMINI_API_KEY=your_gemini_key
SARVAM_API_KEY=your_sarvam_key
GROQ_API_KEY=your_groq_key          # optional fallback
GOOGLE_API_KEY=your_gcp_key         # for Vision OCR
MONGO_URI=mongodb+srv://...
DB_ALERTS_URL=http://localhost:8002
```

**DB + Alerts** (`db_alerts/.env`):
```ini
MONGO_URI=mongodb+srv://...
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
ELEVENLABS_API_KEY=your_elevenlabs_key
PUBLIC_BASE_URL=https://your-ngrok-or-vultr-url   # for audio file serving
STORE_ID=store_001
```

**Webhook** (`webhook/.env`):
```ini
INGESTION_URL=http://localhost:8001/process
DB_ALERTS_URL=http://localhost:8002/log
SHOPKEEPER_PHONE=whatsapp:+919999999999
```

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/kirana-ai.git
   cd kirana-ai
   ```

2. **Set up Python services** (three terminals)
   ```bash
   # Terminal 1 – Ingestion
   cd ingestion
   python -m venv venv
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8001

   # Terminal 2 – DB + Alerts
   cd ../db_alerts
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8002

   # Terminal 3 – Webhook (optional for local testing)
   cd ../webhook
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8003
   ```

3. **Set up frontend**
   ```bash
   cd ../frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with backend URLs (usually http://localhost:8002)
   npm run dev
   ```
   Frontend runs on `http://localhost:3000`.

4. **Train ML model (optional, but needed for forecasts)**
   ```bash
   cd ../ML
   pip install -r requirements.txt
   python generate_data.py        # creates synthetic_kirana_dataset.csv
   python train_xgboost.py        # generates db_alerts/model_forecasts.pkl
   ```

5. **Expose webhook with ngrok** (for Twilio)
   ```bash
   ngrok http 8003
   ```
   Configure your Twilio sandbox webhook URL to `https://your-ngrok.ngrok.io/webhook`.

### Testing the Pipeline

- **Text order:** Send a WhatsApp message like:  
  `"2 kilo aata aur ek doodh ka packet, Rahul ke saath split karna hai, khate mein daal do"`
- **Audio order:** Send a voice note.
- **Image order:** Send a photo of a handwritten list.

The shopkeeper will receive a text receipt. If the order uses khata and a customer’s total debt exceeds ₹1500, an **automatic Vasooli voice note** will be sent to that customer.

---

## 📂 Repository Structure

```
.
├── .github/workflows/          # CI (pytest for ingestion)
├── db_alerts/                  # Person 3: MongoDB + alerts + forecasts
│   ├── alerts.py               # ElevenLabs + Twilio logic
│   ├── mongo_connector.py      # Order write, khata, loyalty, pricing
│   ├── main.py                 # FastAPI app (port 8002)
│   └── model_forecasts.pkl     # Serialised ML forecasts
├── frontend/                   # React + TypeScript frontend
│   ├── src/
│   │   ├── components/         # Reusable UI (MetricCard, Sidebar, MLDashboard)
│   │   ├── pages/              # Dashboard, Orders, Khata, Forecasts, etc.
│   │   ├── services/           # API clients for each backend
│   │   └── types.ts            # Shared TypeScript interfaces
│   └── package.json
├── ingestion/                  # Person 2: Multimodal parsing & SKU matching
│   ├── data/sku_catalog.json   # Canonical product aliases (10+ languages)
│   ├── gemini.py               # Gemini + Groq + heuristic fallback
│   ├── sarvam.py               # Sarvam STT / OCR integration
│   ├── sku_match.py            # Fuzzy matching against catalog
│   ├── orchestrator.py         # Split logic, price lookup, khata fetch
│   └── main.py                 # FastAPI (port 8001)
├── ML/                         # Demand forecasting
│   ├── generate_data.py        # Synthetic dataset generator
│   ├── train_xgboost.py        # XGBoost regressor + classifier
│   ├── src/                    # Feature engineering & simulation
│   └── product_to_canonical.json # Mapping to product IDs
├── webhook/                    # Person 1: Twilio webhook receiver
│   └── main.py
├── schema.json                 # MongoDB JSON schema definitions
└── README.md                   # This file
```

---

## 🧪 Demo Scenarios

### 1. Split Khata Order
**Customer text:** `"1kg aata, 2 litre milk. Abhi ke saath split kar do. Khate mein daal dena."`  
**Result:**  
- Two splits: “default” (customer) and “Abhi”.  
- Bill equally split, each half added to their khata.  
- Shopkeeper receives text receipt.  
- If Abhi’s total outstanding > ₹1500, he gets a voice note.

### 2. Image Order (Handwritten)
A customer sends a photo of a paper with: `"3 packet maggi, 1 litre oil"`  
- OCR extracts text → Gemini parses → order processed.

### 3. Manual Order via Dashboard
Shopkeeper clicks “+ New Order”, selects products, adds to cart, chooses “Cash” or “Khata” – order is persisted and stock reduced.

### 4. Forecast & Reorder
- ML page shows `"Milk: stockout in 2 days, reorder 50 units"`.  
- Click “Restock Cargo” → creates a Purchase Order (`Awaiting Approval`).  
- Approve → status becomes `In Transit`.  
- Receive → stock automatically incremented.

---

## 🌍 Multilingual Support

| Language | Code | Supported For                           |
|----------|------|------------------------------------------|
| Hindi    | hi   | Text extraction, OCR, receipts, Vasooli |
| Kannada  | kn   | Full (script & translit)                 |
| Tamil    | ta   | Full                                     |
| Telugu   | te   | Full                                     |
| Marathi  | mr   | Full                                     |
| Gujarati | gu   | Full                                     |
| Bengali  | bn   | Full                                     |
| Punjabi  | pa   | Full                                     |
| Malayalam| ml   | Full                                     |
| Odia     | or   | Full                                     |
| English  | en   | Full                                     |

All Sarvam language codes map to a translated receipt and escalating debt‑collection script.

---

## 📈 Performance & Scaling

- **Ingestion:** Under 2 seconds for text/audio/image → order (Gemini Flash + fuzzy match).  
- **MongoDB:** Indexes on `created_at`, `customer_name`, `store_id` keep dashboard queries < 50ms.  
- **Forecast API:** Loads pre‑computed `.pkl` – response < 10ms.  
- **Frontend:** Vite + React – Lighthouse score > 90.  
- **ML Training:** 90k rows → full pipeline (generation + XGBoost) ~2 minutes on a laptop.

---

## 🔒 Security & Data Privacy

- All API keys stored in `.env` – never committed.  
- MongoDB Atlas uses VPC peering (recommended) or IP whitelist.  
- Twilio media URLs are signed and expire.  
- No customer PII logged beyond phone/name (can be anonymised).  
- PDF bills generated on‑the‑fly, not persisted longer than needed.

---

## 🧪 Testing

```bash
# Run ingestion unit tests (requires pytest)
pytest ingestion/tests/

# Test Person 3 standalone (MongoDB, ElevenLabs, Twilio)
cd db_alerts
python debug_local.py mongo        # test MongoDB write
python debug_local.py alert        # full alert (needs valid phone in .env)
python debug_local.py full         # end-to-end with mock order
```

---

## 🤝 Contributing

1. Fork the repository.  
2. Create a feature branch (`git checkout -b feature/amazing-feature`).  
3. Commit your changes.  
4. Push to the branch.  
5. Open a Pull Request.

Please ensure your code passes `pytest` and follows the existing code style (Black for Python, ESLint for TypeScript).

---

## 📄 License

**Apache 2.0** – See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Google Gemini API](https://ai.google.dev/gemini) – structured extraction.  
- [Sarvam AI](https://sarvam.ai) – speech‑to‑text & OCR for Indian languages.  
- [ElevenLabs](https://elevenlabs.io) – multilingual voice synthesis for Vasooli.  
- [Twilio](https://twilio.com) – WhatsApp Business API.  
- [XGBoost](https://xgboost.ai) – demand forecasting.  
- [MongoDB Atlas](https://mongodb.com/atlas) – cloud database.  
- [Vite](https://vitejs.dev) + [Tailwind CSS](https://tailwindcss.com) – frontend stack.

---