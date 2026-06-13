"""
alerts.py — Kirana AI | Person 3
Handles: ElevenLabs TTS generation + Twilio WhatsApp delivery
         + textual receipts + emotion-aware voice alerts
         + automated "Vasooli" (debt collection) voice notes
"""

import os
import uuid
import requests
from pathlib import Path
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# ── ElevenLabs config ──────────────────────────────────────────────────────────
ELEVENLABS_API_KEY   = os.getenv("ELEVENLABS_API_KEY")

# Two voice IDs: a calm default + an energetic one for big-ticket orders
ELEVENLABS_VOICE_ID          = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")        # Adam (neutral, clear)
ELEVENLABS_VOICE_ID_EXCITED  = os.getenv("ELEVENLABS_VOICE_ID_EXCITED", "pNInz6obpgDQGcFmaJgB") # swap for an energetic voice ID
ELEVENLABS_MODEL     = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Threshold for "High-Value Order" emotional alert
HIGH_VALUE_THRESHOLD = 1500.0

# ── Twilio config ──────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WA_FROM       = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# ── Audio file serving ─────────────────────────────────────────────────────────
# PUBLIC_BASE_URL = your ngrok URL (local) or http://VULTR_IP:8002 (cloud)
PUBLIC_BASE_URL  = os.getenv("PUBLIC_BASE_URL", "http://localhost:8002")

AUDIO_DIR = Path(__file__).parent / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────
# STEP A1: Format Hinglish item list
# ──────────────────────────────────────────────
def _format_items_hinglish(items: list) -> str:
    """
    [{"name": "Milk", "qty": 2}, {"name": "Bread", "qty": 1}]
    → "2 Milk aur 1 Bread"
    """
    if not items:
        return "kuch saman"

    parts = [f"{item.get('qty', 1)} {item.get('name', 'item')}" for item in items]

    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} aur {parts[1]}"
    # 3+ items: "A, B aur C"
    return ", ".join(parts[:-1]) + f" aur {parts[-1]}"


# ──────────────────────────────────────────────
# STEP A2: Emotion-aware alert text
# ──────────────────────────────────────────────
def format_alert_text(order: dict) -> str:
    """
    Builds the voice-note script. The opening line changes based on
    order value ("High-Value Order" emotional alert feature):

      - total > HIGH_VALUE_THRESHOLD → excited prefix
      - otherwise                    → standard prefix

    Also mentions the wholesale discount if one was applied.
    """
    customer_name = order.get("customer_name", "Customer")
    items         = order.get("items", [])
    total_amount  = order.get("total_amount", 0)
    discount      = order.get("discount_applied", 0)

    items_str = _format_items_hinglish(items)

    if total_amount > HIGH_VALUE_THRESHOLD:
        prefix = "Bhaiya, bada order aaya hai!"
    else:
        prefix = "Naya order aaya hai."

    text = f"{prefix} {customer_name} ne {items_str} mangaya. Total: {total_amount} rupees."

    if discount and discount > 0:
        text += f" {discount} rupees ka discount diya gaya hai."

    return text


def get_voice_id_for_order(order: dict) -> str:
    """
    Picks an excited voice for high-value orders, calm voice otherwise.
    """
    total_amount = order.get("total_amount", 0)
    if total_amount > HIGH_VALUE_THRESHOLD:
        return ELEVENLABS_VOICE_ID_EXCITED
    return ELEVENLABS_VOICE_ID


def get_voice_settings_for_order(order: dict) -> dict:
    """
    Tunes stability/similarity_boost/style based on order value to make
    the TTS sound calmer (low-value) or more energetic (high-value).
    """
    total_amount = order.get("total_amount", 0)

    if total_amount > HIGH_VALUE_THRESHOLD:
        return {
            "stability": 0.35,
            "similarity_boost": 0.85,
            "style": 0.65,            # more expressive/excited
            "use_speaker_boost": True,
        }

    return {
        "stability": 0.50,
        "similarity_boost": 0.75,
        "style": 0.20,
        "use_speaker_boost": True,
    }


# ──────────────────────────────────────────────
# STEP B: Textual receipt (WhatsApp message body)
# ──────────────────────────────────────────────
def create_text_bill(order: dict) -> str:
    """
    Builds a nicely formatted WhatsApp text receipt, including
    line items, discount (if any), and final total.
    """
    bill  = "🛒 *Kirana AI Receipt*\n"
    bill += f"👤 Customer: {order.get('customer_name', 'Unknown')}\n"
    bill += "------------------------\n"

    for item in order.get("items", []):
        name  = item.get("name", "item")
        qty   = item.get("qty", 1)
        price = item.get("line_total", 0)
        bill += f"▪ {qty}x {name} - ₹{price}\n"

    bill += "------------------------\n"

    discount = order.get("discount_applied", 0)
    if discount and discount > 0:
        original = order.get("original_total", order.get("total_amount", 0))
        bill += f"Subtotal: ₹{original}\n"
        bill += f"🎉 Bulk Discount (10%): -₹{discount}\n"

    bill += f"💰 *Total: ₹{order.get('total_amount', 0)}*\n"

    split_with = order.get("split_with", [])
    if split_with:
        num_parties = len(split_with) + 1
        per_person = round(order.get("total_amount", 0) / num_parties, 2)
        bill += f"\n👥 Split between {num_parties} people: ₹{per_person} each\n"
        bill += f"   (with: {', '.join(split_with)})\n"

    return bill


