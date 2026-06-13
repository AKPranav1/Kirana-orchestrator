import os
from google import genai
from google.genai import types
from .schema import ParsedOrderPayload

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
        raise ValueError("CRITICAL FAILURE: GEMINI_API_KEY variable is absent from your environment configuration.")
    
    # The new SDK uses a Client object instead of global configuration
    client = genai.Client(api_key=api_key)
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Raw Unprocessed Ingestion Line: {text_content}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ParsedOrderPayload
        )
    )
    
    return ParsedOrderPayload.model_validate_json(response.text)