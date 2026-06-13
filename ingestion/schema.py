from pydantic import BaseModel, Field
from typing import List, Optional, Any

class Item(BaseModel):
    name: str
    qty: float
    unit: Optional[str]
    unit_price: Optional[float] = None
    match_score: Optional[float] = None
    original_name: Optional[str] = None

class Order(BaseModel):
    customer_phone: Optional[str] = None
    store_id: Optional[str] = None
    items: List[Item] = Field(default_factory=list)
    split_with: Optional[List[str]] = None
    payment_mode: Optional[str] = None
    input_type: str
    raw_input_url: Optional[str] = None
    total_amount: Optional[float] = None
    status: Optional[str] = "pending"
    error: Optional[bool] = False
    debug: Optional[Any] = None