# ──────────────────────────────────────────────
# STEP C: ElevenLabs → save MP3 locally
# ──────────────────────────────────────────────
def generate_audio(text: str, voice_id: str = None, voice_settings: dict = None) -> str:
    """
    Sends text to ElevenLabs, saves the returned MP3 to audio_files/.
    Returns just the filename (e.g. "alert_a3f9b2c1.mp3").
    Raises on any API error.

    voice_id / voice_settings let callers customize emotion per order.
    """
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY is not set in your .env file!")

    voice_id = voice_id or ELEVENLABS_VOICE_ID
    voice_settings = voice_settings or {
        "stability":        0.50,
        "similarity_boost": 0.75,
        "style":            0.20,
        "use_speaker_boost": True,
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key":   ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept":       "audio/mpeg",
    }

    payload = {
        "text":     text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": voice_settings,
    }

    print(f"[ElevenLabs] 📤 Sending (voice={voice_id}): \"{text}\"")
    resp = requests.post(url, json=payload, headers=headers, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs API error {resp.status_code}: {resp.text[:200]}"
        )

    filename = f"alert_{uuid.uuid4().hex[:8]}.mp3"
    filepath = AUDIO_DIR / filename

    with open(filepath, "wb") as f:
        f.write(resp.content)

    print(f"[ElevenLabs] ✅ Audio saved → {filename} ({len(resp.content)//1024} KB)")
    return filename


# ──────────────────────────────────────────────
# STEP D: Twilio → send WhatsApp voice note + receipt
# ──────────────────────────────────────────────
def _normalize_phone(phone: str) -> str:
    """Ensure the number is in whatsapp:+91XXXXXXXXXX format."""
    phone = phone.strip()
    if not phone.startswith("whatsapp:"):
        phone = f"whatsapp:{phone}"
    return phone


def send_whatsapp(audio_filename: str, shopkeeper_phone: str, body_text: str = "🛒 Naya order aaya hai!") -> None:
    """
    Sends the MP3 as a WhatsApp media message via Twilio, with a
    customizable text body (used for the textual receipt).
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials (SID / AUTH_TOKEN) are not set in .env!")

    audio_url = f"{PUBLIC_BASE_URL}/audio/{audio_filename}"
    to_phone  = _normalize_phone(shopkeeper_phone)

    print(f"[Twilio] 📤 Sending audio to {to_phone}")
    print(f"[Twilio]    Media URL → {audio_url}")

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=TWILIO_WA_FROM,
        to=to_phone,
        media_url=[audio_url],
        body=body_text,
    )

    print(f"[Twilio] ✅ Message sent → SID={message.sid}  Status={message.status}")


def send_whatsapp_text(shopkeeper_phone: str, body_text: str) -> None:
    """
    Sends a text-only WhatsApp message (no audio attachment).
    Used for the Vasooli debt-collection note.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials (SID / AUTH_TOKEN) are not set in .env!")

    to_phone = _normalize_phone(shopkeeper_phone)

    print(f"[Twilio] 📤 Sending text-only message to {to_phone}")

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=TWILIO_WA_FROM,
        to=to_phone,
        body=body_text,
    )

    print(f"[Twilio] ✅ Text message sent → SID={message.sid}  Status={message.status}")


# ──────────────────────────────────────────────
# PUBLIC ENTRY POINT (called from main.py)
# ──────────────────────────────────────────────
def send_alert(order: dict, shopkeeper_phone: str) -> None:
    """
    Full pipeline:
      1. Format emotion-aware Hinglish alert text
      2. Pick voice ID + voice settings based on order value
      3. Generate ElevenLabs MP3
      4. Build textual receipt
      5. Send audio + receipt via Twilio WhatsApp
    """
    text           = format_alert_text(order)
    voice_id       = get_voice_id_for_order(order)
    voice_settings = get_voice_settings_for_order(order)

    audio_filename = generate_audio(text, voice_id=voice_id, voice_settings=voice_settings)

    receipt = create_text_bill(order)
    send_whatsapp(audio_filename, shopkeeper_phone, body_text=receipt)


# ──────────────────────────────────────────────
# FEATURE: Automated "Vasooli" (Debt Collection) Voice Note
# ──────────────────────────────────────────────
def build_vasooli_text(customer_name: str, outstanding_amount: float) -> str:
    """
    Builds the polite-but-firm Hindi reminder script for outstanding khata.
    """
    return (
        f"Namaste {customer_name}, Kirana store se bol rahe hain. "
        f"Aapka pichla khata balance {outstanding_amount} rupees hai. "
        f"Kripya payment kar dein. Dhanyavaad."
    )


def send_vasooli_alert(customer_name: str, customer_phone: str, outstanding_amount: float) -> str:
    """
    Generates and sends a debt-collection voice note directly to the
    customer's WhatsApp, asking them to clear their khata balance.

    Returns the generated audio filename.
    """
    text = build_vasooli_text(customer_name, outstanding_amount)

    # Use the calm/standard voice for a polite, non-aggressive tone
    audio_filename = generate_audio(
        text,
        voice_id=ELEVENLABS_VOICE_ID,
        voice_settings={
            "stability":        0.65,
            "similarity_boost": 0.75,
            "style":            0.10,
            "use_speaker_boost": True,
        },
    )

    send_whatsapp(
        audio_filename,
        customer_phone,
        body_text=(
            f"🙏 *Payment Reminder*\n"
            f"Aapka outstanding khata balance: ₹{outstanding_amount}\n"
            f"Kripya jaldi clear kar dein. Dhanyavaad! 🛒"
        ),
    )

    return audio_filename