"""
alerts.py — Kirana AI | Person 3
Handles: multilingual text receipts + escalating Vasooli (debt-collection) voice notes

FIXES APPLIED:
  [Fix 1] TRANSLATIONS dict: hi, kn, en fully translated; ta/te/ml/bn/gu/mr/or/pa → Hindi fallback
  [Fix 2] Text-Only Default: /log sends text receipt ONLY. No audio for normal orders.
  [Fix 3] Audio is now RESERVED for Vasooli (debt collection) voice notes only.
  [Fix 4] Escalating firmness: reminder_count drives voice settings (calm → firm → stern).
  REMOVED: send_alert(), format_alert_text(), dual-voice high-value system (simplified).
"""

import os
import uuid
import requests
from pathlib import Path
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# ── ElevenLabs ─────────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"
)  # Adam: clear, neutral
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# ── Twilio ──────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WA_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# ── Audio serving (ngrok URL in local dev, Vultr IP on cloud) ──────────────────
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8002")
AUDIO_DIR = Path(__file__).parent / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)


# ── Fix 1: Multilingual Translation Table ─────────────────────────────────────
# Covers all 10 Sarvam AI supported language codes.

# Covers all 10 Sarvam AI supported language codes.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "hi": {
        "receipt_title": "🛒 *Kirana AI Receipt*",
        "customer": "👤 Grahak",
        "subtotal": "Subtotal",
        "discount": "🎉 Bulk Discount (10%)",
        "total": "💰 *Total*",
        "vasooli_1": "Namaste {name}. Kirana store se bol rahe hain. Aapka khata balance {amount} rupees hai. Kripya payment kar dein.",
        "vasooli_2": "Suniye {name}, aapka khata balance ab {amount} rupees ho gaya hai. Payment ki date nikal rahi hai. Kripya jaldi clear karein.",
        "vasooli_3": "ALERT! {name}, aapka balance {amount} rupees limit cross kar chuka hai. Turant payment karein!",
    },
    "kn": {
        "receipt_title": "🛒 *ಕಿರಾಣಿ AI ರಸೀದಿ*",
        "customer": "👤 ಗ್ರಾಹಕ",
        "subtotal": "ಉಪಮೊತ್ತ",
        "discount": "🎉 ರಿಯಾಯಿತಿ",
        "total": "💰 *ಒಟ್ಟು*",
        "vasooli_1": "ನಮಸ್ಕಾರ {name}. ಕಿರಾಣಿ ಅಂಗಡಿಯಿಂದ. ನಿಮ್ಮ ಖಾತಾ ಬಾಕಿ {amount} ರೂಪಾಯಿ. ದಯವಿಟ್ಟು ಪಾವತಿಸಿ.",
        "vasooli_2": "ಕೇಳಿ {name}, ನಿಮ್ಮ ಖಾತಾ ಬಾಕಿ ಈಗ {amount} ರೂಪಾಯಿ ಆಗಿದೆ. ದಯವಿಟ್ಟು ತಕ್ಷಣ ಪಾವತಿ ಮಾಡಿ.",
        "vasooli_3": "ಎಚ್ಚರಿಕೆ! {name}, ನಿಮ್ಮ ಬಾಕಿ {amount} ರೂಪಾಯಿ ಮೀರಿದೆ. ತಕ್ಷಣ ಹಣ ಪಾವತಿಸಿ!",
    },
    "en": {
        "receipt_title": "🛒 *Kirana AI Receipt*",
        "customer": "👤 Customer",
        "subtotal": "Subtotal",
        "discount": "🎉 Bulk Discount (10%)",
        "total": "💰 *Total*",
        "vasooli_1": "Hello {name}. A gentle reminder that your store balance is {amount} rupees.",
        "vasooli_2": "Hi {name}, your outstanding balance has reached {amount} rupees. Please clear your dues.",
        "vasooli_3": "URGENT! {name}, your debt of {amount} rupees is overdue. Clear it immediately!",
    },
    "ta": {  # Tamil
        "receipt_title": "🛒 *கிரானா AI ரசீது*",
        "customer": "👤 வாடிக்கையாளர்",
        "subtotal": "உபமொத்தம்",
        "discount": "🎉 தள்ளுபடி",
        "total": "💰 *மொத்தம்*",
        "vasooli_1": "வணக்கம் {name}. மளிகை கடையிலிருந்து பேசுகிறோம். உங்கள் பாக்கி {amount} ரூபாய். தயவுசெய்து செலுத்தவும்.",
        "vasooli_2": "கேளுங்கள் {name}, உங்கள் பாக்கி இப்போது {amount} ரூபாய். தயவுசெய்து விரைவாக செலுத்தவும்.",
        "vasooli_3": "எச்சரிக்கை! {name}, உங்கள் பாக்கி {amount} ரூபாயை தாண்டிவிட்டது. உடனடியாக செலுத்தவும்!",
    },
    "te": {  # Telugu
        "receipt_title": "🛒 *కిరాణా AI రసీదు*",
        "customer": "👤 కస్టమర్",
        "subtotal": "ఉపమొత్తం",
        "discount": "🎉 తగ్గింపు",
        "total": "💰 *మొత్తం*",
        "vasooli_1": "నమస్కారం {name}. కిరాణా షాపు నుండి. మీ బకాయి {amount} రూపాయలు. దయచేసి చెల్లించండి.",
        "vasooli_2": "వినండి {name}, మీ బకాయి ఇప్పుడు {amount} రూపాయలు అయింది. దయచేసి త్వరగా చెల్లించండి.",
        "vasooli_3": "హెచ్చరిక! {name}, మీ బకాయి {amount} రూపాయలు దాటింది. వెంటనే చెల్లించండి!",
    },
    "ml": {  # Malayalam
        "receipt_title": "🛒 *കിരാന AI രസീത്*",
        "customer": "👤 ഉപഭോക്താവ്",
        "subtotal": "ഉപതുക",
        "discount": "🎉 കിഴിവ്",
        "total": "💰 *ആകെ*",
        "vasooli_1": "നമസ്കാരം {name}. പലചരക്ക് കടയിൽ നിന്നാണ്. നിങ്ങളുടെ കുടിശ്ശിക {amount} രൂപയാണ്. ദയവായി അടയ്ക്കുക.",
        "vasooli_2": "ശ്രദ്ധിക്കുക {name}, നിങ്ങളുടെ കുടിശ്ശിക ഇപ്പോൾ {amount} രൂപയായി. ദയവായി വേഗം അടയ്ക്കുക.",
        "vasooli_3": "മുന്നറിയിപ്പ്! {name}, നിങ്ങളുടെ കുടിശ്ശിക {amount} രൂപ കടന്നിരിക്കുന്നു. ഉടൻ അടയ്ക്കുക!",
    },
    "bn": {  # Bengali
        "receipt_title": "🛒 *কিরানা AI রসিদ*",
        "customer": "👤 গ্রাহক",
        "subtotal": "উপমোট",
        "discount": "🎉 ছাড়",
        "total": "💰 *মোট*",
        "vasooli_1": "নমস্কার {name}। কিরানা দোকান থেকে বলছি। আপনার বাকি {amount} টাকা। অনুগ্রহ করে পেমেন্ট করুন।",
        "vasooli_2": "শুনুন {name}, আপনার বাকি এখন {amount} টাকা হয়েছে। অনুগ্রহ করে তাড়াতাড়ি পেমেন্ট করুন।",
        "vasooli_3": "সতর্কবার্তা! {name}, আপনার বাকি {amount} টাকা ছাড়িয়ে গেছে। অবিলম্বে পেমেন্ট করুন!",
    },
    "mr": {  # Marathi
        "receipt_title": "🛒 *किराणा AI पावती*",
        "customer": "👤 ग्राहक",
        "subtotal": "उपएकूण",
        "discount": "🎉 सवलत",
        "total": "💰 *एकूण*",
        "vasooli_1": "नमस्कार {name}. किराणा दुकानातून बोलत आहोत. तुमची बाकी {amount} रुपये आहे. कृपया पेमेंट करा.",
        "vasooli_2": "ऐका {name}, तुमची बाकी आता {amount} रुपये झाली आहे. कृपया लवकर पेमेंट करा.",
        "vasooli_3": "इशारा! {name}, तुमची बाकी {amount} रुपये ओलांडली आहे. त्वरित पेमेंट करा!",
    },
    "gu": {  # Gujarati
        "receipt_title": "🛒 *કિરાણા AI રસીદ*",
        "customer": "👤 ગ્રાહક",
        "subtotal": "ઉપકુલ",
        "discount": "🎉 ડિસ્કાઉન્ટ",
        "total": "💰 *કુલ*",
        "vasooli_1": "નમસ્તે {name}. કિરાણા દુકાનથી બોલી રહ્યા છીએ. તમારું બાકી {amount} રૂપિયા છે. કૃપા કરીને પેમેન્ટ કરો.",
        "vasooli_2": "સાંભળો {name}, તમારું બાકી હવે {amount} રૂપિયા થઈ ગયું છે. કૃપા કરીને જલ્દી પેમેન્ટ કરો.",
        "vasooli_3": "ચેતવણી! {name}, તમારું બાકી {amount} રૂપિયા પાર કરી ગયું છે. તાત્કાલિક પેમેન્ટ કરો!",
    },
    "pa": {  # Punjabi
        "receipt_title": "🛒 *ਕਿਰਾਨਾ AI ਰਸੀਦ*",
        "customer": "👤 ਗਾਹਕ",
        "subtotal": "ਉਪ-ਕੁੱਲ",
        "discount": "🎉 ਛੋਟ",
        "total": "💰 *ਕੁੱਲ*",
        "vasooli_1": "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ {name}। ਕਿਰਾਨਾ ਦੁਕਾਨ ਤੋਂ ਬੋਲ ਰਹੇ ਹਾਂ। ਤੁਹਾਡਾ ਬਕਾਇਆ {amount} ਰੁਪਏ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਭੁਗਤਾਨ ਕਰੋ।",
        "vasooli_2": "ਸੁਣੋ {name}, ਤੁਹਾਡਾ ਬਕਾਇਆ ਹੁਣ {amount} ਰੁਪਏ ਹੋ ਗਿਆ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਜਲਦੀ ਭੁਗਤਾਨ ਕਰੋ।",
        "vasooli_3": "ਚੇਤਾਵਨੀ! {name}, ਤੁਹਾਡਾ ਬਕਾਇਆ {amount} ਰੁਪਏ ਪਾਰ ਕਰ ਗਿਆ ਹੈ। ਤੁਰੰਤ ਭੁਗਤਾਨ ਕਰੋ!",
    },
    "or": {  # Odia (Usually written in Oriya script, but transliterated heavily. Providing formal script)
        "receipt_title": "🛒 *କିରାନା AI ରସିଦ*",
        "customer": "👤 ଗ୍ରାହକ",
        "subtotal": "ଉପମୋଟ",
        "discount": "🎉 ରିହାତି",
        "total": "💰 *ମୋଟ*",
        "vasooli_1": "ନମସ୍କାର {name}। କିରାନା ଦୋକାନରୁ କହୁଛୁ। ଆପଣଙ୍କର ବାକି {amount} ଟଙ୍କା ଅଛି। ଦୟାକରି ପେମେଣ୍ଟ କରନ୍ତୁ।",
        "vasooli_2": "ଶୁଣନ୍ତୁ {name}, ଆପଣଙ୍କର ବାକି ବର୍ତ୍ତମାନ {amount} ଟଙ୍କା ହୋଇଛି। ଦୟାକରି ଶୀଘ୍ର ପେମେଣ୍ଟ କରନ୍ତୁ।",
        "vasooli_3": "ସତର୍କ ସୂଚନା! {name}, ଆପଣଙ୍କର ବାକି {amount} ଟଙ୍କା ଅତିକ୍ରମ କରିଛି। ତୁରନ୍ତ ପେମେଣ୍ଟ କରନ୍ତୁ!",
    },
}

