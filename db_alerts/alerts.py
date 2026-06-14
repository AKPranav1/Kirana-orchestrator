"""
alerts.py — Kirana AI | Person 3
Handles: multilingual text receipts + escalating Vasooli (debt-collection) voice notes

FIXES APPLIED:
  [Fix 1] TRANSLATIONS dict: hi, kn, en fully translated; ta/te/ml/bn/gu/mr/or/pa → Hindi fallback
  [Fix 2] Text-Only Default: /log sends text receipt ONLY. No audio for normal orders.
  [Fix 3] Audio is now RESERVED for Vasooli (debt collection) voice notes only.
  [Fix 4] Escalating firmness: reminder_count drives voice settings (calm → firm → stern).
  [Fix 5] Amount (money) spoken in ENGLISH ONLY for clarity, rest in native language.
"""

import io
import os
import uuid
import requests
from pathlib import Path
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# ── ElevenLabs ─────────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam: clear, neutral
ELEVENLABS_MODEL    = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# ── Twilio ──────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WA_FROM      = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# ── Audio serving (ngrok URL in local dev, Vultr IP on cloud) ──────────────────
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8002")
AUDIO_DIR       = Path(__file__).parent / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)


# ── Fix 1: Multilingual Translation Table ─────────────────────────────────────
# Amount placeholder {amount_en} will be replaced with ENGLISH number
TRANSLATIONS: dict[str, dict[str, str]] = {
    "hi": {
        "receipt_title": "🛒 *Kirana AI Receipt*",
        "customer":      "👤 Grahak",
        "subtotal":      "Subtotal",
        "discount":      "🎉 Bulk Discount (10%)",
        "total":         "💰 *Total*",
        # Vasooli escalation scripts - amount_spoken in ENGLISH
        "vasooli_1": (
            "Namaste {name}. Kirana store se bol rahe hain. "
            "Aapka khata balance {amount_en} rupees hai. Kripya payment kar dein. Dhanyavaad."
        ),
        "vasooli_2": (
            "Suniye {name}, aapka khata balance ab {amount_en} rupees ho gaya hai. "
            "Payment ki date nikal rahi hai. Kripya jaldi clear karein."
        ),
        "vasooli_3": (
            "ALERT! {name}, aapka balance {amount_en} rupees limit cross kar chuka hai. "
            "Khata band kiya ja raha hai. Turant payment karein!"
        ),
    },
    "kn": {
        "receipt_title": "🛒 *ಕಿರಾಣಿ AI ರಸೀದಿ*",
        "customer":      "👤 ಗ್ರಾಹಕ (Customer)",
        "subtotal":      "ಉಪಮೊತ್ತ (Subtotal)",
        "discount":      "🎉 ರಿಯಾಯಿತಿ (Discount 10%)",
        "total":         "💰 *ಒಟ್ಟು (Total)*",
        "vasooli_1": (
            "Namaskara {name}. Kirana angadiyinda kare madutiddene. "
            "Nimma khata balance {amount_en} rupees. Dayavittu payment madiri. Dhanyavada."
        ),
        "vasooli_2": (
            "Keli {name}, nimma khata balance eega {amount_en} rupees aagide. "
            "Dayavittu tondane clear madiri."
        ),
        "vasooli_3": (
            "Echcharike! {name}, nimma balance {amount_en} rupees limit daati hode. "
            "Tondane payment madiri, illadidare khata suspend agutte!"
        ),
    },
    "en": {
        "receipt_title": "🛒 *Kirana AI Receipt*",
        "customer":      "👤 Customer",
        "subtotal":      "Subtotal",
        "discount":      "🎉 Bulk Discount (10%)",
        "total":         "💰 *Total*",
        "vasooli_1": (
            "Hello {name}. This is a gentle reminder from the Kirana store. "
            "Your outstanding balance is {amount_en} rupees. Please make a payment at your earliest convenience."
        ),
        "vasooli_2": (
            "Hi {name}, your outstanding balance has now reached {amount_en} rupees. "
            "Please clear your dues immediately."
        ),
        "vasooli_3": (
            "URGENT NOTICE! {name}, your debt of {amount_en} rupees is overdue. "
            "Your store credit has been suspended until payment is received."
        ),
    },
}

# Map all remaining Sarvam codes safely to Hindi (guaranteed non-crash)
for _code in ["ta", "te", "ml", "bn", "gu", "mr", "or", "pa"]:
    TRANSLATIONS[_code] = TRANSLATIONS["hi"]


def _get_text(lang: str, key: str, **kwargs) -> str:
    """Safe multilingual lookup. Falls back hi → key string to never raise."""
    lang     = (lang or "hi").lower().strip()
    t        = TRANSLATIONS.get(lang, TRANSLATIONS["hi"])
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

    bill  = f"{_get_text(lang, 'receipt_title')}\n"
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
        per_person  = round(order.get("total_amount", 0) / num_parties, 2)
        bill += f"\n👥 Split {num_parties} ways: ₹{per_person} each\n"
        bill += f"   (with: {', '.join(split_with)})\n"

    return bill


