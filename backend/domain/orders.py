"""Canonical commands accepted from manual, extracted and webhook orders."""
from decimal import Decimal
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class DomainError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


class InputModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True, allow_inf_nan=False)


class OrderItem(InputModel):
    product_id: str | None = Field(None, max_length=100, validation_alias=AliasChoices("product_id", "productId"))
    name: str | None = Field(None, max_length=200, validation_alias=AliasChoices("name", "productName", "item_name"))
    qty: Decimal = Field(gt=0, le=100000, decimal_places=3, validation_alias=AliasChoices("qty", "quantity"))
    unit: str | None = Field(None, max_length=20)

    @model_validator(mode="after")
    def identity_required(self):
        if not self.product_id and not self.name:
            raise ValueError("A catalogue product ID or exact name is required")
        if self.unit:
            self.unit = self.unit.casefold()
        return self


class OrderCommand(InputModel):
    request_id: str = Field(min_length=8, max_length=128)
    store_id: str = Field("store_001", min_length=1, max_length=100)
    customer_name: str = Field("Walk-in", min_length=1, max_length=100, validation_alias=AliasChoices("customer_name", "customerName"))
    customer_phone: str = Field("", max_length=40, validation_alias=AliasChoices("customer_phone", "customerPhone"))
    items: list[OrderItem] = Field(min_length=1, max_length=100)
    payment_mode: Literal["cash", "upi", "khata"] = "cash"
    split_with: list[str] = Field(default_factory=list, max_length=20)
    language: str = Field("en", min_length=2, max_length=10)
    input_type: str = Field("manual", max_length=30)

    @model_validator(mode="after")
    def valid_participants(self):
        participants = [self.customer_name.casefold()]
        for name in self.split_with:
            if not name.strip() or len(name) > 100 or name.strip().casefold() in participants:
                raise ValueError("Split participants must be distinct nonempty names")
            participants.append(name.strip().casefold())
        self.split_with = [name.strip() for name in self.split_with]
        return self


class LedgerCommand(InputModel):
    request_id: str = Field(min_length=8, max_length=128)
    store_id: str = Field("store_001", min_length=1, max_length=100)
    customer_name: str = Field(min_length=1, max_length=100, validation_alias=AliasChoices("customer_name", "customerId", "customerName"))
    type: Literal["credit", "payment"]
    amount: Decimal = Field(gt=0, le=100000000, decimal_places=2)
    description: str = Field("", max_length=500)