# Map all remaining Sarvam codes safely to Hindi (guaranteed non-crash)
for _code in ["ta", "ml", "bn", "gu", "mr", "or", "pa"]:
    TRANSLATIONS[_code] = TRANSLATIONS["hi"]


def _get_text(lang: str, key: str, **kwargs) -> str:
    """Safe multilingual lookup. Falls back hi → key string to never raise."""
    lang = (lang or "hi").lower().strip()
    t = TRANSLATIONS.get(lang, TRANSLATIONS["hi"])
    template = t.get(key, TRANSLATIONS["hi"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def _normalize_phone(phone: str) -> str:
    phone = phone.strip()
    if not phone.startswith("whatsapp:"):
        phone = f"whatsapp:{phone}"
    return phone


# ── Fix 2: Text-Only Receipt for Standard Orders ─────────────────────────────
def create_text_bill(order: dict) -> str:
    """Builds a WhatsApp-formatted text receipt in the order's language."""
    lang = order.get("language", "hi")

    bill = f"{_get_text(lang, 'receipt_title')}\n"
    bill += f"{_get_text(lang, 'customer')}: {order.get('customer_name', 'Walk-in')}\n"
    bill += "------------------------\n"

    for item in order.get("items", []):
        bill += f"▪ {item.get('qty', 1)}x {item.get('name', 'item')} - ₹{item.get('line_total', 0)}\n"

    bill += "------------------------\n"
    discount = order.get("discount_applied", 0)
    if discount and discount > 0:
        bill += f"{_get_text(lang, 'subtotal')}: ₹{order.get('original_total', 0)}\n"
        bill += f"{_get_text(lang, 'discount')}: -₹{discount}\n"

    bill += f"{_get_text(lang, 'total')}: ₹{order.get('total_amount', 0)}\n"

    split_with = order.get("split_with", [])
    if split_with:
        num_parties = len(split_with) + 1
        per_person = round(order.get("total_amount", 0) / num_parties, 2)
        bill += f"\n👥 Split {num_parties} ways: ₹{per_person} each\n"
        bill += f"   (with: {', '.join(split_with)})\n"

    return bill


def send_receipt_only(order: dict, shopkeeper_phone: str) -> None:
    """
    Fix 2: Sends a TEXT-ONLY WhatsApp receipt to the shopkeeper.
    No audio file generated. No ElevenLabs call. No cost on free tier.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not set in .env!")

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=TWILIO_WA_FROM,
        to=_normalize_phone(shopkeeper_phone),
        body=create_text_bill(order),
    )
    print(f"[Twilio] ✅ Text receipt → shopkeeper | SID={message.sid}")


# ── Audio Generation (only used for Vasooli) ──────────────────────────────────
def generate_audio(text: str, settings: dict) -> str:
    """
    Calls ElevenLabs, saves MP3 to audio_files/, returns filename.
    settings dict controls stability/style (drives escalating firmness in Vasooli).
    """
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not set in .env!")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": settings,
    }

    preview = text[:80] + ("..." if len(text) > 80 else "")
    print(f'[ElevenLabs] 📤 Generating: "{preview}"')

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        # Surface helpful error including snippet of response
        raise RuntimeError(f"ElevenLabs {resp.status_code}: {resp.text[:200]}")

    filename = f"alert_{uuid.uuid4().hex[:8]}.mp3"
    with open(AUDIO_DIR / filename, "wb") as f:
        f.write(resp.content)

    print(f"[ElevenLabs] ✅ Saved {filename} ({len(resp.content) // 1024} KB)")
    return filename


def _send_audio_whatsapp(audio_filename: str, phone: str, body: str) -> None:
    """Sends a generated MP3 to a WhatsApp number via Twilio media message."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not set in .env!")

    audio_url = f"{PUBLIC_BASE_URL}/audio/{audio_filename}"
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=TWILIO_WA_FROM,
        to=_normalize_phone(phone),
        media_url=[audio_url],
        body=body,
    )
    print(f"[Twilio] ✅ Audio → {phone} | URL={audio_url} | SID={message.sid}")