def send_khata_pdf_via_whatsapp(customer_name: str, phone: str, khata_doc: dict) -> None:
    """Generate a PDF of the khata ledger and send via WhatsApp media."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not set in .env!")

    pdf_buffer = io.BytesIO()
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        hs = ParagraphStyle('H', parent=styles['Heading1'], fontSize=18, leading=22, spaceAfter=10)
        ms = ParagraphStyle('M', parent=styles['Normal'], fontSize=11, leading=14, spaceAfter=6)

        story = [Paragraph(f"<b>KHATA LEDGER — {customer_name.upper()}</b>", hs)]
        story.append(Paragraph(f"<b>Total Outstanding:</b> ₹{khata_doc.get('total_outstanding', 0):.2f}", ms))
        story.append(Spacer(1, 12))

        entries = khata_doc.get("entries", [])
        if entries:
            data = [["Date", "Order ID", "Amount", "Settled"]]
            for e in entries:
                data.append([
                    str(e.get("date", ""))[:19],
                    e.get("order_id", "")[:8],
                    f"₹{e.get('amount', 0):.2f}",
                    "✅" if e.get("settled") else "❌",
                ])
            t = Table(data, colWidths=[180, 100, 100, 80])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("No entries recorded.", ms))

        doc.build(story)
    except ImportError:
        pdf_buffer.write(b"PDF library not available; send text-only summary.")
    pdf_buffer.seek(0)

    filename = f"khata_{uuid.uuid4().hex[:8]}.pdf"
    filepath = AUDIO_DIR / filename
    filepath.write_bytes(pdf_buffer.read())
    pdf_buffer.seek(0)

    pdf_url = f"{PUBLIC_BASE_URL}/audio/{filename}"
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=TWILIO_WA_FROM,
        to=_normalize_phone(phone),
        media_url=[pdf_url],
        body=f"📄 Khata Ledger — {customer_name}\nOutstanding: ₹{khata_doc.get('total_outstanding', 0):.2f}",
    )
    print(f"[Twilio] ✅ Khata PDF → {phone} | URL={pdf_url} | SID={message.sid}")


def send_text_message(phone: str, body: str) -> None:
    """Send a plain text WhatsApp message — no receipt formatting."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not set in .env!")
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=TWILIO_WA_FROM,
        to=_normalize_phone(phone),
        body=body,
    )
    print(f"[Twilio] ✅ Text → {phone} | SID={message.sid}")


def send_receipt_only(order: dict, shopkeeper_phone: str) -> None:
    """
    Fix 2: Sends a TEXT-ONLY WhatsApp receipt to the shopkeeper.
    No audio file generated. No ElevenLabs call. No cost on free tier.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not set in .env!")

    client  = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
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

    url     = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key":   ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept":       "audio/mpeg",
    }
    payload = {
        "text":           text,
        "model_id":       ELEVENLABS_MODEL,
        "voice_settings": settings,
    }

    preview = text[:80] + ("..." if len(text) > 80 else "")
    print(f"[ElevenLabs] 📤 Generating: \"{preview}\"")

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
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
    client    = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message   = client.messages.create(
        from_=TWILIO_WA_FROM,
        to=_normalize_phone(phone),
        media_url=[audio_url],
        body=body,
    )
    print(f"[Twilio] ✅ Audio → {phone} | URL={audio_url} | SID={message.sid}")


# ── Fix 3 + Fix 4 + Fix 5: Escalating Vasooli Voice Notes with English Amount ──
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
    
    Fix 5 — Amount (money) is spoken in ENGLISH ONLY for clarity.
      Example: "1500" spoken as "fifteen hundred" or "one thousand five hundred"
    """
    level = min(reminder_count, 3)  # Hard cap — no escalation beyond stern
    
    # Format the amount in English words for clarity
    amount_in_english = _format_amount_in_english(outstanding_amount)
    
    if level == 1:
        text     = _get_text(lang, "vasooli_1", name=customer_name, amount_en=amount_in_english)
        settings = {
            "stability": 0.70, "similarity_boost": 0.75,
            "style": 0.00, "use_speaker_boost": True,
        }
    elif level == 2:
        text     = _get_text(lang, "vasooli_2", name=customer_name, amount_en=amount_in_english)
        settings = {
            "stability": 0.50, "similarity_boost": 0.85,
            "style": 0.40, "use_speaker_boost": True,
        }
    else:  # level == 3
        text     = _get_text(lang, "vasooli_3", name=customer_name, amount_en=amount_in_english)
        settings = {
            "stability": 0.30, "similarity_boost": 0.95,
            "style": 0.80, "use_speaker_boost": True,
        }

    urgency_emojis = {1: "🙏", 2: "⚠️", 3: "🚨"}
    emoji = urgency_emojis[level]

    print(f"[Vasooli] {emoji} Level {level} reminder → {customer_name} | ₹{outstanding_amount} (spoken: {amount_in_english})")

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


def _format_amount_in_english(amount: float) -> str:
    """
    Convert a numeric amount to English words for clear speech.
    Example: 1250 -> "one thousand two hundred fifty"
             1500 -> "fifteen hundred" OR "one thousand five hundred"
             45 -> "forty five"
    """
    amount_int = int(round(amount))
    
    if amount_int == 0:
        return "zero"
    
    # Handle amounts up to 99999
    if amount_int >= 100000:
        lakhs = amount_int // 100000
        remainder = amount_int % 100000
        if remainder > 0:
            return f"{_format_number_words(lakhs)} lakh {_format_number_words(remainder)}"
        return f"{_format_number_words(lakhs)} lakh"
    
    return _format_number_words(amount_int)


def _format_number_words(n: int) -> str:
    """Convert integer to English words."""
    if n == 0:
        return "zero"
    
    ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
            "seventeen", "eighteen", "nineteen"]
    
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    
    if n < 20:
        return ones[n]
    
    if n < 100:
        return tens[n // 10] + ("" if n % 10 == 0 else " " + ones[n % 10])
    
    if n < 1000:
        return ones[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + _format_number_words(n % 100))
    
    if n < 100000:
        return _format_number_words(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + _format_number_words(n % 1000))
    
    return str(n)  # fallback