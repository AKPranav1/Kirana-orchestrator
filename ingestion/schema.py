from pydantic import BaseModel, Field
from typing import List, Optional, Any

# =====================================================================
# LAYER 1: EXTRACTION SCHEMA (Strictly what the LLM populates)
# =====================================================================

class RawItem(BaseModel):
    name: str = Field(..., description="The unnormalized name of the item in any language (e.g., 'aata', 'doodh', 'milk')")
    qty: float = Field(..., description="The specific numerical quantity requested by the user")
    unit: Optional[str] = Field(None, description="The unit of measurement if explicitly stated (e.g., 'kg', 'packet', 'litre')")

class BuyerSplit(BaseModel):
    buyer_name: str = Field(..., description="The name of the individual this group of items belongs to. Use 'default' if no specific name is mentioned.")
    raw_items: List[RawItem] = Field(default_factory=list)

class ParsedOrderPayload(BaseModel):
    payment_intent: str = Field(..., description="Must return 'khata' if terms like tab, udhaar, account, credit, or 'khate me likho' are caught. Otherwise default to 'cash' or 'upi'.")
    request_pdf: bool = Field(False, description="Set to True ONLY if the customer explicitly requests a written statement, bill file, document, or historical statement.")
    raw_splits: List[BuyerSplit] = Field(default_factory=list)
    
    # 👇 Added 'te' for Telugu right here
    language: str = Field("hi", description="The 2-letter language code of the input (e.g., 'en' for English, 'hi' for Hindi/Hinglish, 'kn' for Kannada, 'te' for Telugu). Default to 'hi'.")

# =====================================================================
# LAYER 2: SYSTEM ORDINANCE SCHEMA (What your Python API outputs)
# =====================================================================

class ProcessedItem(BaseModel):
    item_name: str           # Clean catalog match name (e.g., "Ashirvaad Atta 5kg")
    quantity: float
    unit: Optional[str]
    unit_price: float        # Exact base price verified from your database catalog
    subtotal: float          # Programmatic computation (unit_price * quantity)

class ProcessedSplit(BaseModel):
    buyer_name: str
    items: List[ProcessedItem]
    order_total: float       # Exact arithmetic sum computed natively in Python
    previous_ledger: float   # Historical data retrieved securely from MongoDB Atlas
    updated_ledger: float    # New outstanding balance (previous_ledger + order_total)

class WhatsAppNotification(BaseModel):
    recipient_name: str
    message_body: str        # The exact custom bill text block dispatched back to Twilio

# ONLY KEEP THIS ONE
class FinalOrderManifest(BaseModel):
    customer_phone: str      # <-- The primary ID for the database
    input_type: str          
    raw_input_url: Optional[str] = None
    payment_mode: str
    pdf_requested: bool
    processed_splits: List[ProcessedSplit]
    whatsapp_notifications: List[WhatsAppNotification]
    status: str = "pending"
    error: bool = False
    debug: Optional[Any] = None
    language: str = "hi"   