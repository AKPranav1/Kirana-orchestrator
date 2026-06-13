import os
import re
from .schema import ParsedOrderPayload, BuyerSplit, RawItem

SYSTEM_INSTRUCTION = """
You are the structural parsing brain of an enterprise Kirana Management System. Your strict function is to extract semantic data from unstructured user strings.

OPERATIONAL PARAMETERS:
1. Multi-lingual Adaptability: Accept inputs in pure English, Hindi, Hinglish, or mixed-code variations. Map semantic concepts accurately regardless of syntax or phonetic spelling.
2. Payment Intent Tracking: If phrases like "khate me likho", "account me daal dena", "udhaar karo", or "put it on my tab" are detected, set payment_intent to 'khata'.
3. PDF/Statement Detection: If the user requests an itemized bill record or statement ("pdf bill de do", "hisab ka list bhejo", "generate history document"), set request_pdf to true.
4. Entity Split Grouping: Identify individual names if multiple buyers are embedded in a single sentence (e.g., "Mohan ko ek doodh packet aur Anil ko 2kg sugar"). Group items explicitly inside separate 'raw_splits' entities matching those names. If no name is given, assign items to buyer_name 'default'.
5. Mathematical Isolation: Perform ZERO arithmetic, addition, tracking of prices, or valuation. Extract structural data tokens only.
"""


async def parse_order_text(text_content: str) -> ParsedOrderPayload:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Graceful fallback for demo mode when GEMINI_API_KEY is not present.
        # Try a lightweight heuristic parser to extract simple quantity+item pairs
        # from common user utterances. This is NOT a replacement for the LLM
        # but improves demo fidelity when the SDK/key is absent.
        try:
            from ingestion.utils import normalize_text
        except Exception:
            normalize_text = None

        print(
            "[gemini] GEMINI_API_KEY missing — using heuristic fallback parser for demo"
        )
        text = text_content or ""
        cleaned = text.lower()
        if normalize_text:
            cleaned, _ = normalize_text(cleaned)

        # map English 'half' to 0.5 for heuristics
        cleaned = cleaned.replace("half", "0.5")

        # determine payment intent heuristically
        payment_intent = (
            "khata"
            if "khata" in cleaned
            or "udhaar" in cleaned
            or "account" in cleaned
            or "tab" in cleaned
            else "cash"
        )

        # split on commas and ' and '
        parts = [p.strip() for p in re.split(r",| and | & ", cleaned) if p.strip()]
        items = []
        for p in parts:
            # skip phrases that look like instructions
            if (
                any(w in p for w in ("put", "please", "send", "to", "on", "for"))
                and re.search(r"\d", p) is None
            ):
                continue
            m = re.search(r"(\d+(?:\.\d+)?)", p)
            if m:
                qty = float(m.group(1))
                name = re.sub(r"(\d+(?:\.\d+)?)", "", p).strip()
            else:
                qty = 1.0
                name = p
            # remove trailing words like 'kg', 'litre' not necessary here — SKU matcher handles units
            name = re.sub(
                r"\b(kg|kilo|litre|liter|packet|pack|piece|pc|gm|gram)\b", "", name
            ).strip()
            if name and name != "":
                items.append(RawItem(name=name, qty=qty))

        if not items:
            # fallback to single raw item if heuristics failed
            items = [RawItem(name=text_content.strip(), qty=1)]

        return ParsedOrderPayload(
            payment_intent=payment_intent,
            request_pdf=False,
            raw_splits=[BuyerSplit(buyer_name="default", raw_items=items)],
            language="hi",
        )

    # If SDK not available or import fails, fall back to demo payload
    try:
        from google import genai
        from google.genai import types
    except Exception as e:
        print(
            f"[gemini] genai SDK unavailable ({e}) — returning fallback ParsedOrderPayload for demo"
        )
        return ParsedOrderPayload(
            payment_intent="cash",
            request_pdf=False,
            raw_splits=[
                BuyerSplit(
                    buyer_name="default",
                    raw_items=[RawItem(name=text_content.strip(), qty=1)],
                )
            ],
            language="hi",
        )

    # The new SDK uses a Client object instead of global configuration
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Raw Unprocessed Ingestion Line: {text_content}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ParsedOrderPayload,
        ),
    )

    return ParsedOrderPayload.model_validate_json(response.text)