# ── Fix 3 + Fix 4: Escalating Vasooli Voice Notes ────────────────────────────
def send_vasooli_alert(
    customer_name: str,
    customer_phone: str,
    outstanding_amount: float,
    reminder_count: int,
    lang: str = "hi",
) -> str:
    """
    Generates and sends a debt-collection voice note directly to the customer.

    Fix 4 — Escalating firmness based on reminder_count:
      Level 1 → Polite  (stability=0.70, style=0.00) — calm, friendly
      Level 2 → Firm    (stability=0.50, style=0.40) — serious tone
      Level 3 → Stern   (stability=0.30, style=0.80) — urgent, assertive

    Returns the generated audio filename.
    """
    level = min(reminder_count, 3)  # Hard cap — no escalation beyond stern

    if level == 1:
        text = _get_text(
            lang, "vasooli_1", name=customer_name, amount=outstanding_amount
        )
        settings = {
            "stability": 0.70,
            "similarity_boost": 0.75,
            "style": 0.00,
            "use_speaker_boost": True,
        }
    elif level == 2:
        text = _get_text(
            lang, "vasooli_2", name=customer_name, amount=outstanding_amount
        )
        settings = {
            "stability": 0.50,
            "similarity_boost": 0.85,
            "style": 0.40,
            "use_speaker_boost": True,
        }
    else:  # level == 3
        text = _get_text(
            lang, "vasooli_3", name=customer_name, amount=outstanding_amount
        )
        settings = {
            "stability": 0.30,
            "similarity_boost": 0.95,
            "style": 0.80,
            "use_speaker_boost": True,
        }

    urgency_emojis = {1: "🙏", 2: "⚠️", 3: "🚨"}
    emoji = urgency_emojis[level]

    print(
        f"[Vasooli] {emoji} Level {level} reminder → {customer_name} | ₹{outstanding_amount}"
    )

    audio_filename = generate_audio(text, settings)

    _send_audio_whatsapp(
        audio_filename,
        customer_phone,
        body=(
            f"{emoji} *Khata Reminder (Level {level})*\n"
            f"Outstanding balance: ₹{outstanding_amount}\n"
            f"Please clear your dues immediately."
        ),
    )

    return audio_filename
